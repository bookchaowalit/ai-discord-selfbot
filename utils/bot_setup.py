import math
import os
import random
import re
import shutil
import sys
import time
from asyncio import Lock
from collections import deque
from datetime import datetime

import discord
import pytz
from discord.ext import commands
from dotenv import load_dotenv

from utils.ai import generate_response, generate_response_image, init_ai
from utils.ai_agents import (
    filter_agent,
    personalization_agent,
    reply_to_reply_agent,
    reply_validity_agent,
    should_reply_agent,
    tone_context_agent,
)
from utils.db import get_channels, get_ignored_users, init_db
from utils.error_notifications import webhook_log
from utils.helpers import (
    clear_console,
    get_env_path,
    load_config,
    load_instructions,
    resource_path,
)
from utils.split_response import split_response

# --- Configuration and Initialization ---
config = load_config()
env_path = get_env_path()
load_dotenv(dotenv_path=env_path, override=True)
init_db()
init_ai()

TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = config["bot"]["prefix"]
OWNER_ID = config["bot"]["owner_id"]
DISABLE_MENTIONS = config["bot"]["disable_mentions"]

bot = commands.Bot(command_prefix=PREFIX, help_command=None)

bot.owner_id = OWNER_ID
bot.active_channels = set(config["bot"].get("active_channels", []))
bot.ignore_users = get_ignored_users()
bot.message_history = {}
bot.paused = False
bot.allow_dm = config["bot"].get("allow_dm", True)
bot.allow_gc = config["bot"].get("allow_gc", True)
bot.help_command_enabled = config["bot"].get("help_command_enabled", True)
bot.realistic_typing = config["bot"].get("realistic_typing", True)
bot.anti_age_ban = config["bot"].get("anti_age_ban", False)
bot.batch_messages = config["bot"].get("batch_messages", False)
bot.batch_wait_time = float(config["bot"].get("batch_wait_time", 2.0))
bot.hold_conversation = config["bot"].get("hold_conversation", True)
bot.user_message_counts = {}
bot.user_cooldowns = {}
bot.last_reply_time = {}
bot.instructions = load_instructions()
bot.message_queues = {}
bot.processing_locks = {}
bot.user_message_batches = {}
bot.active_conversations = {}
CONVERSATION_TIMEOUT = 150.0

SPAM_MESSAGE_THRESHOLD = 5
SPAM_TIME_WINDOW = 10.0
COOLDOWN_DURATION = 60.0
MAX_HISTORY = 15
MAX_CONTEXT = 6

# --- Helper Functions ---


def build_context_window(history, user_name):
    context_window = history[-MAX_CONTEXT:] if history else []
    return "\n".join(
        [
            f"{user_name}: {msg['content']}"
            for msg in context_window
            if msg["role"] == "user"
            and msg.get("content")
            and isinstance(msg["content"], str)
        ]
    )


def should_ignore_message(message):
    return (
        message.author.id in bot.ignore_users
        or message.author.id == bot.selfbot_id
        or message.author.bot
    )


def update_message_history(author_id, message_content):
    if author_id not in bot.message_history:
        bot.message_history[author_id] = []
    bot.message_history[author_id].append(message_content)
    bot.message_history[author_id] = bot.message_history[author_id][-MAX_HISTORY:]


def is_time_question(msg):
    msg = msg.lower()
    return any(
        kw in msg
        for kw in [
            "what time",
            "time is it",
            "current time",
            "now time",
        ]
    )


def get_thai_time_phrase():
    tz = pytz.timezone("Asia/Bangkok")
    now = datetime.now(tz)
    hour = now.hour
    minute = now.minute
    if random.random() < 0.5:
        if 5 <= hour < 12:
            return random.choice(["morning", "it's morning"])
        elif 12 <= hour < 17:
            return random.choice(["afternoon", "it's afternoon"])
        elif 17 <= hour < 20:
            return random.choice(["evening", "it's evening"])
        else:
            return random.choice(["night", "it's night"])
    else:
        return f"{hour:02d}:{minute:02d} (Thailand time)"


def is_relevant_message(msg, history=None):
    msg_lower = msg.lower().strip()
    if not msg or len(msg_lower) < 3:
        return False
    if all(c in "0123456789.,:;!?-_/\\ " for c in msg_lower):
        return False
    if msg_lower.count("?") > 1 or all(c in "?!" for c in msg_lower):
        return False
    url_pattern = r"^(https?://\S+)$"
    if re.match(url_pattern, msg_lower):
        return False
    gratitude_phrases = ["thank you", "thanks", "thx", "ขอบคุณ", "ขอบใจ"]
    if any(phrase in msg_lower for phrase in gratitude_phrases):
        if history:
            recent = history[-5:]
            for entry in reversed(recent):
                if entry.get("role") == "assistant":
                    return True
        return False
    return True


async def generate_response_and_reply(message, prompt, history, image_url=None):
    user_name = message.author.name
    filtered_history = [
        h
        for h in history
        if h.get("content")
        and isinstance(h["content"], str)
        and h["content"].strip() != ""
    ]
    context_window = [h for h in filtered_history if h["role"] == "user"][-MAX_CONTEXT:]
    if context_window:
        combined_prompt = "\n".join([msg["content"] for msg in context_window])
        last_user_message = context_window[-1]["content"]
    else:
        combined_prompt = prompt
        last_user_message = prompt

    tone = await tone_context_agent(message, history)
    should_reply = await should_reply_agent(message, history)
    if not should_reply:
        return

    if message.reference and message.reference.resolved:
        should_reply_to_reply = await reply_to_reply_agent(message)
        if not should_reply_to_reply:
            return

    if is_time_question(last_user_message):
        time_reply = get_thai_time_phrase()
        await message.reply(time_reply)
        key = f"{message.author.id}-{message.channel.id}"
        bot.message_history[key].append({"role": "assistant", "content": time_reply})
        return

    if not is_relevant_message(last_user_message, history):
        return

    should_filter = await filter_agent(last_user_message)
    if not should_filter:
        return

    context_str = build_context_window(filtered_history, user_name)
    instructions = load_instructions() + f"\n{context_str}"

    if image_url:
        response = await generate_response_image(
            combined_prompt, instructions, image_url, filtered_history
        )
    else:
        response = await generate_response(
            combined_prompt, instructions, filtered_history
        )

    response = await personalization_agent(response)
    is_valid = await reply_validity_agent(response)
    if not is_valid:
        return

    chunks = split_response(response)
    sent = False

    base_delay = random.uniform(8.0, 12.0)
    if chunks:
        total_length = sum(len(chunk) for chunk in chunks)
        base_delay += min(8.0, math.log1p(total_length) / 2)

    if (
        response is not None
        and isinstance(response, str)
        and response.strip() == "Sorry, I couldn't generate a response."
    ):
        return

    await asyncio.sleep(base_delay)

    async with message.channel.typing():
        for chunk in chunks:
            if chunk.strip() == "":
                continue
            await asyncio.sleep(random.uniform(1.0, 3.0))
            await message.reply(chunk)
            sent = True
        if not sent:
            pass

    if response and isinstance(response, str) and response.strip() != "":
        key = f"{message.author.id}-{message.channel.id}"
        bot.message_history[key].append({"role": "assistant", "content": response})

    return response


def should_bot_reply(message, history):
    if message.reference and message.reference.resolved:
        replied_to = message.reference.resolved
        replied_to_author = getattr(replied_to, "author", None)
        if replied_to_author and replied_to_author.id == bot.selfbot_id:
            return True
        recent = history[-5:]
        for entry in reversed(recent):
            if entry.get("role") == "assistant":
                return True
        if len(history) < 5:
            return True
        if history and hasattr(message.reference.resolved, "id"):
            last_msg = history[-1]
            if hasattr(message.reference.resolved, "id") and getattr(
                message.reference.resolved, "id", None
            ) == getattr(message, "id", None):
                return True
        return False
    return True


async def process_message_queue(channel_id):
    def get_reply_priority(message):
        if message.reference and message.reference.resolved:
            replied_to = message.reference.resolved
            replied_to_author = getattr(replied_to, "author", None)
            if replied_to_author and replied_to_author.id == bot.selfbot_id:
                return 0
            else:
                return 2
        else:
            return 1

    async with bot.processing_locks[channel_id]:
        while bot.message_queues[channel_id]:
            sorted_msgs = sorted(
                list(bot.message_queues[channel_id]), key=get_reply_priority
            )
            bot.message_queues[channel_id] = deque(sorted_msgs)

            message = bot.message_queues[channel_id].popleft()
            batch_key = f"{message.author.id}-{channel_id}"
            current_time = time.time()

            if bot.batch_messages:
                if batch_key not in bot.user_message_batches:
                    first_image_url = (
                        message.attachments[0].url if message.attachments else None
                    )
                    bot.user_message_batches[batch_key] = {
                        "messages": [],
                        "last_time": current_time,
                        "image_url": first_image_url,
                    }
                    bot.user_message_batches[batch_key]["messages"].append(message)

                    await asyncio.sleep(bot.batch_wait_time)

                    while bot.message_queues[channel_id]:
                        next_message = bot.message_queues[channel_id][0]
                        if (
                            next_message.author.id == message.author.id
                            and not next_message.content.startswith(PREFIX)
                        ):
                            next_message = bot.message_queues[channel_id].popleft()
                            if next_message.content not in [
                                m.content
                                for m in bot.user_message_batches[batch_key]["messages"]
                            ]:
                                bot.user_message_batches[batch_key]["messages"].append(
                                    next_message
                                )

                            if (
                                not bot.user_message_batches[batch_key]["image_url"]
                                and next_message.attachments
                            ):
                                bot.user_message_batches[batch_key]["image_url"] = (
                                    next_message.attachments[0].url
                                )
                        else:
                            break

                    messages_to_process = bot.user_message_batches[batch_key][
                        "messages"
                    ]
                    seen = set()
                    unique_messages = []
                    for msg in messages_to_process:
                        if msg.content not in seen:
                            seen.add(msg.content)
                            unique_messages.append(msg)

                    combined_content = "\n".join(msg.content for msg in unique_messages)
                    message_to_reply_to = unique_messages[-1]
                    image_url = bot.user_message_batches[batch_key]["image_url"]

                    del bot.user_message_batches[batch_key]
            else:
                combined_content = message.content
                message_to_reply_to = message
                image_url = message.attachments[0].url if message.attachments else None

            for mention in message_to_reply_to.mentions:
                combined_content = combined_content.replace(
                    f"<@{mention.id}>", f"@{mention.display_name}"
                )

            key = f"{message_to_reply_to.author.id}-{message_to_reply_to.channel.id}"
            if key not in bot.message_history:
                bot.message_history[key] = []

            if combined_content and isinstance(combined_content, str):
                bot.message_history[key].append(
                    {"role": "user", "content": combined_content}
                )
            history = bot.message_history[key]

            consecutive_bot_replies = 0
            for entry in reversed(history):
                if entry["role"] == "assistant":
                    consecutive_bot_replies += 1
                elif entry["role"] == "user":
                    break

            if consecutive_bot_replies >= 2:
                return

            now = time.time()
            min_delay = 25
            max_delay = 40
            delay = random.uniform(min_delay, max_delay)
            last_time = bot.last_reply_time.get(channel_id, 0)
            if now - last_time < delay:
                wait_time = delay - (now - last_time)
                await asyncio.sleep(wait_time)

            if message_to_reply_to.channel.id in bot.active_channels or (
                isinstance(message_to_reply_to.channel, discord.DMChannel)
                and bot.allow_dm
            ):
                response = await generate_response_and_reply(
                    message_to_reply_to, combined_content, history, image_url
                )
                if response and isinstance(response, str) and response.strip() != "":
                    bot.message_history[key].append(
                        {"role": "assistant", "content": response}
                    )
                    bot.last_reply_time[channel_id] = time.time()


# --- Bot Events ---


@bot.event
async def on_ready():
    bot.selfbot_id = bot.user.id
    clear_console()
    print(f"AI Selfbot successfully logged in as {bot.user.name} ({bot.selfbot_id}).\n")
    print("Active in the following channels:")
    for channel_id in bot.active_channels:
        channel = bot.get_channel(channel_id)
        if channel:
            try:
                print(f"- #{channel.name} in {channel.guild.name}")
            except Exception:
                pass


@bot.event
async def setup_hook():
    await load_extensions()


@bot.event
async def on_message(message):
    if should_ignore_message(message) and not message.author.id == bot.owner_id:
        return

    if message.content.startswith(PREFIX):
        await bot.process_commands(message)
        return

    channel_id = message.channel.id
    user_id = message.author.id
    current_time = time.time()

    batch_key = f"{user_id}-{channel_id}"

    if not bot.paused:
        if user_id in bot.user_cooldowns:
            cooldown_end = bot.user_cooldowns[user_id]
            if current_time < cooldown_end:
                return
            else:
                del bot.user_cooldowns[user_id]

        if user_id not in bot.user_message_counts:
            bot.user_message_counts[user_id] = []

        bot.user_message_counts[user_id] = [
            timestamp
            for timestamp in bot.user_message_counts[user_id]
            if current_time - timestamp < SPAM_TIME_WINDOW
        ]

        bot.user_message_counts[user_id].append(current_time)

        if len(bot.user_message_counts[user_id]) > SPAM_MESSAGE_THRESHOLD:
            bot.user_cooldowns[user_id] = current_time + COOLDOWN_DURATION
            bot.user_message_counts[user_id] = []
            return

        if channel_id not in bot.message_queues:
            bot.message_queues[channel_id] = deque()
            bot.processing_locks[channel_id] = Lock()

        bot.message_queues[channel_id].append(message)

        if not bot.processing_locks[channel_id].locked():
            import asyncio

            asyncio.create_task(process_message_queue(channel_id))


# --- Cog Loader ---


async def load_extensions():
    if getattr(sys, "frozen", False):
        cogs_dir = os.path.join(sys._MEIPASS, "cogs")
    else:
        cogs_dir = os.path.join(os.path.abspath("."), "cogs")

    if not os.path.exists(cogs_dir):
        print(f"Warning: Cogs directory not found at {cogs_dir}. Skipping cog loading.")
        return

    clear_console()

    for filename in os.listdir(cogs_dir):
        if filename.endswith(".py"):
            cog_name = f"cogs.{filename[:-3]}"
            try:
                print(f"Loading cog: {cog_name}")
                await bot.load_extension(cog_name)
            except Exception as e:
                print(f"Error loading cog {cog_name}: {e}")
