from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime

class CourseBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)

class CourseCreate(CourseBase):
    pass

class CourseUpdate(CourseBase):
    status: Optional[str] = None

class CourseResponse(CourseBase):
    id: int
    tenant_id: int
    status: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class LevelBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    order: Optional[int] = Field(0, ge=0, le=10000)
    max_score: Optional[int] = Field(100, ge=0, le=100000)
    config: Optional[dict] = None

class LevelCreate(LevelBase):
    pass

class LevelResponse(LevelBase):
    id: int
    course_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class QuestionBase(BaseModel):
    type: str = Field(..., max_length=32)
    content: str = Field(..., min_length=1, max_length=5000)
    options: Optional[list] = None
    explanation: Optional[str] = Field(None, max_length=5000)
    difficulty: Optional[int] = Field(1, ge=1, le=10)

class QuestionCreate(QuestionBase):
    correct_answer: Any

class QuestionResponse(BaseModel):
    id: int
    level_id: int
    type: str
    content: str
    options: Optional[list] = None
    difficulty: int

    class Config:
        from_attributes = True

class QuestionWithAnswerResponse(BaseModel):
    id: int
    level_id: int
    type: str
    content: str
    options: Optional[list] = None
    correct_answer: Any
    explanation: Optional[str] = None
    difficulty: int

    class Config:
        from_attributes = True

class LevelAttemptResponse(BaseModel):
    id: int
    user_id: int
    level_id: int
    score: int
    max_score: int
    completed: bool
    started_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True
