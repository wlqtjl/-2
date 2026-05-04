from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class LevelAttemptCreate(BaseModel):
    level_id: int

class LevelAttemptSubmit(BaseModel):
    attempt_id: int
    answers: Dict[int, Any]

class LevelAttemptResponse(BaseModel):
    id: int
    user_id: int
    level_id: int
    score: int
    max_score: int
    completed: bool
    answers: Optional[Dict[str, Any]]
    started_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True

class AchievementResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    icon: Optional[str]
    unlocked_at: datetime

    class Config:
        from_attributes = True

class LearnerProfileResponse(BaseModel):
    id: int
    user_id: int
    memory_type: str
    data: Dict[str, Any]
    last_updated: datetime

    class Config:
        from_attributes = True
