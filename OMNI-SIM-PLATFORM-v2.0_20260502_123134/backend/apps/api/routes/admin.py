from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from datetime import datetime, timedelta, timezone
from sqlalchemy import text
from apps.core.models import User, Course, Level, Question, LevelAttempt, Achievement, LearnerProfile, Memory, Tenant
from apps.core.database import SessionLocal
from apps.core import tenant_context
from apps.api.deps import get_current_user, require_super_admin
from pydantic import BaseModel

router = APIRouter(prefix="/admin", tags=["管理后台"])


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    role: str
    is_active: bool
    created_at: datetime


class CourseResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    status: str
    created_at: datetime
    level_count: int = 0


class LevelResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    order: int
    course_id: int


class DashboardStats(BaseModel):
    total_users: int
    active_users: int
    total_courses: int
    published_courses: int
    total_levels: int
    total_questions: int
    total_attempts: int
    completion_rate: float


class UserManagementResponse(BaseModel):
    users: List[UserResponse]
    total: int
    page: int
    page_size: int


class CourseManagementResponse(BaseModel):
    courses: List[CourseResponse]
    total: int
    page: int
    page_size: int


class AnalyticsSummary(BaseModel):
    date_range: str
    total_users: int
    new_users: int
    total_completions: int
    average_score: float
    top_learners: List[dict]
    popular_courses: List[dict]


def require_admin(current_user: User = Depends(get_current_user)):
    if current_user.role not in ["admin", "instructor"]:
        raise HTTPException(status_code=403, detail="需要管理员或讲师权限")
    return current_user


def apply_tenant_filter(query, model, current_user: User, super_admin_bypass: bool = False):
    """根据当前用户应用租户过滤。

    默认行为：始终按 tenant_id 过滤，避免讲师/管理员越权访问其他租户数据。
    仅当显式传入 ``super_admin_bypass=True`` 且用户角色为 admin 时才放行（用于跨租户运维视图）。
    """
    if super_admin_bypass and current_user.role == "admin":
        return query

    tenant_id = current_user.tenant_id
    if tenant_id and hasattr(model, 'tenant_id'):
        return query.filter(model.tenant_id == tenant_id)
    # 用户没有 tenant_id 时，避免泄露其他租户数据：返回空查询
    if hasattr(model, 'tenant_id'):
        return query.filter(model.tenant_id == -1)
    return query


@router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(current_user: User = Depends(require_admin)):
    """获取仪表盘统计数据（租户隔离）"""
    db = SessionLocal()
    try:
        user_query = apply_tenant_filter(db.query(User), User, current_user)
        course_query = apply_tenant_filter(db.query(Course), Course, current_user)
        level_query = apply_tenant_filter(db.query(Level), Level, current_user)
        question_query = apply_tenant_filter(db.query(Question), Question, current_user)
        attempt_query = apply_tenant_filter(db.query(LevelAttempt), LevelAttempt, current_user)

        total_users = user_query.count()
        active_users = user_query.filter(User.is_active == True).count()
        total_courses = course_query.count()
        published_courses = course_query.filter(Course.status == "published").count()
        total_levels = level_query.count()
        total_questions = question_query.count()
        total_attempts = attempt_query.count()

        completed_attempts = attempt_query.filter(LevelAttempt.completed == True).count()
        completion_rate = completed_attempts / total_attempts if total_attempts > 0 else 0

        return DashboardStats(
            total_users=total_users,
            active_users=active_users,
            total_courses=total_courses,
            published_courses=published_courses,
            total_levels=total_levels,
            total_questions=total_questions,
            total_attempts=total_attempts,
            completion_rate=round(completion_rate, 4)
        )
    finally:
        db.close()


@router.get("/users", response_model=UserManagementResponse)
async def get_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    role: Optional[str] = None,
    search: Optional[str] = None,
    current_user: User = Depends(require_admin)
):
    """获取用户列表（租户隔离）"""
    db = SessionLocal()
    try:
        query = apply_tenant_filter(db.query(User), User, current_user)

        if role:
            query = query.filter(User.role == role)
        if search:
            query = query.filter(
                (User.email.contains(search)) |
                (User.full_name.contains(search))
            )

        total = query.count()
        users = query.order_by(User.created_at.desc())\
            .offset((page - 1) * page_size)\
            .limit(page_size)\
            .all()

        return UserManagementResponse(
            users=[
                UserResponse(
                    id=u.id,
                    email=u.email,
                    full_name=u.full_name,
                    role=u.role,
                    is_active=u.is_active,
                    created_at=u.created_at
                )
                for u in users
            ],
            total=total,
            page=page,
            page_size=page_size
        )
    finally:
        db.close()


@router.put("/users/{user_id}")
async def update_user(
    user_id: int,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    current_user: User = Depends(require_admin)
):
    """更新用户信息（租户隔离）"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")

        if current_user.role != "admin" and user.tenant_id != current_user.tenant_id:
            raise HTTPException(status_code=403, detail="无权修改其他租户的用户")

        if role and role in ["admin", "instructor", "learner"]:
            if current_user.role != "admin" and role == "admin":
                raise HTTPException(status_code=403, detail="只有超级管理员可以设置管理员角色")
            user.role = role
        if is_active is not None:
            user.is_active = is_active

        db.commit()
        return {"success": True, "message": "用户更新成功"}
    finally:
        db.close()


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(require_admin)
):
    """删除用户（租户隔离）"""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="不能删除当前登录用户")

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")

        if current_user.role != "admin" and user.tenant_id != current_user.tenant_id:
            raise HTTPException(status_code=403, detail="无权删除其他租户的用户")

        db.delete(user)
        db.commit()
        return {"success": True, "message": "用户删除成功"}
    finally:
        db.close()


@router.get("/courses", response_model=CourseManagementResponse)
async def get_courses(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    search: Optional[str] = None,
    current_user: User = Depends(require_admin)
):
    """获取课程列表（租户隔离）"""
    db = SessionLocal()
    try:
        query = apply_tenant_filter(db.query(Course), Course, current_user)

        if status:
            query = query.filter(Course.status == status)
        if search:
            query = query.filter(Course.name.contains(search))

        total = query.count()
        courses = query.order_by(Course.created_at.desc())\
            .offset((page - 1) * page_size)\
            .limit(page_size)\
            .all()

        result = []
        for c in courses:
            level_count = db.query(Level).filter(Level.course_id == c.id).count()
            result.append(CourseResponse(
                id=c.id,
                name=c.name,
                description=c.description,
                status=c.status,
                created_at=c.created_at,
                level_count=level_count
            ))

        return CourseManagementResponse(
            courses=result,
            total=total,
            page=page,
            page_size=page_size
        )
    finally:
        db.close()


@router.post("/courses")
async def create_course(
    name: str,
    description: Optional[str] = None,
    current_user: User = Depends(require_admin)
):
    """创建课程（租户隔离）"""
    db = SessionLocal()
    try:
        course = Course(
            name=name,
            description=description,
            status="draft",
            tenant_id=current_user.tenant_id if current_user.role != "admin" else None
        )
        db.add(course)
        db.commit()
        db.refresh(course)
        return {"id": course.id, "name": course.name, "status": course.status, "tenant_id": course.tenant_id}
    finally:
        db.close()


@router.put("/courses/{course_id}")
async def update_course(
    course_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(require_admin)
):
    """更新课程（租户隔离）"""
    db = SessionLocal()
    try:
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            raise HTTPException(status_code=404, detail="课程不存在")

        if current_user.role != "admin" and course.tenant_id != current_user.tenant_id:
            raise HTTPException(status_code=403, detail="无权修改其他租户的课程")

        if name:
            course.name = name
        if description is not None:
            course.description = description
        if status and status in ["draft", "published", "archived"]:
            course.status = status

        db.commit()
        return {"success": True, "message": "课程更新成功"}
    finally:
        db.close()


@router.delete("/courses/{course_id}")
async def delete_course(
    course_id: int,
    current_user: User = Depends(require_admin)
):
    """删除课程"""
    db = SessionLocal()
    try:
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            raise HTTPException(status_code=404, detail="课程不存在")

        db.query(Level).filter(Level.course_id == course_id).delete()
        db.delete(course)
        db.commit()
        return {"success": True, "message": "课程删除成功"}
    finally:
        db.close()


@router.get("/courses/{course_id}/levels")
async def get_course_levels(
    course_id: int,
    current_user: User = Depends(require_admin)
):
    """获取课程关卡"""
    db = SessionLocal()
    try:
        levels = db.query(Level).filter(Level.course_id == course_id).order_by(Level.order).all()
        return [
            {
                "id": l.id,
                "name": l.name,
                "description": l.description,
                "order": l.order,
                "question_count": db.query(Question).filter(Question.level_id == l.id).count()
            }
            for l in levels
        ]
    finally:
        db.close()


@router.post("/courses/{course_id}/levels")
async def create_level(
    course_id: int,
    name: str,
    description: Optional[str] = None,
    current_user: User = Depends(require_admin)
):
    """创建关卡"""
    db = SessionLocal()
    try:
        max_order = db.query(Level).filter(Level.course_id == course_id).count()
        level = Level(course_id=course_id, name=name, description=description, order=max_order)
        db.add(level)
        db.commit()
        db.refresh(level)
        return {"id": level.id, "name": level.name, "order": level.order}
    finally:
        db.close()


@router.delete("/levels/{level_id}")
async def delete_level(
    level_id: int,
    current_user: User = Depends(require_admin)
):
    """删除关卡"""
    db = SessionLocal()
    try:
        level = db.query(Level).filter(Level.id == level_id).first()
        if not level:
            raise HTTPException(status_code=404, detail="关卡不存在")

        db.query(Question).filter(Question.level_id == level_id).delete()
        db.delete(level)
        db.commit()
        return {"success": True, "message": "关卡删除成功"}
    finally:
        db.close()


@router.get("/analytics/summary")
async def get_analytics_summary(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(require_admin)
):
    """获取分析摘要"""
    db = SessionLocal()
    try:
        start_date = datetime.now(timezone.utc) - timedelta(days=days)

        total_users = db.query(User).count()
        new_users = db.query(User).filter(User.created_at >= start_date).count()

        total_completions = db.query(LevelAttempt).filter(
            LevelAttempt.completed == True,
            LevelAttempt.completed_at >= start_date
        ).count() if hasattr(LevelAttempt, 'completed_at') else 0

        attempts = db.query(LevelAttempt).filter(LevelAttempt.score.isnot(None)).all()
        average_score = sum(a.score for a in attempts) / len(attempts) if attempts else 0

        top_learners = db.query(
            User.id, User.full_name, User.email
        ).join(LevelAttempt).filter(
            LevelAttempt.completed == True
        ).group_by(User.id).order_by(
            db.func.count(LevelAttempt.id).desc()
        ).limit(5).all()

        popular_courses = db.query(
            Course.id, Course.name, db.func.count(LevelAttempt.id).label('attempt_count')
        ).join(Level).join(LevelAttempt).group_by(Course.id).order_by(
            db.func.count(LevelAttempt.id).desc()
        ).limit(5).all()

        return AnalyticsSummary(
            date_range=f"最近{days}天",
            total_users=total_users,
            new_users=new_users,
            total_completions=total_completions,
            average_score=round(average_score, 2),
            top_learners=[
                {"id": u.id, "name": u.full_name or u.email, "email": u.email}
                for u in top_learners
            ],
            popular_courses=[
                {"id": c.id, "name": c.name, "attempts": c.attempt_count}
                for c in popular_courses
            ]
        )
    finally:
        db.close()


@router.get("/analytics/user-progress")
async def get_user_progress_stats(
    current_user: User = Depends(require_admin)
):
    """获取用户进度统计"""
    db = SessionLocal()
    try:
        total_users = db.query(User).filter(User.role == "learner").count()
        users_with_completions = db.query(LevelAttempt.user_id).filter(
            LevelAttempt.completed == True
        ).distinct().count()

        avg_attempts = db.query(db.func.count(LevelAttempt.id)).scalar() / total_users if total_users > 0 else 0

        recent_activity = db.query(LevelAttempt).order_by(
            LevelAttempt.started_at.desc()
        ).limit(10).all()

        return {
            "total_learners": total_users,
            "active_learners": users_with_completions,
            "engagement_rate": round(users_with_completions / total_users, 4) if total_users > 0 else 0,
            "avg_attempts_per_user": round(avg_attempts, 2),
            "recent_activity": [
                {
                    "user_id": a.user_id,
                    "level_id": a.level_id,
                    "score": a.score,
                    "completed": a.completed,
                    "timestamp": a.started_at.isoformat() if a.started_at else None
                }
                for a in recent_activity
            ]
        }
    finally:
        db.close()


@router.get("/achievements")
async def get_achievements_stats(
    current_user: User = Depends(require_admin)
):
    """获取成就统计"""
    db = SessionLocal()
    try:
        total_achievements = db.query(Achievement).count()
        recent_achievements = db.query(Achievement).order_by(
            Achievement.unlocked_at.desc()
        ).limit(20).all()

        achievement_breakdown = db.query(
            Achievement.name, db.func.count(Achievement.id).label('count')
        ).group_by(Achievement.name).all()

        return {
            "total_achievements": total_achievements,
            "recent_unlock": [
                {
                    "user_id": a.user_id,
                    "achievement": a.name,
                    "unlocked_at": a.unlocked_at.isoformat() if a.unlocked_at else None
                }
                for a in recent_achievements
            ],
            "breakdown": [
                {"name": n, "count": c}
                for n, c in achievement_breakdown
            ]
        }
    finally:
        db.close()


@router.get("/system/health")
async def get_system_health(
    current_user: User = Depends(require_admin)
):
    """获取系统健康状态。每个子系统独立 try，始终返回一致结构，前端无需做形状判断。"""
    db_status = "unknown"
    redis_status = "unknown"
    cpu_percent = 0.0
    memory_percent = 0.0
    disk_percent = 0.0

    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception:
        db_status = "unhealthy"
    finally:
        db.close()

    try:
        import redis  # type: ignore
        r = redis.Redis.from_url("redis://localhost:6379/0", socket_connect_timeout=0.5)
        r.ping()
        redis_status = "healthy"
    except Exception:
        redis_status = "unhealthy"

    try:
        import psutil  # type: ignore
        cpu_percent = float(psutil.cpu_percent(interval=None))
        memory_percent = float(psutil.virtual_memory().percent)
        disk_percent = float(psutil.disk_usage('/').percent)
    except Exception:
        pass

    return {
        "database": db_status,
        "redis": redis_status,
        "cpu_percent": cpu_percent,
        "memory_percent": memory_percent,
        "disk_percent": disk_percent,
        "uptime": "N/A",
    }
