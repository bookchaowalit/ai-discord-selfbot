from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from utils.bot_setup import bot

app = FastAPI(title="AI Discord Selfbot API")


class SendMessageRequest(BaseModel):
    channel_id: int
    content: str


@app.get("/thinking")
async def get_thinking():
    result = {}
    for channel_id, queue in bot.message_queues.items():
        result[str(channel_id)] = [
            {
                "author_id": msg.author.id,
                "author_name": getattr(msg.author, "name", ""),
                "content": msg.content,
                "id": msg.id,
            }
            for msg in list(queue)
        ]
    return result


@app.post("/send_message")
async def send_message(req: SendMessageRequest):
    channel = bot.get_channel(req.channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    try:
        await channel.send(req.content)
        return {"status": "sent"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/status")
async def get_status():
    return {
        "paused": bot.paused,
        "active_channels": list(bot.active_channels),
        "message_queues": {str(k): len(v) for k, v in bot.message_queues.items()},
        "user_cooldowns": bot.user_cooldowns,
    }


@app.post("/pause")
async def pause_bot():
    bot.paused = True
    return {"status": "paused"}


@app.post("/unpause")
async def unpause_bot():
    bot.paused = False
    return {"status": "unpaused"}
