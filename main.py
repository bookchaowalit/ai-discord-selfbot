import os

from dotenv import load_dotenv

load_dotenv()

from utils.api import app as api_app  # FastAPI app
from utils.bot_setup import TOKEN, bot, load_extensions

if __name__ == "__main__":
    import asyncio

    import uvicorn

    # Start both the Discord bot and FastAPI in the same process
    async def main():
        # Start FastAPI server in the background
        config = uvicorn.Config(api_app, host="0.0.0.0", port=8000, log_level="info")
        server = uvicorn.Server(config)
        bot_task = asyncio.create_task(bot.start(TOKEN))
        api_task = asyncio.create_task(server.serve())
        await asyncio.gather(bot_task, api_task)

    asyncio.run(main())
