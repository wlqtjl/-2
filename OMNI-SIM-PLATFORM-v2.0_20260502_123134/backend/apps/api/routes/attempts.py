from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from apps.core import database, models
from schemas.attempt import (
    LevelAttemptCreate, LevelAttemptSubmit, LevelAttemptResponse,
    AchievementResponse, LearnerProfileResponse
)
from apps.api.deps import get_current_user
from datetime import datetime, timezone
from pydantic import BaseModel
from typing import Any

router = APIRouter(prefix="/attempts", tags=["attempts"])


class CheckAnswerRequest(BaseModel):
    attempt_id: int
    question_id: int
    answer: Any


class CheckAnswerResponse(BaseModel):
    correct: bool
    points_awarded: int
    explanation: str | None = None


def _normalize_answer(value):
    """规范化答案以便结构化比对：列表排序，字符串去空白且小写，dict 按键排序。"""
    if isinstance(value, list):
        return sorted([_normalize_answer(v) for v in value], key=lambda x: str(x))
    if isinstance(value, dict):
        return {k: _normalize_answer(value[k]) for k in sorted(value.keys())}
    if isinstance(value, str):
        return value.strip().lower()
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value
    return value


def _is_correct(user_answer, correct_answer) -> bool:
    return _normalize_answer(user_answer) == _normalize_answer(correct_answer)


@router.post("/start", response_model=LevelAttemptResponse)
def start_level_attempt(
    attempt_data: LevelAttemptCreate,
    db: Session = Depends(database.get_db),
    current_user = Depends(get_current_user)
):
    level = db.query(models.Level).filter(models.Level.id == attempt_data.level_id).first()
    if not level:
        raise HTTPException(status_code=404, detail="关卡不存在")

    existing = db.query(models.LevelAttempt).filter(
        models.LevelAttempt.user_id == current_user.id,
        models.LevelAttempt.level_id == attempt_data.level_id,
        models.LevelAttempt.completed == False
    ).first()

    if existing:
        return existing

    new_attempt = models.LevelAttempt(
        user_id=current_user.id,
        level_id=attempt_data.level_id,
        max_score=level.max_score,
        answers={}
    )
    db.add(new_attempt)
    db.commit()
    db.refresh(new_attempt)
    return new_attempt

@router.post("/check", response_model=CheckAnswerResponse)
def check_answer(
    payload: CheckAnswerRequest,
    db: Session = Depends(database.get_db),
    current_user = Depends(get_current_user)
):
    """逐题校验：仅返回是否正确 + 分值 + 解析，不向客户端泄露 correct_answer。"""
    attempt = db.query(models.LevelAttempt).filter(
        models.LevelAttempt.id == payload.attempt_id,
        models.LevelAttempt.user_id == current_user.id,
    ).first()
    if not attempt:
        raise HTTPException(status_code=404, detail="尝试记录不存在")
    if attempt.completed:
        raise HTTPException(status_code=400, detail="该关卡已提交，无法继续作答")

    question = db.query(models.Question).filter(
        models.Question.id == payload.question_id,
        models.Question.level_id == attempt.level_id,
    ).first()
    if not question:
        raise HTTPException(status_code=404, detail="题目不存在或不属于该关卡")

    correct = _is_correct(payload.answer, question.correct_answer)
    try:
        difficulty = int(question.difficulty or 1)
    except (TypeError, ValueError):
        difficulty = 1
    points = int(getattr(question, "points", None) or (difficulty * 10)) if correct else 0

    return CheckAnswerResponse(
        correct=correct,
        points_awarded=points,
        explanation=question.explanation,
    )


@router.post("/submit", response_model=LevelAttemptResponse)
def submit_level_attempt(
    submit_data: LevelAttemptSubmit,
    db: Session = Depends(database.get_db),
    current_user = Depends(get_current_user)
):
    attempt = db.query(models.LevelAttempt).filter(
        models.LevelAttempt.id == submit_data.attempt_id,
        models.LevelAttempt.user_id == current_user.id
    ).first()

    if not attempt:
        raise HTTPException(status_code=404, detail="尝试记录不存在")

    if attempt.completed:
        raise HTTPException(status_code=400, detail="该关卡已提交")

    questions = db.query(models.Question).filter(models.Question.level_id == attempt.level_id).all()

    score = 0
    for question in questions:
        user_answer = submit_data.answers.get(question.id) or submit_data.answers.get(str(question.id))
        if user_answer is None:
            continue
        if _is_correct(user_answer, question.correct_answer):
            # 优先使用题目自身分值；否则按 难度 * 10 估算
            try:
                difficulty = int(question.difficulty or 1)
            except (TypeError, ValueError):
                difficulty = 1
            score += int(getattr(question, "points", None) or (difficulty * 10))

    attempt.answers = submit_data.answers
    attempt.score = min(score, attempt.max_score)
    attempt.completed = True
    attempt.completed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(attempt)

    check_achievements(db, current_user.id, attempt.level_id)

    return attempt

@router.get("/stats/me")
def get_my_stats(
    db: Session = Depends(database.get_db),
    current_user = Depends(get_current_user)
):
    """获取当前用户的学习统计（总积分、完成关卡数、成就数）"""
    from sqlalchemy import func as sql_func
    total_score = db.query(sql_func.sum(models.LevelAttempt.score)).filter(
        models.LevelAttempt.user_id == current_user.id,
        models.LevelAttempt.completed == True,
    ).scalar() or 0
    completed_levels = db.query(models.LevelAttempt).filter(
        models.LevelAttempt.user_id == current_user.id,
        models.LevelAttempt.completed == True,
    ).count()
    achievement_count = db.query(models.Achievement).filter(
        models.Achievement.user_id == current_user.id,
    ).count()
    return {
        "total_score": total_score,
        "completed_levels": completed_levels,
        "achievement_count": achievement_count,
    }


@router.get("/achievements", response_model=list[AchievementResponse])
def get_user_achievements(
    db: Session = Depends(database.get_db),
    current_user = Depends(get_current_user)
):
    achievements = db.query(models.Achievement).filter(
        models.Achievement.user_id == current_user.id
    ).order_by(models.Achievement.unlocked_at.desc()).all()
    return achievements

def check_achievements(db: Session, user_id: int, level_id: int):
    completed_count = db.query(models.LevelAttempt).filter(
        models.LevelAttempt.user_id == user_id,
        models.LevelAttempt.completed == True
    ).count()

    achievements_to_unlock = []

    if completed_count >= 1:
        achievements_to_unlock.append(("first_blood", "初出茅庐", "完成第一个关卡", "🎯"))
    if completed_count >= 5:
        achievements_to_unlock.append(("five_stars", "五关上将", "完成五个关卡", "⭐"))
    if completed_count >= 10:
        achievements_to_unlock.append(("decathlon", "十项全能", "完成十个关卡", "🏆"))

    level_attempt = db.query(models.LevelAttempt).filter(
        models.LevelAttempt.user_id == user_id,
        models.LevelAttempt.level_id == level_id
    ).first()

    if level_attempt and level_attempt.score >= level_attempt.max_score * 0.9:
        achievements_to_unlock.append(("perfectionist", "完美主义", "获得关卡满分", "💯"))

    for name, title, desc, icon in achievements_to_unlock:
        existing = db.query(models.Achievement).filter(
            models.Achievement.user_id == user_id,
            models.Achievement.name == name
        ).first()

        if not existing:
            achievement = models.Achievement(
                user_id=user_id,
                name=name,
                description=desc,
                icon=icon
            )
            db.add(achievement)

    db.commit()
