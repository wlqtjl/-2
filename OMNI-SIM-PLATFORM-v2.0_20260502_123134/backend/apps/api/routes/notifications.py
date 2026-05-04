from fastapi import APIRouter, Depends, WebSocket, status
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from apps.core.notification import (
    NotificationService,
    NotificationType,
    NotificationPriority
)
from apps.api.deps import get_current_user, require_admin_or_instructor
from apps.core.security import decode_access_token

router = APIRouter(prefix="/notifications", tags=["通知系统"])

notification_service = NotificationService()


class SendNotificationRequest(BaseModel):
    user_id: int
    notification_type: NotificationType
    title: str
    content: str
    data: Optional[dict] = None
    priority: NotificationPriority = NotificationPriority.NORMAL


@router.post("", status_code=201)
async def send_notification(
    request: SendNotificationRequest,
    current_user = Depends(require_admin_or_instructor)
):
    notification = await notification_service.send_notification(
        user_id=request.user_id,
        notification_type=request.notification_type,
        title=request.title,
        content=request.content,
        data=request.data,
        priority=request.priority
    )
    return {"id": notification.id, "status": "sent"}


@router.get("", response_model=List[dict])
async def get_notifications(
    limit: int = 50,
    unread_only: bool = False,
    current_user = Depends(get_current_user)
):
    notifications = await notification_service.get_notifications(
        user_id=current_user.id,
        limit=limit,
        unread_only=unread_only
    )
    return [
        {
            "id": n.id,
            "type": n.type,
            "title": n.title,
            "content": n.content,
            "data": n.data,
            "priority": n.priority,
            "read": n.read,
            "created_at": n.created_at.isoformat()
        }
        for n in notifications
    ]


@router.get("/unread-count")
async def get_unread_count(current_user = Depends(get_current_user)):
    count = notification_service.get_unread_count(current_user.id)
    return {"count": count}


@router.put("/{notification_id}/read")
async def mark_as_read(
    notification_id: str,
    current_user = Depends(get_current_user)
):
    success = await notification_service.mark_as_read(current_user.id, notification_id)
    return {"success": success}


@router.put("/read-all")
async def mark_all_as_read(current_user = Depends(get_current_user)):
    count = await notification_service.mark_all_as_read(current_user.id)
    return {"count": count}


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: str,
    current_user = Depends(get_current_user)
):
    success = await notification_service.delete_notification(current_user.id, notification_id)
    return {"success": success}


@router.websocket("/ws/{user_id}")
async def notification_websocket(websocket: WebSocket, user_id: int, token: Optional[str] = None):
    # JWT 鉴权：必须携带 token，且 token 中的 user_id 必须与 URL 一致
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    payload = decode_access_token(token)
    if not payload or payload.get("user_id") != user_id:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    queue = await notification_service.subscribe(user_id)

    try:
        while True:
            notification = await queue.get()
            await websocket.send_json({
                "type": "notification",
                "data": {
                    "id": notification.id,
                    "notification_type": notification.type,
                    "title": notification.title,
                    "content": notification.content,
                    "priority": notification.priority
                }
            })
    except Exception:
        await notification_service.unsubscribe(user_id)
