from utils.ai import generate_response
from utils.helpers import get_current_time_context
from utils.prompts import (
    analyze_history_agent_prompt,
    casual_grammar_agent_prompt,
    compact_followup_agent_prompt,
    final_compact_agent_prompt,
    final_decision_agent_prompt,
    final_truncation_agent_prompt,
    followup_question_agent_prompt,
    gfogo_repeat_filter_agent_prompt,
    memory_agent_prompt,
    personalization_agent_prompt,
    question_decision_agent_prompt,
    reply_validity_agent_prompt,
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
    }


def format_history(history):
    return "\n".join(
        f"{h['role']}: {h['content']}" for h in history if h.get("content")
    )


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


async def personalization_agent(user_message, message, history):
    current_time_context = get_current_time_context()
    formatted_history = ""
    if history:
        formatted_history = "\n".join(
            f"{h['role']}: {h['content']}" for h in history if h.get("content")
        )
    prompt = personalization_agent_prompt.format(
        current_time_context=current_time_context,
        history=formatted_history,
        user_message=user_message,
    )
    response = await generate_response(prompt, user_message, history)
    return response.strip()


async def analyze_history_agent(history):
    formatted_history = format_history(history)
    last_user_message = ""
    for h in reversed(history):
        if h.get("role") == "user" and h.get("content"):
            last_user_message = h["content"]
            break
    prompt = analyze_history_agent_prompt.format(
        history=formatted_history, last_user_message=last_user_message
    )
    result = await generate_response(prompt, last_user_message, history)
    return result.strip()


async def followup_question_agent(answer, history, current_time_context):
    formatted_history = "\n".join(
        f"{h['role']}: {h['content']}" for h in history if h.get("content")
    )
    prompt = followup_question_agent_prompt.format(
        current_time_context=current_time_context,
        history=formatted_history,
        answer=answer,
    )
    result = await generate_response(prompt, answer, history)
    return result.strip()


async def compact_followup_agent(reply, history):
    prompt = compact_followup_agent_prompt.format(
        history=format_history(history), reply=reply
    )
    result = await generate_response(prompt, reply, history)
    return result.strip()


async def final_truncation_agent(reply, history, current_time_context):
    formatted_history = "\n".join(
        f"{h['role']}: {h['content']}" for h in history if h.get("content")
    )
    prompt = final_truncation_agent_prompt.format(
        current_time_context=current_time_context,
        history=formatted_history,
        reply=reply,
    )
    result = await generate_response(prompt, reply, history)
    return result.strip()


async def final_decision_agent(reply, history):
    prompt = final_decision_agent_prompt.format(
        history=format_history(history), reply=reply
    )
    result = await generate_response(prompt, reply, history)
    return result.strip().lower()


async def question_decision_agent(reply, history):
    prompt = question_decision_agent_prompt.format(
        history=format_history(history), reply=reply
    )
    result = await generate_response(prompt, reply, history)
    return result.strip().lower()


async def casual_grammar_agent(reply, history):
    prompt = casual_grammar_agent_prompt.format(
        history=format_history(history), reply=reply
    )
    result = await generate_response(prompt, reply, history)
    return result.strip()


async def final_compact_agent(reply, history):
    prompt = final_compact_agent_prompt.format(
        history=format_history(history), reply=reply
    )
    result = await generate_response(prompt, reply, history)
    return result.strip()


async def gfogo_repeat_filter_agent(reply, history):
    formatted_history = "\n".join(
        f"{h['role']}: {h['content']}" for h in history if h.get("content")
    )
    prompt = gfogo_repeat_filter_agent_prompt.format(
        history=formatted_history, reply=reply
    )
    result = await generate_response(prompt, reply, history)
    return result.strip()


async def memory_agent(user_message, history):
    formatted_history = "\n".join(
        f"{h['role']}: {h['content']}" for h in history if h.get("content")
    )
    prompt = memory_agent_prompt.format(
        history=formatted_history, user_message=user_message
    )
    result = await generate_response(prompt, user_message, history)
    return result.strip()
