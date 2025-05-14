import asyncio
import os
import random

import discord
from discord.ext import commands

from utils.ai import generate_response
from utils.error_notifications import webhook_log
from utils.helpers import load_instructions
from utils.split_response import split_response

MAX_CONTEXT = 6  # Number of recent messages to use as context


class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def is_owner(ctx):
        return ctx.author.id == ctx.bot.owner_id

    @commands.command(name="ping")
    @commands.cooldown(1, 30, commands.BucketType.user)
    @commands.check(is_owner)
    async def ping(self, ctx):
        latency = self.bot.latency * 1000
        await ctx.send(f"Pong! Latency: {latency:.2f} ms", delete_after=30)

    @commands.command(name="help", description="Get all other commands!")
    @commands.check(is_owner)
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def help(self, ctx):
        if not self.bot.help_command_enabled:
            return

        prefix = self.bot.command_prefix
        help_text = f"""```
Bot Commands:
{prefix}pause - Pause the bot from producing AI responses
{prefix}analyse [user] - Analyze a user's message history and provides a psychological profile
{prefix}wipe - Clears history of the bot
{prefix}ping - Shows the bot's latency
{prefix}toggleactive [id / channel] - Toggle a mentioned channel or the current channel to the list of active channels
{prefix}toggledm - Toggle if the bot should be active in DM's or not
{prefix}togglegc - Toggle if the bot should be active in group chats or not
{prefix}ignore [user] - Stop a user from using the bot
{prefix}reload - Reloads all cogs and the instructions
{prefix}prompt [prompt / clear] - View, set or clear the prompt for the AI
{prefix}restart - Restarts the entire bot
{prefix}shutdown - Shuts down the entire bot

Created by @najmul (451627446941515817) (Discord Server: /yUWmzQBV4P)
https://github.com/Najmul190/Discord-AI-Selfbot```
"""
        await ctx.send(help_text, delete_after=30)

    @commands.command(
        aliases=["analyze"],
        description="Analyze a user's message history and provides a psychological profile.",
    )
    @commands.check(is_owner)
    @commands.cooldown(1, 300, commands.BucketType.user)
    async def analyse(self, ctx, user: discord.User):
        temp = await ctx.send(f"Analysing {user.name}'s message history...")

        message_history = []
        async for message in ctx.channel.history(limit=1500):
            if message.author == user:
                message_history.append(message.content)

        if len(message_history) > 200:
            message_history = message_history[-200:]

        # Contextual Agent: Use a sliding window for context
        context_window = message_history[-MAX_CONTEXT:] if message_history else []
        last_message = context_window[-1] if context_window else ""

        # Sentiment/Intent Agent (expanded filter prompt)
        filter_prompt = (
            "You are a filter for a group chat AI. "
            "If the following message is a normal, casual, or friendly question, joke, or statement a typical teenager would answer, reply with 'yes'. "
            "If it's a hard question (like math, technical, homework, or something a regular person wouldn't answer), reply with 'no'. "
            "If it's spam, offensive, or out of character, reply with 'no'. "
            "Examples:\n"
            "Q: What's up? A: yes\n"
            "Q: How are you? A: yes\n"
            "Q: What is 37373/282? A: no\n"
            "Q: Can you solve this equation? A: no\n"
            "Q: Wanna play a game? A: yes\n"
            "Q: You're so annoying! A: yes\n"
            "Q: Tell me a joke! A: yes\n"
            f'Message: "{last_message}"'
        )

        # Build context string for the main agent
        context_str = "\n".join([f"{user.name}: {msg}" for msg in context_window])

        instructions = load_instructions() + f"\n{context_str}"
        prompt = last_message

        async def generate_response_in_thread(prompt):
            print(
                f"[AI-Selfbot] [START] Analyse command triggered for user: {user.name}"
            )
            print(f"[AI-Selfbot] [CONTEXT] Context window: {context_window}")
            print(f"[AI-Selfbot] [FILTER] Filter prompt: {filter_prompt}")

            # Step 1: Sentiment/Intent Agent (filter)
            filter_result = await generate_response(filter_prompt, "", history=None)
            print(f"[AI-Selfbot] [FILTER RESULT] {filter_result.strip()}")
            if filter_result.strip().lower().startswith("no"):
                print(
                    f"[AI-Selfbot] [SKIP] Skipped hard/unusual question: {last_message}"
                )
                await temp.delete()
                return

            # Step 2: Contextual + Main Agent
            print(f"[AI-Selfbot] [MAIN AGENT] Instructions: {instructions}")
            print(f"[AI-Selfbot] [MAIN AGENT] Prompt: {prompt}")
            response = await generate_response(prompt, instructions, history=None)
            print(f"[AI-Selfbot] [MAIN AGENT] Response: {response}")
            chunks = split_response(response)

            await temp.delete()

            # Step 3: Fallback Agent if empty
            fallback_replies = [
                "idk bro",
                "no clue fr",
                "can't help with that bro",
                "not sure tbh",
            ]
            sent = False
            for chunk in chunks:
                if chunk.strip() == "":
                    fallback = random.choice(fallback_replies)
                    print(
                        f"[AI-Selfbot] [FALLBACK] No answer generated for: {prompt[:80]}... Using fallback: {fallback}"
                    )
                    await asyncio.sleep(random.uniform(1.0, 3.0))
                    await ctx.reply(fallback)
                    sent = True
                    continue
                print(f"[AI-Selfbot] [SEND] Sending chunk: {chunk}")
                await asyncio.sleep(random.uniform(1.0, 3.0))
                await ctx.reply(chunk)
                sent = True
            if not sent:
                print(f"[AI-Selfbot] [NO REPLY] No reply sent for: {prompt[:80]}...")

        async with ctx.channel.typing():
            asyncio.create_task(generate_response_in_thread(prompt))


async def setup(bot):
    await bot.add_cog(General(bot))
