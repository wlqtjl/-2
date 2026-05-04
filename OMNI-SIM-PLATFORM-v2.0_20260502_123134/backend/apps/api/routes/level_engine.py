from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Any

from ...core.database import get_db
from ...services.level_service import LevelService
from ..deps import get_current_user
from ...core.models import User

router = APIRouter(prefix="/api/levels/engine", tags=["Level Engine"])


def get_level_service(db: Session = Depends(get_db)):
    return LevelService(db)


def _ensure_session_owner(service: LevelService, session_id: str, user: User) -> dict:
    """\u9a8c\u8bc1 session \u5c5e\u4e8e\u5f53\u524d\u7528\u6237\uff08\u7ba1\u7406\u5458\u9664\u5916\uff09\u3002"""
    session = service.get_level_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    owner_id = session.get("user_id")
    if user.role != "admin" and owner_id is not None and owner_id != user.id:
        raise HTTPException(status_code=403, detail="\u65e0\u6743\u8bbf\u95ee\u8be5\u5173\u5361\u4f1a\u8bdd")
    return session


@router.post("/start")
async def start_level(
    course_id: int,
    level_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        service = LevelService(db)
        result = service.start_level(current_user.id, course_id, level_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/session/{session_id}")
async def get_level_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = LevelService(db)
    session = _ensure_session_owner(service, session_id, current_user)
    return {"success": True, "session": session}


@router.post("/session/{session_id}/answer")
async def answer_task(
    session_id: str,
    user_answer: Any,
    task_index: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = LevelService(db)
    _ensure_session_owner(service, session_id, current_user)
    try:
        return service.answer_task(session_id, user_answer, task_index)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/session/{session_id}/next")
async def next_task(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = LevelService(db)
    _ensure_session_owner(service, session_id, current_user)
    try:
        return service.next_task(session_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/session/{session_id}/pause")
async def pause_level(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = LevelService(db)
    _ensure_session_owner(service, session_id, current_user)
    try:
        return service.pause_level(session_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/session/{session_id}/resume")
async def resume_level(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = LevelService(db)
    _ensure_session_owner(service, session_id, current_user)
    try:
        return service.resume_level(session_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
