import asyncio
import datetime
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from utils.prompts import (  # Import prompts from prompts.py
    personalization_agent_prompt,
    reply_validity_agent_prompt,
)

connected_clients = set()


# --- Lifespan event to start the Discord bot ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    from main import run_bot  # This import will trigger startup()

    asyncio.create_task(run_bot())
    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.websocket("/ws/logs")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.add(websocket)
    try:
        while True:
            await websocket.receive_text()  # Keep connection alive
    except WebSocketDisconnect:
        connected_clients.remove(websocket)


@app.get("/test-log")
async def test_log():
    await broadcast_log("This is a test log from /test-log endpoint!")
    return {"status": "sent"}


# Utility to broadcast logs
async def broadcast_log(
    log: str,
    channel_id: int = None,
    message_id: int = None,
    channel_name: str = None,
    author_name: str = None,
    server_name: str = None,
    success: bool = True,
):
    now = datetime.datetime.now()
    message = {
        "channel_id": channel_id,
        "message_id": message_id,
        "channel_name": channel_name,
        "log": log,
        "author_name": author_name,
        "timestamp": now.isoformat(),
        "date": now.strftime("%Y-%m-%d"),
        "server_name": server_name,
        "success": success,
    }
    for ws in list(connected_clients):
        try:
            await ws.send_text(json.dumps(message))
        except Exception:
            connected_clients.remove(ws)


# Agent settings with prompts
agent_settings = {
    "reply_validity_agent": {
        "enabled": True,
        "prompt": reply_validity_agent_prompt,
    },
    "personalization_agent": {
        "enabled": True,
        "prompt": personalization_agent_prompt,
    },
}


# Pydantic models for validation
class AgentSetting(BaseModel):
    enabled: bool
    prompt: str


@app.get("/api/agents")
async def get_agents():
    """Get all agent settings."""
    return agent_settings


@app.get("/api/agents/{agent_name}")
async def get_agent(agent_name: str):
    """Get a specific agent's settings."""
    if agent_name not in agent_settings:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent_settings[agent_name]


@app.put("/api/agents/{agent_name}")
async def update_agent(agent_name: str, setting: AgentSetting):
    """Update a specific agent's settings."""
    if agent_name not in agent_settings:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent_settings[agent_name]["enabled"] = setting.enabled
    agent_settings[agent_name]["prompt"] = setting.prompt
    return agent_settings[agent_name]
