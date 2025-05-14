from utils.ai import generate_response


async def should_reply_agent(message, history):
    context_snippet = ""
    if history:
        recent = history[-5:]
        context_snippet = "\n".join(
            f"{h.get('role','user')}: {h.get('content','')}" for h in recent
        )
    should_reply_prompt = (
        "You are an assistant that decides if a Discord bot should reply to a message in a group chat. "
        "Given the recent conversation context, the message, and who is replying to whom, answer 'yes' if the bot should reply, "
        "or 'no' if the bot should skip. Only reply 'yes' if the message is relevant, addressed to the bot, or the bot was involved recently.\n"
        f"Recent context:\n{context_snippet}\n"
        f'Current message: "{message.content}"\n'
        f"Who is replying: {message.author}\n"
        f"Who is being replied to: {getattr(getattr(message.reference, 'resolved', None), 'author', None) if message.reference and message.reference.resolved else 'None'}\n"
        "Should the bot reply? (yes/no)"
    )
    agentic_decision = await generate_response(should_reply_prompt, "", history=None)
    print(f"[AI-Selfbot] [SHOULD-REPLY AGENT] {agentic_decision.strip()}")
    return agentic_decision.strip().lower().startswith("yes")


async def reply_to_reply_agent(message):
    replied_to_content = getattr(getattr(message, "reference", None), "resolved", None)
    replied_to_content = getattr(replied_to_content, "content", "")
    agent_prompt = (
        "You are an assistant that decides if a Discord bot should reply to a message. "
        "Given the previous message and the reply, answer 'yes' if the reply is directed at the bot or continues a conversation with the bot, "
        "otherwise answer 'no'.\n"
        f'Previous message: "{replied_to_content}"\n'
        f'Reply: "{message.content}"\n'
        "Should the bot reply? (yes/no)"
    )
    agent_result = await generate_response(agent_prompt, "", history=None)
    print(f"[AI-Selfbot] [AGENTIC FILTER] {agent_result.strip()}")
    return agent_result.strip().lower().startswith("yes")


async def filter_agent(last_user_message):
    filter_prompt = (
        "You are a filter for a group chat AI. "
        "If the following message is a normal, casual, or friendly question, joke, or statement a typical teenager would answer, reply with 'yes'. "
        "If it's a hard question (like math, technical, homework, trivia, history, science, or something a regular person wouldn't answer), reply with 'no'. "
        "If it's a question that needs book knowledge, facts, or is nerdy/smart (like 'Who is the smartest person ever?', 'Who invented the lightbulb?', 'What is the capital of France?'), reply with 'no'. "
        "If it's spam, offensive, or out of character, reply with 'no'. "
        "Examples:\n"
        "Q: What's up? A: yes\n"
        "Q: How are you? A: yes\n"
        "Q: What is 37373/282? A: no\n"
        "Q: Can you solve this equation? A: no\n"
        "Q: Wanna play a game? A: yes\n"
        "Q: You're so annoying! A: yes\n"
        "Q: Tell me a joke! A: yes\n"
        "Q: Who is the smartest person ever? A: no\n"
        "Q: Who invented the lightbulb? A: no\n"
        "Q: What is the capital of France? A: no\n"
        "Q: Who won the world cup in 2018? A: no\n"
        "Q: What's your favorite movie? A: yes\n"
        f'Message: "{last_user_message}"'
    )
    print(f"[AI-Selfbot] [FILTER] Filter prompt: {filter_prompt}")
    filter_result = await generate_response(filter_prompt, "", history=None)
    print(f"[AI-Selfbot] [FILTER RESULT] {filter_result.strip()}")
    return filter_result.strip().lower().startswith("yes")


async def tone_context_agent(message, history):
    # Classifies the message tone/context (step E)
    prompt = (
        "You are an agent that classifies the tone and context of a Discord message. "
        "Given the message and recent context, reply with 'casual', 'friendly', 'neutral', 'serious', 'off-topic', or 'other'.\n"
        f"Recent context: {history[-5:] if history else 'None'}\n"
        f'Message: "{message.content}"'
    )
    result = await generate_response(prompt, "", history=None)
    print(f"[AI-Selfbot] [TONE/CONTEXT AGENT] {result.strip()}")
    return result.strip().lower()


async def reply_validity_agent(reply):
    # Checks if the generated reply is valid and non-empty (step I)
    prompt = (
        "You are an agent that checks if a Discord bot's reply is valid and non-empty. "
        "If the reply is appropriate, non-empty, and makes sense, reply 'yes'. Otherwise, reply 'no'.\n"
        f'Reply: "{reply}"'
    )
    result = await generate_response(prompt, "", history=None)
    print(f"[AI-Selfbot] [REPLY VALIDITY AGENT] {result.strip()}")
    return result.strip().lower().startswith("yes")


async def personalization_agent(reply):
    """
    Modifies the reply to sound like a Thai teenager with imperfect English,
    avoids bot-like language, and adds a personal touch.
    """
    prompt = (
        "You are a Thai teenager chatting in a Discord server. "
        "Your English is not perfect, and you sometimes mix in casual Thai words or slang. "
        "You never reveal you are a bot or AI. "
        "Rewrite the following reply to sound like a real Thai teenager, casual, friendly, and a bit playful. "
        "If the reply is too formal or sounds like a bot, make it more natural and personal. "
        "Never mention you are a bot or AI.\n"
        f'Original reply: "{reply}"\n'
        "Personalized reply:"
    )
    result = await generate_response(prompt, "", history=None)
    print(f"[AI-Selfbot] [PERSONALIZATION AGENT] {result.strip()}")
    return result.strip()
