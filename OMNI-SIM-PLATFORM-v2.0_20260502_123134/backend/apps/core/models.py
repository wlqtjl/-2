from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum, JSON, Boolean, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base
from enum import Enum as PyEnum

class Tenant(Base):
    __tablename__ = "tenants"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(50), unique=True, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan", passive_deletes=True)
    courses = relationship("Course", back_populates="tenant", cascade="all, delete-orphan", passive_deletes=True)

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"))
    email = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100))
    role = Column(Enum("admin", "instructor", "learner", name="user_role"), default="learner")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    tenant = relationship("Tenant", back_populates="users")
    profiles = relationship("LearnerProfile", back_populates="user", cascade="all, delete-orphan", passive_deletes=True)
    achievements = relationship("Achievement", back_populates="user", cascade="all, delete-orphan", passive_deletes=True)
    memories = relationship("Memory", back_populates="user", cascade="all, delete-orphan", passive_deletes=True)

class MemoryType(str, PyEnum):
    USER = "user"
    FEEDBACK = "feedback"
    PROJECT = "project"
    REFERENCE = "reference"

class LearnerProfile(Base):
    __tablename__ = "learner_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    memory_type = Column(Enum(MemoryType), nullable=False, default=MemoryType.USER)
    data = Column(JSON, nullable=False)
    last_updated = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="profiles")

class Memory(Base):
    __tablename__ = "memories"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    memory_type = Column(Enum(MemoryType), nullable=False, index=True)
    key = Column(String(255), nullable=False)
    value = Column(JSON, nullable=False)
    vector_embedding = Column(JSON)
    meta_data = Column(JSON, default={})
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    user = relationship("User", back_populates="memories")

class Course(Base):
    __tablename__ = "courses"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"))
    name = Column(String(200), nullable=False)
    description = Column(Text)
    status = Column(Enum("draft", "published", "archived", name="course_status"), default="draft")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        Index("ix_courses_tenant_status", "tenant_id", "status"),
    )

    tenant = relationship("Tenant", back_populates="courses")
    levels = relationship("Level", back_populates="course", cascade="all, delete-orphan", passive_deletes=True)

class Level(Base):
    __tablename__ = "levels"
    
    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"))
    name = Column(String(100), nullable=False)
    description = Column(Text)
    order = Column(Integer, default=0)
    max_score = Column(Integer, default=100)
    config = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    course = relationship("Course", back_populates="levels")
    questions = relationship("Question", back_populates="level", cascade="all, delete-orphan", passive_deletes=True)
    attempts = relationship("LevelAttempt", back_populates="level", cascade="all, delete-orphan", passive_deletes=True)

class QuestionType(str, PyEnum):
    SINGLE_CHOICE = "single_choice"
    MULTIPLE_CHOICE = "multiple_choice"
    TRUE_FALSE = "true_false"
    FILL_BLANK = "fill_blank"
    DRAG_DROP = "drag_drop"

class Question(Base):
    __tablename__ = "questions"
    
    id = Column(Integer, primary_key=True, index=True)
    level_id = Column(Integer, ForeignKey("levels.id"))
    type = Column(Enum(QuestionType), nullable=False)
    content = Column(Text, nullable=False)
    options = Column(JSON)
    correct_answer = Column(JSON, nullable=False)
    explanation = Column(Text)
    difficulty = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    level = relationship("Level", back_populates="questions")

class LevelAttempt(Base):
    __tablename__ = "level_attempts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    level_id = Column(Integer, ForeignKey("levels.id"))
    score = Column(Integer, default=0)
    max_score = Column(Integer)
    completed = Column(Boolean, default=False)
    answers = Column(JSON)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))

    __table_args__ = (
        Index("ix_level_attempts_user_completed", "user_id", "completed"),
        Index("ix_level_attempts_user_level", "user_id", "level_id"),
    )

    level = relationship("Level", back_populates="attempts")

class Achievement(Base):
    __tablename__ = "achievements"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String(100), nullable=False)
    description = Column(Text)
    icon = Column(String(255))
    unlocked_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="achievements")


class LeaderboardType(str, PyEnum):
    COURSE = "course"
    GLOBAL = "global"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    ACHIEVEMENT = "achievement"


class LeaderboardEntry(Base):
    __tablename__ = "leaderboard_entries"
    
    id = Column(Integer, primary_key=True, index=True)
    leaderboard_type = Column(Enum(LeaderboardType), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    score = Column(Integer, nullable=False, default=0)
    rank = Column(Integer, nullable=False, default=0)
    period_start = Column(DateTime(timezone=True), nullable=True)
    period_end = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    course = relationship("Course")
    user = relationship("User")


class UserScore(Base):
    __tablename__ = "user_scores"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    score_type = Column(String(50), nullable=False, index=True)
    score = Column(Integer, nullable=False, default=0)
    meta_data = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    user = relationship("User")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    action = Column(String(50), nullable=False, index=True)
    resource_type = Column(String(50), nullable=False, index=True)
    resource_id = Column(Integer, index=True)
    resource_name = Column(String(255))
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    user_name = Column(String(100))
    tenant_id = Column(Integer, ForeignKey("tenants.id"), index=True)
    ip_address = Column(String(50))
    user_agent = Column(String(500))
    status = Column(String(20), default="success")
    message = Column(Text)
    details = Column(JSON)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User")
    tenant = relationship("Tenant")


class UserProgress(Base):
    __tablename__ = "user_progress"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), index=True)
    level_id = Column(Integer, ForeignKey("levels.id"), index=True)
    status = Column(String(20), default="in_progress", index=True)  # in_progress, completed, failed
    score = Column(Integer, default=0)
    attempts = Column(Integer, default=0)
    completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    user = relationship("User")
    course = relationship("Course")
    level = relationship("Level")


# ---------------------------------------------------------------------------
# 场景包 DSL（Scene DSL v1）
# ---------------------------------------------------------------------------

class ScenarioStatus(str, PyEnum):
    DRAFT = "draft"
    REVIEW = "review"
    PUBLISHED = "published"


class Scenario(Base):
    """通用场景包，存储符合 Scene DSL v1 规范的 JSON payload。

    ``scenario_id`` 是对外暴露的 slug（如 ``smartx-hci-deploy-iops-v1``），
    游戏客户端通过 ``GET /api/scenarios/{scenario_id}`` 拉取完整 DSL 数据。
    """
    __tablename__ = "scenarios"

    id = Column(Integer, primary_key=True, index=True)
    scenario_id = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    domain = Column(String(50), index=True)
    difficulty = Column(String(20))
    version = Column(String(20), default="1.0.0")
    status = Column(
        Enum(ScenarioStatus, name="scenario_status"),
        default=ScenarioStatus.DRAFT,
        nullable=False,
        index=True,
    )
    payload = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        Index("ix_scenarios_domain_status", "domain", "status"),
    )
