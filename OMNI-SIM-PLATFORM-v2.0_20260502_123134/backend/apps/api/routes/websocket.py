from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, status
from typing import List, Dict, Set, Optional
from datetime import datetime
import json
import asyncio
import logging
import time
from collections import deque
from apps.core.security import decode_access_token
from apps.api.deps import require_admin

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket 实时通信"])

MAX_WS_MESSAGE_SIZE = 8 * 1024
WS_RATE_WINDOW_SECONDS = 10
WS_MAX_MESSAGES_PER_WINDOW = 30


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, Set[WebSocket]] = {}
        self.group_connections: Dict[str, Set[WebSocket]] = {}
        self.user_rate_windows: Dict[int, deque] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)

    async def disconnect(self, websocket: WebSocket, user_id: int):
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
                self.user_rate_windows.pop(user_id, None)

    def consume_user_message_slot(self, user_id: int) -> bool:
        now = time.monotonic()
        recent_msgs = self.user_rate_windows.setdefault(user_id, deque())
        while recent_msgs and (now - recent_msgs[0]) > WS_RATE_WINDOW_SECONDS:
            recent_msgs.popleft()
        if len(recent_msgs) >= WS_MAX_MESSAGES_PER_WINDOW:
            return False
        recent_msgs.append(now)
        return True

    async def send_personal_message(self, message: dict, user_id: int):
        if user_id in self.active_connections:
            disconnected = set()
            for websocket in self.active_connections[user_id]:
                try:
                    await websocket.send_json(message)
                except (WebSocketDisconnect, RuntimeError, ConnectionError):
                    disconnected.add(websocket)
            for ws in disconnected:
                self.active_connections[user_id].discard(ws)

    async def broadcast(self, message: dict, group: str = None):
        if group:
            connections = self.group_connections.get(group, set())
        else:
            connections = set()
            for conns in self.active_connections.values():
                connections.update(conns)

        disconnected = set()
        for websocket in connections:
            try:
                await websocket.send_json(message)
            except (WebSocketDisconnect, RuntimeError, ConnectionError):
                disconnected.add(websocket)

        for ws in disconnected:
            connections.discard(ws)

    async def join_group(self, websocket: WebSocket, group: str):
        if group not in self.group_connections:
            self.group_connections[group] = set()
        self.group_connections[group].add(websocket)

    async def leave_group(self, websocket: WebSocket, group: str):
        if group in self.group_connections:
            self.group_connections[group].discard(websocket)
            if not self.group_connections[group]:
                del self.group_connections[group]

    def get_online_count(self) -> int:
        return len(self.active_connections)

    def get_group_count(self, group: str) -> int:
        return len(self.group_connections.get(group, set()))


manager = ConnectionManager()


@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int, token: Optional[str] = None):
    # 鉴权：必须携带有效 JWT，且 token.user_id 必须与路由中的 user_id 一致
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    try:
        payload = decode_access_token(token)
    except Exception as e:
        logger.warning(f"WebSocket auth failed for user {user_id}: {e}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    if not payload or payload.get("user_id") != user_id:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect(websocket, user_id)

    await manager.send_personal_message({
        "type": "connected",
        "user_id": user_id,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }, user_id)

    try:
        while True:
            data = await websocket.receive_text()

            if len(data.encode("utf-8")) > MAX_WS_MESSAGE_SIZE:
                await websocket.send_json({
                    "type": "error",
                    "code": "MESSAGE_TOO_LARGE",
                    "message": "消息体过大",
                })
                continue

            if not manager.consume_user_message_slot(user_id):
                await websocket.send_json({
                    "type": "error",
                    "code": "RATE_LIMITED",
                    "message": "消息过于频繁，请稍后再试",
                })
                continue

            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                continue

            await handle_websocket_message(message, user_id, websocket)

    except WebSocketDisconnect:
        await manager.disconnect(websocket, user_id)
        await manager.broadcast({
            "type": "user_left",
            "user_id": user_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    except Exception as e:
        logger.warning(f"WebSocket error for user {user_id}: {e}")
        await manager.disconnect(websocket, user_id)


async def handle_websocket_message(message: dict, user_id: int, websocket: WebSocket):
    msg_type = message.get("type")

    if msg_type == "ping":
        await manager.send_personal_message({
            "type": "pong",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }, user_id)

    elif msg_type == "join_group":
        group = message.get("group")
        if group:
            await manager.join_group(websocket, group)
            await manager.send_personal_message({
                "type": "joined_group",
                "group": group,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }, user_id)

    elif msg_type == "leave_group":
        group = message.get("group")
        if group:
            await manager.leave_group(websocket, group)

    elif msg_type == "game_action":
        action = message.get("action")
        game_id = message.get("game_id")
        await manager.broadcast({
            "type": "game_action",
            "user_id": user_id,
            "action": action,
            "game_id": game_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }, group=f"game_{game_id}")

    elif msg_type == "chat":
        content = message.get("content")
        channel = message.get("channel", "global")
        await manager.broadcast({
            "type": "chat",
            "user_id": user_id,
            "content": content,
            "channel": channel,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }, group=f"chat_{channel}")

    elif msg_type == "typing":
        channel = message.get("channel", "global")
        await manager.broadcast({
            "type": "typing",
            "user_id": user_id,
            "channel": channel,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }, group=f"chat_{channel}")


@router.get("/ws/status")
async def get_websocket_status(_: object = Depends(require_admin)):
    return {
        "online_users": manager.get_online_count(),
        "groups": {
            group: manager.get_group_count(group)
            for group in manager.group_connections.keys()
        }
    }
