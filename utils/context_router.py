from utils.ai_agents import language_is_english_agent


async def route_by_language(message, last_user_message, history, image_url=None):
    """
    Route message to the correct agent based on language.
    Returns a tuple: (is_english, response)
    """
    is_english = await language_is_english_agent(last_user_message)
    if is_english:
        return True, None  # Let main pipeline handle English
    # Here you could call a non-English agent or handler
    # For now, just return False and None
    return False, None
