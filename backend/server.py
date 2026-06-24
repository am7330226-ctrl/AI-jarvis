"""
WebSocket Server for Jarvis Dashboard
======================================
Broadcasts real-time events from the Jarvis backend to the React dashboard.
Events include: state changes, transcript updates, and tool activity logs.
"""

import asyncio
import json
import logging
import threading
from datetime import datetime
from typing import Set

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from backend.config import WEBSOCKET_HOST, WEBSOCKET_PORT

logger = logging.getLogger(__name__)

app = FastAPI(title="Jarvis Dashboard API")

# Allow React dev server to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Connection Manager ────────────────────────────────────────────────────────

class ConnectionManager:
    """Manages all active WebSocket connections."""

    def __init__(self):
        self.active: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        async with self._lock:
            self.active.add(ws)
        logger.info(f"Dashboard connected. Total: {len(self.active)}")

    async def disconnect(self, ws: WebSocket):
        async with self._lock:
            self.active.discard(ws)
        logger.info(f"Dashboard disconnected. Total: {len(self.active)}")

    async def broadcast(self, message: dict):
        """Send a message to all connected clients."""
        data = json.dumps(message)
        dead = set()
        for ws in self.active.copy():
            try:
                await ws.send_text(data)
            except Exception:
                dead.add(ws)
        async with self._lock:
            self.active -= dead


manager = ConnectionManager()

# ─── Singleton broadcaster (used from sync code) ──────────────────────────────

_event_loop: asyncio.AbstractEventLoop = None


def set_event_loop(loop: asyncio.AbstractEventLoop):
    global _event_loop
    _event_loop = loop


def broadcast_event(event_type: str, **payload):
    """
    Thread-safe broadcast from synchronous Jarvis code.
    
    Args:
        event_type: Event type string (e.g., 'status', 'transcript', 'tool_call').
        **payload: Additional event data fields.
    
    Event types:
        - 'status':     state='listening'|'thinking'|'speaking'|'idle'|'executing:{tool}'
        - 'transcript': role='user'|'jarvis', text='...'
        - 'tool_call':  name='tool_name', args={...}, result='...'
        - 'system':     cpu=0.0, ram=0.0, mic_level=0.0
    """
    if _event_loop is None:
        return

    message = {
        "type": event_type,
        "timestamp": datetime.now().isoformat(),
        **payload,
    }

    asyncio.run_coroutine_threadsafe(
        manager.broadcast(message),
        _event_loop,
    )


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Send initial state
        await websocket.send_text(json.dumps({
            "type": "status",
            "state": "idle",
            "timestamp": datetime.now().isoformat(),
        }))
        # Keep alive — wait for disconnect
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket)


@app.get("/health")
async def health():
    return {"status": "online", "connections": len(manager.active)}


# ─── Server runner (in background thread) ─────────────────────────────────────

def start_server_in_background():
    """Start the FastAPI server in a daemon thread."""
    def run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        set_event_loop(loop)
        config = uvicorn.Config(
            app,
            host=WEBSOCKET_HOST,
            port=WEBSOCKET_PORT,
            log_level="warning",
            loop="asyncio",
        )
        server = uvicorn.Server(config)
        loop.run_until_complete(server.serve())

    t = threading.Thread(target=run, daemon=True, name="JarvisDashboardServer")
    t.start()
    logger.info(f"Dashboard WebSocket server started at ws://{WEBSOCKET_HOST}:{WEBSOCKET_PORT}/ws")
