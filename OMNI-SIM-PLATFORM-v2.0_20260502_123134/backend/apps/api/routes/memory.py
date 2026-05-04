from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from ...core import database
from ...core.models import MemoryType, User
from ...services.memory_service import MemoryService
from ..deps import get_current_active_user
from pydantic import BaseModel, Json

router = APIRouter(prefix="/memory", tags=["memory"])

class MemoryCreate(BaseModel):
    memory_type: MemoryType
    key: str
    value: dict
    metadata: Optional[dict] = None

class UserProfileUpdate(BaseModel):
    learning_style: Optional[str] = None
    difficulty_preference: Optional[str] = None
    goal: Optional[str] = None
    preferred_topics: Optional[List[str]] = None

class LearningFeedbackCreate(BaseModel):
    level_id: int
    feedback_type: str
    feedback_content: str
    score: Optional[int] = None

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/")
async def create_memory(
    data: MemoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    service = MemoryService(db)
    memory = service.store_memory(
        current_user.id,
        data.memory_type,
        data.key,
        data.value,
        data.metadata
    )
    return {
        "success": True,
        "memory_id": memory.id
    }

@router.get("/type/{memory_type}")
async def get_memories_by_type(
    memory_type: MemoryType,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    service = MemoryService(db)
    memories = service.get_memories_by_type(current_user.id, memory_type, limit)
    return {
        "success": True,
        "memories": [
            {
                "id": m.id,
                "key": m.key,
                "value": m.value,
                "metadata": m.metadata,
                "updated_at": m.updated_at.isoformat()
            }
            for m in memories
        ]
    }

@router.get("/search")
async def search_memories(
    query: str,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    service = MemoryService(db)
    memories = service.search_memories(current_user.id, query, limit=limit)
    return {
        "success": True,
        "memories": [
            {
                "id": m.id,
                "type": m.memory_type.value,
                "key": m.key,
                "value": m.value,
                "updated_at": m.updated_at.isoformat()
            }
            for m in memories
        ]
    }

@router.get("/profile")
async def get_user_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    service = MemoryService(db)
    profile = service.get_user_profile(current_user.id)
    return {
        "success": True,
        "profile": profile
    }

@router.put("/profile")
async def update_user_profile(
    data: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    service = MemoryService(db)
    profile_data = {k: v for k, v in data.model_dump().items() if v is not None}
    service.update_user_profile(current_user.id, profile_data)
    return {
        "success": True,
        "message": "Profile updated successfully"
    }

@router.post("/feedback")
async def record_learning_feedback(
    data: LearningFeedbackCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    service = MemoryService(db)
    memory = service.record_learning_feedback(
        current_user.id,
        data.level_id,
        data.feedback_type,
        data.feedback_content,
        data.score
    )
    return {
        "success": True,
        "feedback_id": memory.id
    }

@router.get("/insights")
async def get_learning_insights(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    service = MemoryService(db)
    insights = service.get_learning_insights(current_user.id)
    return {
        "success": True,
        "insights": insights
    }

@router.post("/reference/course/{course_id}")
async def store_course_reference(
    course_id: int,
    content: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    service = MemoryService(db)
    memory = service.store_course_reference(current_user.id, course_id, content)
    return {
        "success": True,
        "reference_id": memory.id
    }

@router.get("/reference/course/{course_id}")
async def get_course_reference(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    service = MemoryService(db)
    reference = service.get_course_reference(current_user.id, course_id)
    return {
        "success": True,
        "reference": reference
    }

@router.delete("/{memory_type}/{key}")
async def delete_memory(
    memory_type: MemoryType,
    key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    service = MemoryService(db)
    deleted = service.delete_memory(current_user.id, memory_type, key)
    return {
        "success": deleted,
        "message": "Memory deleted" if deleted else "Memory not found"
    }
