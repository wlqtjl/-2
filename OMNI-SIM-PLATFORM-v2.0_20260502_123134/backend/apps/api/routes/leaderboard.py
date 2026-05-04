from fastapi import APIRouter, Depends, Query
from typing import Optional
from apps.core.leaderboard import leaderboard_service, LeaderboardType
from apps.api.deps import get_current_user, require_admin

router = APIRouter(prefix="/leaderboard", tags=["排行榜系统"])


@router.get("/{leaderboard_type}")
def get_leaderboard(
    leaderboard_type: str,
    course_id: Optional[int] = None,
    limit: int = Query(50, ge=1, le=200),
):
    lb_type = LeaderboardType(leaderboard_type)
    leaderboard = leaderboard_service.get_leaderboard(lb_type, course_id, limit)

    if not leaderboard:
        return {
            "id": leaderboard_type,
            "type": leaderboard_type,
            "name": "排行榜",
            "entries": [],
            "updated_at": None
        }

    return {
        "id": leaderboard.id,
        "type": leaderboard.type,
        "name": leaderboard.name,
        "description": leaderboard.description,
        "entries": [
            {
                "rank": e.rank,
                "user_id": e.user_id,
                "user_name": e.user_name,
                "score": e.score,
                "avatar": e.avatar
            }
            for e in leaderboard.entries
        ],
        "updated_at": leaderboard.updated_at.isoformat() if leaderboard.updated_at else None,
        "period_start": leaderboard.period_start.isoformat() if leaderboard.period_start else None,
        "period_end": leaderboard.period_end.isoformat() if leaderboard.period_end else None
    }


@router.get("/{leaderboard_type}/rank")
def get_user_rank(
    leaderboard_type: str,
    course_id: Optional[int] = None,
    current_user = Depends(get_current_user)
):
    lb_type = LeaderboardType(leaderboard_type)
    rank = leaderboard_service.get_user_rank(lb_type, current_user.id, course_id)

    if rank is None:
        return {"rank": None, "message": "用户未上榜"}

    return {"rank": rank}


@router.get("/{leaderboard_type}/surrounding")
def get_user_surrounding(
    leaderboard_type: str,
    range_size: int = Query(5, ge=1, le=50),
    course_id: Optional[int] = None,
    current_user = Depends(get_current_user)
):
    lb_type = LeaderboardType(leaderboard_type)
    entries = leaderboard_service.get_user_surrounding(
        lb_type, current_user.id, course_id, range_size
    )

    return {
        "entries": [
            {
                "rank": e.rank,
                "user_id": e.user_id,
                "user_name": e.user_name,
                "score": e.score,
                "avatar": e.avatar
            }
            for e in entries
        ]
    }


@router.post("/{leaderboard_type}/score")
def update_score(
    leaderboard_type: str,
    score: int,
    course_id: Optional[int] = None,
    current_user = Depends(require_admin),
):
    leaderboard_service.update_score(
        leaderboard_type=LeaderboardType(leaderboard_type),
        user_id=current_user.id,
        score=score,
        course_id=course_id
    )
    return {"status": "updated"}


@router.get("/user/scores")
def get_user_scores(
    score_type: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    scores = leaderboard_service.get_user_scores(current_user.id, score_type)
    return {"scores": scores}


@router.post("/user/score")
def update_user_score(
    score_type: str,
    score: int,
    current_user = Depends(require_admin),
):
    leaderboard_service.update_user_score(current_user.id, score_type, score)
    return {"status": "updated"}


@router.get("/top")
def get_top_users(
    limit: int = Query(10, ge=1, le=100),
    score_type: str = "total"
):
    top_users = leaderboard_service.get_top_users(limit, score_type)
    return {"users": top_users}
