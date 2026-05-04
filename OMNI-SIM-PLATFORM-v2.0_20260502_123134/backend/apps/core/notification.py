from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel
from enum import Enum
import asyncio
import json


class NotificationType(str, Enum):
    ACHIEVEMENT = "achievement"
    LEVEL_COMPLETE = "level_complete"
    NEW_MESSAGE = "new_message"
    LEADERBOARD_UPDATE = "leaderboard_update"
    SYSTEM = "system"
    Reminder = "reminder"


class NotificationPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class Notification(BaseModel):
    id: str
    user_id: int
    type: NotificationType
    title: str
    content: str
    data: Optional[Dict[str, Any]] = None
    priority: NotificationPriority = NotificationPriority.NORMAL
    read: bool = False
    created_at: datetime = datetime.now(timezone.utc)


class NotificationChannel(BaseModel):
    user_id: int
    channels: List[str]


class NotificationService:
    def __init__(self):
        self.notifications: Dict[int, List[Notification]] = {}
        self.subscribers: Dict[int, asyncio.Queue] = {}
        self.broadcast_channels: Dict[str, asyncio.Queue] = {}

    async def send_notification(
        self,
        user_id: int,
        notification_type: NotificationType,
        title: str,
        content: str,
        data: Optional[Dict[str, Any]] = None,
        priority: NotificationPriority = NotificationPriority.NORMAL
    ) -> Notification:
        notification = Notification(
            id=f"notif_{user_id}_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
            user_id=user_id,
            type=notification_type,
            title=title,
            content=content,
            data=data,
            priority=priority
        )

        if user_id not in self.notifications:
            self.notifications[user_id] = []
        self.notifications[user_id].insert(0, notification)

        if len(self.notifications[user_id]) > 100:
            self.notifications[user_id] = self.notifications[user_id][:100]

        if user_id in self.subscribers:
            await self.subscribers[user_id].put(notification)

        return notification

    async def broadcast(
        self,
        channel: str,
        notification_type: NotificationType,
        title: str,
        content: str,
        data: Optional[Dict[str, Any]] = None
    ):
        notification = Notification(
            id=f"broadcast_{channel}_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
            user_id=0,
            type=notification_type,
            title=title,
            content=content,
            data=data,
            priority=NotificationPriority.NORMAL
        )

        if channel in self.broadcast_channels:
            await self.broadcast_channels[channel].put(notification)

    async def get_notifications(
        self,
        user_id: int,
        limit: int = 50,
        unread_only: bool = False
    ) -> List[Notification]:
        notifications = self.notifications.get(user_id, [])

        if unread_only:
            notifications = [n for n in notifications if not n.read]

        return notifications[:limit]

    async def mark_as_read(self, user_id: int, notification_id: str) -> bool:
        notifications = self.notifications.get(user_id, [])
        for notif in notifications:
            if notif.id == notification_id:
                notif.read = True
                return True
        return False

    async def mark_all_as_read(self, user_id: int) -> int:
        notifications = self.notifications.get(user_id, [])
        count = 0
        for notif in notifications:
            if not notif.read:
                notif.read = True
                count += 1
        return count

    async def delete_notification(self, user_id: int, notification_id: str) -> bool:
        notifications = self.notifications.get(user_id, [])
        for i, notif in enumerate(notifications):
            if notif.id == notification_id:
                notifications.pop(i)
                return True
        return False

    async def subscribe(self, user_id: int) -> asyncio.Queue:
        queue = asyncio.Queue(maxsize=100)
        self.subscribers[user_id] = queue
        return queue

    async def unsubscribe(self, user_id: int):
        if user_id in self.subscribers:
            del self.subscribers[user_id]

    async def subscribe_channel(self, channel: str) -> asyncio.Queue:
        queue = asyncio.Queue(maxsize=100)
        self.broadcast_channels[channel] = queue
        return queue

    def get_unread_count(self, user_id: int) -> int:
        notifications = self.notifications.get(user_id, [])
        return sum(1 for n in notifications if not n.read)


notification_service = NotificationService()
