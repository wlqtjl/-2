from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from apps.core import database, models
from apps.api.deps import get_current_active_user
from schemas.course import (
    CourseCreate, CourseResponse, LevelCreate, LevelResponse,
    QuestionCreate, QuestionResponse, QuestionWithAnswerResponse
)

router = APIRouter(prefix="/courses", tags=["courses"])

@router.get("/", response_model=list[CourseResponse])
def get_courses(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    query = db.query(models.Course).filter(models.Course.status == "published")
    if current_user.tenant_id:
        query = query.filter(models.Course.tenant_id == current_user.tenant_id)
    return query.all()

@router.get("/{course_id}", response_model=CourseResponse)
def get_course(
    course_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    query = db.query(models.Course).filter(
        models.Course.id == course_id,
        models.Course.status == "published",
    )
    if current_user.tenant_id:
        query = query.filter(models.Course.tenant_id == current_user.tenant_id)
    course = query.first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course

@router.post("/", response_model=CourseResponse)
def create_course(
    course: CourseCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    if current_user.role not in ["admin", "instructor"]:
        raise HTTPException(status_code=403, detail="Not authorized to create courses")

    if not current_user.tenant_id:
        raise HTTPException(status_code=400, detail="当前用户未关联租户")

    new_course = models.Course(
        name=course.name,
        description=course.description,
        tenant_id=current_user.tenant_id,
    )
    db.add(new_course)
    db.commit()
    db.refresh(new_course)
    return new_course

@router.get("/{course_id}/levels", response_model=list[LevelResponse])
def get_course_levels(
    course_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    query = db.query(models.Course).filter(
        models.Course.id == course_id,
        models.Course.status == "published"
    )
    if current_user.tenant_id:
        query = query.filter(models.Course.tenant_id == current_user.tenant_id)
    course = query.first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return sorted(course.levels, key=lambda x: x.order)

@router.post("/{course_id}/levels", response_model=LevelResponse)
def create_level(
    course_id: int,
    level: LevelCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    if current_user.role not in ["admin", "instructor"]:
        raise HTTPException(status_code=403, detail="Not authorized to create levels")

    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if current_user.role != "admin" and current_user.tenant_id and course.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="无权操作其他租户的课程")

    new_level = models.Level(
        name=level.name,
        description=level.description,
        order=level.order,
        max_score=level.max_score,
        config=level.config,
        course_id=course_id
    )
    db.add(new_level)
    db.commit()
    db.refresh(new_level)
    return new_level

@router.get("/{course_id}/levels/{level_id}/questions", response_model=list[QuestionResponse])
def get_level_questions(
    course_id: int,
    level_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    level = db.query(models.Level).filter(
        models.Level.id == level_id,
        models.Level.course_id == course_id
    ).first()
    if not level:
        raise HTTPException(status_code=404, detail="Level not found")
    if current_user.tenant_id and level.course and level.course.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Level not found")
    return level.questions


@router.get("/levels/{level_id}", response_model=LevelResponse)
def get_level_by_id(
    level_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """通过 level_id 直接获取关卡（含 course_id），便于前端不依赖路径推断课程。"""
    level = db.query(models.Level).filter(models.Level.id == level_id).first()
    if not level:
        raise HTTPException(status_code=404, detail="Level not found")
    if current_user.tenant_id and level.course and level.course.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Level not found")
    return level


@router.get("/levels/{level_id}/questions", response_model=list[QuestionResponse])
def get_questions_by_level(
    level_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """通过 level_id 直接获取题目，无需前端拼接 course_id。"""
    level = db.query(models.Level).filter(models.Level.id == level_id).first()
    if not level:
        raise HTTPException(status_code=404, detail="Level not found")
    if current_user.tenant_id and level.course and level.course.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Level not found")
    return level.questions

@router.get("/{course_id}/levels/{level_id}/questions-with-answers", response_model=list[QuestionWithAnswerResponse])
def get_level_questions_with_answers(
    course_id: int,
    level_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    if current_user.role not in ["admin", "instructor"]:
        raise HTTPException(status_code=403, detail="Not authorized to view answers")

    level = db.query(models.Level).filter(
        models.Level.id == level_id,
        models.Level.course_id == course_id
    ).first()
    if not level:
        raise HTTPException(status_code=404, detail="Level not found")
    if current_user.role != "admin" and current_user.tenant_id and level.course and level.course.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Level not found")
    return level.questions

@router.post("/{course_id}/levels/{level_id}/questions", response_model=QuestionResponse)
def create_question(
    course_id: int,
    level_id: int,
    question: QuestionCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    if current_user.role not in ["admin", "instructor"]:
        raise HTTPException(status_code=403, detail="Not authorized to create questions")

    level = db.query(models.Level).filter(
        models.Level.id == level_id,
        models.Level.course_id == course_id
    ).first()
    if not level:
        raise HTTPException(status_code=404, detail="Level not found")
    if current_user.role != "admin" and current_user.tenant_id and level.course and level.course.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="无权操作其他租户的关卡")

    new_question = models.Question(
        type=question.type,
        content=question.content,
        options=question.options,
        correct_answer=question.correct_answer,
        explanation=question.explanation,
        difficulty=question.difficulty,
        level_id=level_id
    )
    db.add(new_question)
    db.commit()
    db.refresh(new_question)
    return new_question
