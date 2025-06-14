from utils.ai import generate_response
from utils.prompts import (
    analyze_history_prompt,
    channel_vocab_agent_prompt,
    consistency_agent_prompt,
    contextual_response_prompt,
    ensure_english_agent_prompt,
    filter_agent_prompt,
    final_compact_agent_prompt,
    hobby_favorite_agent_prompt,
    language_is_english_agent_prompt,
    no_ask_back_agent_prompt,
    nosy_reply_filter_agent_prompt,
    personalization_agent_prompt,
    question_validity_agent_prompt,
    relevance_agent_prompt,
    reply_to_reply_agent_prompt,
    reply_validity_agent_prompt,
    simplify_agent_prompt,
    slang_filter_agent_prompt,
    time_question_agent_prompt,
    tone_context_agent_prompt,
    topic_filter_agent_prompt,
)

# Import agent_settings and broadcast_log from your FastAPI server
try:
    from utils.api_server import agent_settings, broadcast_log
except ImportError:

    async def broadcast_log(*args, **kwargs):
        pass

    agent_settings = {
        "reply_to_reply_agent": {"enabled": True},
        "filter_agent": {"enabled": True},
        "tone_context_agent": {"enabled": True},
        "reply_validity_agent": {"enabled": True},
        "personalization_agent": {"enabled": True},
        "language_is_english_agent": {"enabled": True},
        "ensure_english_agent": {
            "enabled": True,
            "prompt": ensure_english_agent_prompt,
        },
    }


def get_log_context(message=None):
    """Helper to extract context for logging."""
    if message is None:
        return {}
    return {
        "channel_id": getattr(getattr(message, "channel", None), "id", None),
        "message_id": getattr(message, "id", None),
        "channel_name": getattr(getattr(message, "channel", None), "name", None),
        "author_name": str(getattr(message, "author", None)),
        "server_name": getattr(
            getattr(getattr(message, "channel", None), "guild", None), "name", None
        ),
    }


async def reply_to_reply_agent(message, history=None):
    if not agent_settings.get("reply_to_reply_agent", {}).get("enabled", True):
        return True
    replied_to_content = getattr(getattr(message, "reference", None), "resolved", None)
    replied_to_content = getattr(replied_to_content, "content", "")
    context_snippet = ""
    if history:
        recent = history[-5:]
        context_snippet = "\n".join(
            f"{h.get('role','user')}: {h.get('content','')}" for h in recent
        )
    full_prompt = (
        f"{reply_to_reply_agent_prompt}\nRecent context:\n{context_snippet}\n"
        f'Previous message: "{replied_to_content}"\nReply: "{message.content}"'
    )
    agent_result = await generate_response(full_prompt, "", history=None)
    log_msg = f"[AGENTIC FILTER] {agent_result.strip()}"
    print(f"[AI-Selfbot] {log_msg}")
    await broadcast_log(log_msg, **get_log_context(message))
    return agent_result.strip().lower().startswith("yes")


async def filter_agent(last_user_message, message=None, history=None):
    if not agent_settings.get("filter_agent", {}).get("enabled", True):
        return True
    context_snippet = ""
    if history:
        recent = history[-5:]
        context_snippet = "\n".join(
            f"{h.get('role','user')}: {h.get('content','')}" for h in recent
        )
    full_prompt = f'{filter_agent_prompt}\nRecent context:\n{context_snippet}\nMessage: "{last_user_message}"'
    print(f"[AI-Selfbot] [FILTER] Filter prompt: {full_prompt}")
    filter_result = await generate_response(full_prompt, "", history=None)
    log_msg = f"[FILTER RESULT] {filter_result.strip()}"
    print(f"[AI-Selfbot] {log_msg}")
    await broadcast_log(log_msg, **get_log_context(message))
    return filter_result.strip().lower().startswith("yes")


async def tone_context_agent(message, history):
    if not agent_settings.get("tone_context_agent", {}).get("enabled", True):
        return "neutral"
    context_snippet = ""
    if history:
        recent = history[-5:]
        context_snippet = "\n".join(
            f"{h.get('role','user')}: {h.get('content','')}" for h in recent
        )
    full_prompt = f'{tone_context_agent_prompt}\nRecent context:\n{context_snippet}\nMessage: "{message.content}"'
    result = await generate_response(full_prompt, "", history=None)
    log_msg = f"[TONE/CONTEXT AGENT] {result.strip()}"
    print(f"[AI-Selfbot] {log_msg}")
    await broadcast_log(log_msg, **get_log_context(message))
    return result.strip().lower()


async def reply_validity_agent(reply, message=None, history=None):
    if not agent_settings.get("reply_validity_agent", {}).get("enabled", True):
        return True
    context_snippet = ""
    if history:
        recent = history[-5:]
        context_snippet = "\n".join(
            f"{h.get('role','user')}: {h.get('content','')}" for h in recent
        )
    full_prompt = f'{reply_validity_agent_prompt}\nRecent context:\n{context_snippet}\nReply: "{reply}"'
    result = await generate_response(full_prompt, "", history=None)
    log_msg = f"[REPLY VALIDITY AGENT] {result.strip()}"
    print(f"[AI-Selfbot] {log_msg}")
    await broadcast_log(log_msg, **get_log_context(message))
    return result.strip().lower().startswith("yes")


async def personalization_agent(
    user_message, message=None, history=None, special_words=None
):
    context_snippet = ""
    if history:
        recent = history[-6:]
        context_snippet = "\n".join(
            f"{h.get('role','user')}: {h.get('content','')}" for h in recent
        )
    special_words_str = ""
    if special_words and special_words.lower() != "none":
        special_words_str = f"Special words/slang for this channel: {special_words}\n"
    prompt = (
        f"{personalization_agent_prompt}\n"
        f"{special_words_str}"
        f"Recent conversation:\n{context_snippet}\n"
        f'User message: "{user_message}"\n'
        f"Your reply:"
    )
    result = await generate_response(prompt, "", history=None)
    return result.strip()


async def language_is_english_agent(message_text, message=None, history=None):
    if not agent_settings.get("language_is_english_agent", {}).get("enabled", True):
        return True
    context_snippet = ""
    if history:
        recent = history[-5:]
        context_snippet = "\n".join(
            f"{h.get('role','user')}: {h.get('content','')}" for h in recent
        )
    full_prompt = f'{language_is_english_agent_prompt}\nRecent context:\n{context_snippet}\nMessage: "{message_text}"'
    result = await generate_response(full_prompt, "", history=None)
    log_msg = f"[LANGUAGE DETECT AGENT] {result.strip()}"
    print(f"[AI-Selfbot] {log_msg}")
    await broadcast_log(log_msg, **get_log_context(message))
    return result.strip().lower().startswith("true")


async def ensure_english_agent(reply, message=None, history=None):
    if not agent_settings.get("ensure_english_agent", {}).get("enabled", True):
        return reply
    is_english = await language_is_english_agent(
        reply, message=message, history=history
    )
    if is_english:
        return reply
    context_snippet = ""
    if history:
        recent = history[-5:]
        context_snippet = "\n".join(
            f"{h.get('role','user')}: {h.get('content','')}" for h in recent
        )
    full_prompt = f'{ensure_english_agent_prompt}\nRecent context:\n{context_snippet}\nMessage: "{reply}"'
    translated = await generate_response(full_prompt, "", history=None)
    log_msg = f"[ENSURE ENGLISH AGENT] {translated.strip()}"
    print(f"[AI-Selfbot] {log_msg}")
    await broadcast_log(log_msg, **get_log_context(message))
    return translated.strip()


async def analyze_history_agent(user_message, history):
    context_snippet = ""
    if history:
        recent = history[-6:]
        context_snippet = "\n".join(
            f"{h.get('role','user')}: {h.get('content','')}" for h in recent
        )
    prompt = (
        f"{analyze_history_prompt}\n"
        f"Recent conversation:\n{context_snippet}\n"
        f'User\'s latest message: "{user_message}"\n'
        f"Summary:"
    )
    result = await generate_response(prompt, "", history=None)
    return result.strip()


async def contextual_response_agent(summary, user_message, history):
    context_snippet = ""
    if history:
        recent = history[-6:]
        context_snippet = "\n".join(
            f"{h.get('role','user')}: {h.get('content','')}" for h in recent
        )
    prompt = (
        f"{contextual_response_prompt}\n"
        f"Conversation summary: {summary}\n"
        f"Recent conversation:\n{context_snippet}\n"
        f'User\'s latest message: "{user_message}"\n'
        f"Bot's reply:"
    )
    result = await generate_response(prompt, "", history=None)
    return result.strip()


async def consistency_agent(summary, user_message, bot_reply):
    prompt = (
        f"{consistency_agent_prompt}\n"
        f"Conversation summary: {summary}\n"
        f'User\'s latest message: "{user_message}"\n'
        f'Bot\'s reply: "{bot_reply}"\n'
        f"Does the reply match the context and summary? If not, suggest a better reply. If yes, reply with 'OK'."
    )
    result = await generate_response(prompt, "", history=None)
    return result.strip()


async def final_compact_agent(reply):
    prompt = f"{final_compact_agent_prompt}\n" f'Reply: "{reply}"\n' f"Shortened reply:"
    result = await generate_response(prompt, "", history=None)
    return result.strip()


async def topic_filter_agent(user_message, history=None, message=None):
    context_snippet = ""
    if history:
        recent = history[-5:]
        context_snippet = "\n".join(
            f"{h.get('role','user')}: {h.get('content','')}" for h in recent
        )
    prompt = (
        f"{topic_filter_agent_prompt}\n"
        f"Recent context:\n{context_snippet}\n"
        f'User message: "{user_message}"'
    )
    result = await generate_response(prompt, "", history=None)
    log_msg = f"[TOPIC FILTER AGENT] {result.strip()}"
    print(f"[AI-Selfbot] {log_msg}")
    await broadcast_log(log_msg, **get_log_context(message))
    return result.strip().lower().startswith("yes")


async def relevance_agent(user_message, history=None, message=None):
    context_snippet = ""
    if history:
        recent = history[-5:]
        context_snippet = "\n".join(
            f"{h.get('role','user')}: {h.get('content','')}" for h in recent
        )
    prompt = (
        f"{relevance_agent_prompt}\n"
        f"Recent context:\n{context_snippet}\n"
        f'User message: "{user_message}"'
    )
    result = await generate_response(prompt, "", history=None)
    log_msg = f"[RELEVANCE AGENT] {result.strip()}"
    print(f"[AI-Selfbot] {log_msg}")
    await broadcast_log(log_msg, **get_log_context(message))
    return result.strip().lower().startswith("yes")


async def channel_vocab_agent(history=None, message=None):
    context_snippet = ""
    if history:
        recent = history[-10:]  # Use more history for better detection
        context_snippet = "\n".join(
            f"{h.get('role','user')}: {h.get('content','')}" for h in recent
        )
    prompt = (
        f"{channel_vocab_agent_prompt}\n"
        f"Recent conversation:\n{context_snippet}\n"
        f"Special words or slang:"
    )
    result = await generate_response(prompt, "", history=None)
    log_msg = f"[CHANNEL VOCAB AGENT] {result.strip()}"
    print(f"[AI-Selfbot] {log_msg}")
    await broadcast_log(log_msg, **get_log_context(message))
    return result.strip()


async def simplify_agent(reply, message=None):
    prompt = (
        f"{simplify_agent_prompt}\n" f'Original reply: "{reply}"\n' f"Simplified reply:"
    )
    result = await generate_response(prompt, "", history=None)
    return result.strip()


async def slang_filter_agent(reply, message=None):
    prompt = (
        f"{slang_filter_agent_prompt}\n"
        f'Original reply: "{reply}"\n'
        f"Filtered reply:"
    )
    result = await generate_response(prompt, "", history=None)
    return result.strip()


async def question_validity_agent(reply, message=None):
    prompt = (
        f"{question_validity_agent_prompt}\n"
        f'Bot\'s reply: "{reply}"\n'
        f"Checked reply:"
    )
    result = await generate_response(prompt, "", history=None)
    return result.strip()


async def nosy_reply_filter_agent(
    user_message, replied_message, history=None, message=None
):
    context_snippet = ""
    if history:
        recent = history[-5:]
        context_snippet = "\n".join(
            f"{h.get('role','user')}: {h.get('content','')}" for h in recent
        )
    prompt = (
        f"{nosy_reply_filter_agent_prompt}\n"
        f"Recent context:\n{context_snippet}\n"
        f'Original message: "{replied_message}"\n'
        f'User\'s reply: "{user_message}"\n'
        f"Should the bot reply? (yes/no):"
    )
    result = await generate_response(prompt, "", history=None)
    return result.strip().lower().startswith("yes")


async def time_question_agent(user_message, history=None, message=None):
    prompt = (
        f"{time_question_agent_prompt}\n"
        f'User message: "{user_message}"\n'
        f"Your answer:"
    )
    result = await generate_response(prompt, "", history=None)
    return result.strip().lower()


async def no_ask_back_agent(reply, message=None):
    prompt = (
        f"{no_ask_back_agent_prompt}\n" f'Bot\'s reply: "{reply}"\n' f"Rewritten reply:"
    )
    result = await generate_response(prompt, "", history=None)
    return result.strip()


async def hobby_favorite_agent(user_message, reply):
    prompt = (
        f"{hobby_favorite_agent_prompt}\n"
        f'User message: "{user_message}"\n'
        f'Bot\'s reply: "{reply}"\n'
        f"Your answer:"
    )
    result = await generate_response(prompt, "", history=None)
    return result.strip()
