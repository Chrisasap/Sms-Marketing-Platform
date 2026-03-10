"""WebSocket server for real-time updates."""

import json
import logging
from typing import Dict, Set
from fastapi import WebSocket, WebSocketDisconnect
from jose import JWTError
from app.services.auth import decode_token

logger = logging.getLogger(__name__)

class ConnectionManager:
    """Manages WebSocket connections per tenant and user."""

    def __init__(self):
        # {tenant_id: {user_id: set of websockets}}
        self._connections: Dict[str, Dict[str, Set[WebSocket]]] = {}

    async def connect(self, websocket: WebSocket, tenant_id: str, user_id: str):
        await websocket.accept()
        if tenant_id not in self._connections:
            self._connections[tenant_id] = {}
        if user_id not in self._connections[tenant_id]:
            self._connections[tenant_id][user_id] = set()
        self._connections[tenant_id][user_id].add(websocket)
        logger.info(f"WebSocket connected: tenant={tenant_id}, user={user_id}")

    def disconnect(self, websocket: WebSocket, tenant_id: str, user_id: str):
        if tenant_id in self._connections and user_id in self._connections[tenant_id]:
            self._connections[tenant_id][user_id].discard(websocket)
            if not self._connections[tenant_id][user_id]:
                del self._connections[tenant_id][user_id]
            if not self._connections[tenant_id]:
                del self._connections[tenant_id]
        logger.info(f"WebSocket disconnected: tenant={tenant_id}, user={user_id}")

    async def send_to_tenant(self, tenant_id: str, message: dict):
        """Broadcast to all users in a tenant."""
        if tenant_id in self._connections:
            dead = []
            for user_id, sockets in self._connections[tenant_id].items():
                for ws in sockets:
                    try:
                        await ws.send_json(message)
                    except Exception:
                        dead.append((tenant_id, user_id, ws))
            for t, u, ws in dead:
                self.disconnect(ws, t, u)

    async def send_to_user(self, tenant_id: str, user_id: str, message: dict):
        """Send to a specific user."""
        if tenant_id in self._connections and user_id in self._connections[tenant_id]:
            dead = []
            for ws in self._connections[tenant_id][user_id]:
                try:
                    await ws.send_json(message)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self.disconnect(ws, tenant_id, user_id)

    def get_connection_count(self) -> int:
        count = 0
        for tenant in self._connections.values():
            for user_sockets in tenant.values():
                count += len(user_sockets)
        return count

manager = ConnectionManager()

async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint with JWT authentication."""
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Missing auth token")
        return

    try:
        payload = decode_token(token)
        # Verify this is an access token, not a refresh token
        if payload.get("type") != "access":
            await websocket.close(code=4001, reason="Invalid token type")
            return
        tenant_id = payload.get("tenant_id", "")
        user_id = payload.get("sub", "")
    except JWTError:
        await websocket.close(code=4001, reason="Invalid auth token")
        return

    await manager.connect(websocket, tenant_id, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle client messages (ping/pong, subscribe to channels)
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket, tenant_id, user_id)
