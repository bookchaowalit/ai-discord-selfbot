# Selfbot Development Rules for FOGO Group

1. **Problem:** AI answers too quickly, making it obvious it's a bot.
   **Solution:** Always add a random delay (e.g., 2–6 seconds, scaled with message length) before sending any AI-generated response to simulate human thinking and typing speed.

2. **Problem:** AI often repeats the same words or phrases in its answers.
   **Solution:** Make the AI read recent chat history and avoid repeating words or phrases from its previous responses. Encourage varied, natural language.

3. **Problem:** Responses feel too formal or robotic for the FOGO group vibe.
   **Solution:** Tune the AI's instructions to use casual, friendly, and slang language that matches the group's style.

4. **Problem:** AI sometimes responds in channels or DMs where it shouldn't.
   **Solution:** Implement toggles to control where the bot is active (channels, DMs, group chats), and manage active channels in `config.yaml` for privacy.

5. **Problem:** Users may want to pause or stop the bot temporarily.
   **Solution:** Provide commands to pause, resume, or shut down the bot as needed, restricted to the owner or allowed users.

6. **Problem:** Users want to customize the AI's behavior or prompt.
   **Solution:** Allow commands to view, set, or clear the AI's prompt for more flexible interactions, but restrict these commands to the owner or allowed users.

7. **Problem:** AI is asked a hard question (e.g., complex math, technical, trivia, history, science, or "book knowledge" questions) that a typical group member wouldn't answer.
   **Solution:** If the AI detects a question that is too difficult, nerdy, or unnatural for a regular user to answer, it should not reply and instead send an alert or log the event for review.

8. **Problem:** AI replies to irrelevant, low-context, or meaningless messages (e.g., just numbers, symbols, or very short messages).
   **Solution:** Add a context relevance check. If the message is too short, only numbers/symbols, or lacks conversational context, the AI should skip replying and log the event.

9. **Problem:** AI sometimes returns an empty string or a generic error message as a reply.
   **Solution:** If the AI returns an empty string or "Sorry, I couldn't generate a response.", do not send anything to chat and log the event for review.

10. **Problem:** Bot replies too frequently in a row, making it look unnatural or bot-like.
    **Solution:** Track consecutive bot replies per channel. If the bot has replied twice in a row, it will wait for another user to chat before replying again. This prevents the bot from dominating the conversation and helps avoid detection.

11. **Problem:** Bot commands can be triggered by anyone, risking accidental or unauthorized use.
    **Solution:** Restrict all sensitive commands (like pause, reload, toggleactive, etc.) to the owner or a list of allowed users, as specified in `config.yaml`. This keeps bot management secure.

12. **Problem:** Active channels and other sensitive settings are changed via chat commands, exposing them to all users.
    **Solution:** Move management of active channels and other sensitive settings to `config.yaml` so only the owner can change them by editing the config file and reloading the bot.

13. **Problem:** Bot does not have a consistent or personalized identity in chat.
    **Solution:** Use a personalized prompt (in `instructions.txt`) so the bot always answers as "Chaowalit from Thailand," with casual, group-appropriate language and personal details.

14. **Problem:** Bot may respond to its own messages or other bots.
    **Solution:** Ignore messages from itself and from other bots to prevent loops and irrelevant replies.

15. **Problem:** Bot may leak sensitive configuration or management details in chat.
    **Solution:** Ensure all sensitive actions (like toggling channels, changing prompts, or reloading config) are only possible via config files or owner-only commands, and never display sensitive data in chat.

---

*Keep improving the selfbot to make it feel more like a real FOGO group member!*
