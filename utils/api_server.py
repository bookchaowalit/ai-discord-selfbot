import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

connected_clients = set()


# --- Lifespan event to start the Discord bot ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    from main import run_bot  # Import here to avoid circular import

    asyncio.create_task(run_bot())
    yield  # App runs while this yields
    # (Optional) Cleanup code after yield


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
async def broadcast_log(log: str):
    for ws in list(connected_clients):
        try:
            await ws.send_text(log)
        except Exception:
            connected_clients.remove(ws)
