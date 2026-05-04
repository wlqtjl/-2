from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel
from enum import Enum
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from apps.core.database import SessionLocal
from apps.core.models import LeaderboardEntry as DBLeaderboardEntry, LeaderboardType, User, UserScore


class LeaderboardEntry(BaseModel):
    rank: int
    user_id: int
    user_name: str
    score: int
    avatar: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    @classmethod
    def from_db(cls, db_entry: DBLeaderboardEntry, user: User):
        return cls(
            rank=db_entry.rank,
            user_id=db_entry.user_id,
            user_name=user.full_name or f"用户_{db_entry.user_id}",
            score=db_entry.score,
            avatar=None,
            metadata=None
        )


class Leaderboard(BaseModel):
    id: str
    type: str
    name: str
    description: str
    entries: List[LeaderboardEntry]
    updated_at: datetime
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None


class LeaderboardService:
    def __init__(self):
        self._name_map = {
            LeaderboardType.COURSE: "课程排行榜",
            LeaderboardType.GLOBAL: "全站排行榜",
            LeaderboardType.WEEKLY: "本周排行榜",
            LeaderboardType.MONTHLY: "本月排行榜",
            LeaderboardType.ACHIEVEMENT: "成就排行榜"
        }

    def _get_leaderboard_key(self, leaderboard_type: LeaderboardType, course_id: Optional[int] = None) -> str:
        if course_id:
            return f"{leaderboard_type.value}_{course_id}"
        return leaderboard_type.value

    def _get_period(self, leaderboard_type: LeaderboardType) -> tuple:
        now = datetime.now(timezone.utc)
        period_start = None
        period_end = None

        if leaderboard_type == LeaderboardType.WEEKLY:
            period_start = now - timedelta(days=now.weekday())
            period_end = period_start + timedelta(days=7)
        elif leaderboard_type == LeaderboardType.MONTHLY:
            period_start = now.replace(day=1)
            if now.month == 12:
                period_end = now.replace(year=now.year + 1, month=1, day=1)
            else:
                period_end = now.replace(month=now.month + 1, day=1)

        return period_start, period_end

    def _get_db(self) -> Session:
        return SessionLocal()

    def update_score(
        self,
        leaderboard_type: LeaderboardType,
        user_id: int,
        score: int,
        course_id: Optional[int] = None
    ):
        db = self._get_db()
        try:
            period_start, period_end = self._get_period(leaderboard_type)
            key = self._get_leaderboard_key(leaderboard_type, course_id)

            existing_entry = db.query(DBLeaderboardEntry).filter(
                DBLeaderboardEntry.leaderboard_type == leaderboard_type,
                DBLeaderboardEntry.user_id == user_id,
                DBLeaderboardEntry.course_id == course_id,
                DBLeaderboardEntry.period_start == period_start
            ).first()

            if existing_entry:
                if score > existing_entry.score:
                    existing_entry.score = score
                    existing_entry.updated_at = datetime.now(timezone.utc)
            else:
                new_entry = DBLeaderboardEntry(
                    leaderboard_type=leaderboard_type,
                    course_id=course_id,
                    user_id=user_id,
                    score=score,
                    rank=0,
                    period_start=period_start,
                    period_end=period_end
                )
                db.add(new_entry)

            db.commit()
            self._recalculate_leaderboard(db, leaderboard_type, course_id, period_start)
        finally:
            db.close()

    def _recalculate_leaderboard(
        self,
        db: Session,
        leaderboard_type: LeaderboardType,
        course_id: Optional[int],
        period_start: Optional[datetime] = None
    ):
        query = db.query(DBLeaderboardEntry).filter(
            DBLeaderboardEntry.leaderboard_type == leaderboard_type,
            DBLeaderboardEntry.course_id == course_id
        )

        if period_start:
            query = query.filter(DBLeaderboardEntry.period_start == period_start)

        entries = query.order_by(desc(DBLeaderboardEntry.score)).all()

        for idx, entry in enumerate(entries, 1):
            entry.rank = idx

        db.commit()

    def get_leaderboard(
        self,
        leaderboard_type: LeaderboardType,
        course_id: Optional[int] = None,
        limit: int = 50
    ) -> Optional[Leaderboard]:
        db = self._get_db()
        try:
            period_start, period_end = self._get_period(leaderboard_type)
            key = self._get_leaderboard_key(leaderboard_type, course_id)

            query = db.query(DBLeaderboardEntry).filter(
                DBLeaderboardEntry.leaderboard_type == leaderboard_type,
                DBLeaderboardEntry.course_id == course_id
            )

            if period_start:
                query = query.filter(DBLeaderboardEntry.period_start == period_start)

            db_entries = query.order_by(DBLeaderboardEntry.rank).limit(limit).all()

            entries = []
            for db_entry in db_entries:
                user = db.query(User).filter(User.id == db_entry.user_id).first()
                if user:
                    entries.append(LeaderboardEntry.from_db(db_entry, user))

            name = self._name_map.get(leaderboard_type, "排行榜")

            return Leaderboard(
                id=key,
                type=leaderboard_type.value,
                name=name,
                description=f"{name} - 显示前{limit}名",
                entries=entries,
                updated_at=datetime.now(timezone.utc),
                period_start=period_start,
                period_end=period_end
            )
        finally:
            db.close()

    def get_user_rank(
        self,
        leaderboard_type: LeaderboardType,
        user_id: int,
        course_id: Optional[int] = None
    ) -> Optional[int]:
        db = self._get_db()
        try:
            period_start, _ = self._get_period(leaderboard_type)

            entry = db.query(DBLeaderboardEntry).filter(
                DBLeaderboardEntry.leaderboard_type == leaderboard_type,
                DBLeaderboardEntry.user_id == user_id,
                DBLeaderboardEntry.course_id == course_id,
                DBLeaderboardEntry.period_start == period_start
            ).first()

            return entry.rank if entry else None
        finally:
            db.close()

    def get_user_surrounding(
        self,
        leaderboard_type: LeaderboardType,
        user_id: int,
        course_id: Optional[int] = None,
        range_size: int = 5
    ) -> List[LeaderboardEntry]:
        db = self._get_db()
        try:
            period_start, _ = self._get_period(leaderboard_type)

            entry = db.query(DBLeaderboardEntry).filter(
                DBLeaderboardEntry.leaderboard_type == leaderboard_type,
                DBLeaderboardEntry.user_id == user_id,
                DBLeaderboardEntry.course_id == course_id,
                DBLeaderboardEntry.period_start == period_start
            ).first()

            if not entry:
                return []

            user_rank = entry.rank
            start_rank = max(1, user_rank - range_size)
            end_rank = user_rank + range_size

            surrounding_entries = db.query(DBLeaderboardEntry).filter(
                DBLeaderboardEntry.leaderboard_type == leaderboard_type,
                DBLeaderboardEntry.course_id == course_id,
                DBLeaderboardEntry.period_start == period_start,
                DBLeaderboardEntry.rank >= start_rank,
                DBLeaderboardEntry.rank <= end_rank
            ).order_by(DBLeaderboardEntry.rank).all()

            entries = []
            for db_entry in surrounding_entries:
                user = db.query(User).filter(User.id == db_entry.user_id).first()
                if user:
                    entries.append(LeaderboardEntry.from_db(db_entry, user))

            return entries
        finally:
            db.close()

    def get_user_scores(
        self,
        user_id: int,
        score_type: Optional[str] = None
    ) -> Dict[str, int]:
        db = self._get_db()
        try:
            query = db.query(UserScore).filter(UserScore.user_id == user_id)
            if score_type:
                query = query.filter(UserScore.score_type == score_type)

            scores = {}
            for entry in query.all():
                scores[entry.score_type] = entry.score

            return scores
        finally:
            db.close()

    def update_user_score(
        self,
        user_id: int,
        score_type: str,
        score: int,
        metadata: Optional[Dict[str, Any]] = None
    ):
        db = self._get_db()
        try:
            existing = db.query(UserScore).filter(
                UserScore.user_id == user_id,
                UserScore.score_type == score_type
            ).first()

            if existing:
                existing.score = score
                if metadata:
                    existing.meta_data = metadata
                existing.updated_at = datetime.now(timezone.utc)
            else:
                new_score = UserScore(
                    user_id=user_id,
                    score_type=score_type,
                    score=score,
                    meta_data=metadata or {}
                )
                db.add(new_score)

            db.commit()
        finally:
            db.close()

    def get_top_users(
        self,
        limit: int = 10,
        score_type: str = "total"
    ) -> List[Dict[str, Any]]:
        db = self._get_db()
        try:
            subquery = db.query(
                UserScore.user_id,
                func.sum(UserScore.score).label("total_score")
            ).filter(UserScore.score_type == score_type)\
             .group_by(UserScore.user_id)\
             .subquery()

            top_users = db.query(
                subquery.c.user_id,
                subquery.c.total_score,
                User.full_name
            ).join(User, User.id == subquery.c.user_id)\
             .order_by(desc(subquery.c.total_score))\
             .limit(limit).all()

            return [{
                "user_id": row.user_id,
                "score": row.total_score,
                "user_name": row.full_name or f"用户_{row.user_id}"
            } for row in top_users]
        finally:
            db.close()


leaderboard_service = LeaderboardService()
