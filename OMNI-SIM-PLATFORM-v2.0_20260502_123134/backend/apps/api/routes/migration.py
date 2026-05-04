"""SmartX-compatible REST endpoints consumed by the bundled FPS game.

The game (built artefacts under ``backend/static/game``) speaks the SmartX V2V
migration protocol on the ``/api/*`` namespace. We bridge those endpoints into
the OMNI-SIM PLATFORM:

* If the caller forwards a platform JWT (``Authorization: Bearer ...``) on
  ``POST /api/auth/session`` we bind the resulting game session to the
  authenticated platform user and mirror their final score into the platform
  leaderboard (``LeaderboardType.GLOBAL``) and audit log.
* Anonymous play is still supported: the game prompts for a player name and
  scores are recorded under that display name only.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field

from apps.core import database, security
from apps.core.leaderboard import leaderboard_service
from apps.core.models import LeaderboardType, Level, LevelAttempt, User
from apps.migration.store import store


logger = logging.getLogger(__name__)
router = APIRouter(tags=["v2v-migration-game"])


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _resolve_platform_user(authorization: Optional[str]) -> Optional[User]:
    """Best-effort decode of the platform JWT; returns ``None`` on any error."""
    if not authorization:
        return None
    parts = authorization.split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    payload = security.decode_access_token(parts[1].strip())
    if not payload:
        return None
    email = payload.get("sub")
    if not email:
        return None
    db = next(database.get_db())
    try:
        return security.get_user(db, email=email)
    finally:
        db.close()


def _require_session(token: Optional[str]):
    session = store.get_session(token)
    if session is None:
        raise HTTPException(status_code=401, detail="invalid or expired session")
    return session


# ---------------------------------------------------------------------------
# schemas
# ---------------------------------------------------------------------------


class SessionRequest(BaseModel):
    playerName: str = ""


class CreateTaskRequest(BaseModel):
    vmId: str
    vmName: str
    dataTotalGB: float = 0.0


class TransitionRequest(BaseModel):
    state: str
    note: str = ""


class ApplyScoreRequest(BaseModel):
    rule: str
    examples: Optional[list] = None
    delta: Optional[int] = None


class LeaderboardSubmit(BaseModel):
    playerName: Optional[str] = None
    score: int = 0
    taskId: Optional[str] = None
    durationSec: Optional[float] = None
    metadata: Optional[dict] = None


# ---------------------------------------------------------------------------
# auth
# ---------------------------------------------------------------------------


@router.post("/api/auth/session")
def open_session(
    body: SessionRequest,
    request: Request,
    authorization: Optional[str] = Header(default=None),
):
    user = _resolve_platform_user(authorization)
    player_name = (body.playerName or "").strip()
    if user and not player_name:
        player_name = user.full_name or user.email

    session = store.create_session(
        player_name=player_name,
        user_id=user.id if user else None,
    )

    return {
        "token": session.token,
        "playerName": session.player_name,
        "playerId": user.id if user else None,
        "expiresAt": session.expires_at.isoformat() + "Z",
        "boundToPlatformUser": user is not None,
    }


# ---------------------------------------------------------------------------
# migration tasks
# ---------------------------------------------------------------------------


@router.post("/api/migration/tasks")
def create_task(
    body: CreateTaskRequest,
    x_session_token: Optional[str] = Header(default=None),
):
    session = _require_session(x_session_token)
    task = store.create_task(
        vm_id=body.vmId, vm_name=body.vmName,
        data_total_gb=body.dataTotalGB,
        owner_session=session.token,
    )
    return task.to_dict()


@router.post("/api/migration/tasks/{task_id}/transition")
def transition_task(
    task_id: str, body: TransitionRequest,
    x_session_token: Optional[str] = Header(default=None),
):
    _require_session(x_session_token)
    try:
        task = store.transition(task_id, body.state, body.note)
    except KeyError:
        raise HTTPException(status_code=404, detail="task not found")
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return task.to_dict()


@router.post("/api/migration/tasks/{task_id}/score/apply")
def apply_score(
    task_id: str, body: ApplyScoreRequest,
    x_session_token: Optional[str] = Header(default=None),
):
    _require_session(x_session_token)
    try:
        task = store.apply_score(
            task_id, rule=body.rule,
            examples=body.examples, delta=body.delta,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="task not found")
    return task.to_dict()


@router.post("/api/migration/tasks/{task_id}/resume")
def resume_task(
    task_id: str,
    x_session_token: Optional[str] = Header(default=None),
):
    _require_session(x_session_token)
    try:
        task = store.resume(task_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="task not found")
    return task.to_dict()


@router.get("/api/migration/tasks/{task_id}/checkpoints")
def get_checkpoints(
    task_id: str,
    x_session_token: Optional[str] = Header(default=None),
):
    _require_session(x_session_token)
    task = store.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    return {
        "taskId": task.id,
        "state": task.state,
        "checkpoints": list(task.checkpoints),
        "scoreBreakdown": list(task.score_breakdown),
    }


# ---------------------------------------------------------------------------
# leaderboard bridge
# ---------------------------------------------------------------------------


@router.post("/api/leaderboard")
def submit_leaderboard(
    body: LeaderboardSubmit,
    x_session_token: Optional[str] = Header(default=None),
):
    session = _require_session(x_session_token)
    score = max(0, int(body.score or 0))
    player_name = (body.playerName or session.player_name or "").strip() or "anonymous"

    if session.user_id is not None:
        try:
            leaderboard_service.update_score(
                leaderboard_type=LeaderboardType.GLOBAL,
                user_id=session.user_id,
                score=score,
                course_id=None,
            )
        except Exception as exc:
            logger.warning("leaderboard update failed: %s", exc)

    return {
        "ok": True,
        "playerName": player_name,
        "score": score,
        "boundToPlatformUser": session.user_id is not None,
    }


@router.get("/api/leaderboard")
def fetch_leaderboard(limit: int = 10):
    limit = max(1, min(int(limit), 100))
    leaderboard = leaderboard_service.get_leaderboard(
        LeaderboardType.GLOBAL, course_id=None, limit=limit,
    )
    if not leaderboard:
        return {"entries": [], "updatedAt": None}
    return {
        "entries": [
            {
                "rank": e.rank,
                "playerName": e.user_name,
                "score": e.score,
                "userId": e.user_id,
                "avatar": e.avatar,
            }
            for e in leaderboard.entries
        ],
        "updatedAt": leaderboard.updated_at.isoformat() + "Z"
                    if leaderboard.updated_at else None,
    }


# ---------------------------------------------------------------------------
# level <-> FPS bridge
# ---------------------------------------------------------------------------
#
# Each platform Level can declare an FPS mission template via ``Level.config``::
#
#   {
#       "fps_mission": {
#           "vmId":   "vm-prod-db-01",
#           "vmName": "生产数据库主节点",
#           "dataTotalGB": 250,
#           "passScore": 600,
#           "briefing": "把生产 DB 从 VMware 平台无停机迁移到 SmartX 超融合。"
#       }
#   }
#
# If absent, a sensible default is generated from the level's name/order so
# every newly-created course/level is playable as an FPS run with no extra
# authoring effort.


def _default_mission_for(level: Level) -> dict:
    """Build the legacy ``__GAME_LEVEL__`` payload for a platform level.

    Historically this was hardcoded to V2V (vmId/vmName/dataTotalGB). It now
    pulls those defaults from a mission-pack JSON when one is referenced by
    ``Level.config['mission_pack']`` or ``Level.config['fps_mission']['missionPack']``.
    Pure V2V wording lives in ``backend/static/game/missions/smartx-v2v-fps-v1.json``
    so non-V2V training topics (HCI IOPS, security, ...) can ship without code edits.
    """
    pack = _resolve_mission_pack_for(level)
    if pack:
        meta = pack.get("meta") or {}
        vars_ = meta.get("vars") or {}
        scoring = pack.get("scoring") or {}
        acts = pack.get("acts") or []
        first_briefing = (
            (acts[0].get("narration", {}).get("briefing") if acts else None)
            or level.description
            or f"完成《{level.name}》战役以通关本关卡。"
        )
        return {
            "vmId":        str(vars_.get("vmId") or f"level-{level.id}-vm"),
            "vmName":      str(vars_.get("vmName") or f"{level.name} · 目标系统"),
            "dataTotalGB": int(vars_.get("dataTotalGB") or (100 + ((level.id or 1) * 7) % 400)),
            "passScore":   int(scoring.get("passingScore") or max(int((level.max_score or 100) * 0.6), 1)),
            "briefing":    first_briefing,
            "missionPack": pack.get("id"),
        }

    # No mission pack referenced → fall back to a topic-agnostic default.
    seed = (level.id or 1) * 7
    return {
        "vmId": f"level-{level.id}-vm",
        "vmName": f"{level.name} · 目标系统",
        "dataTotalGB": 100 + (seed % 400),
        "passScore": max(int((level.max_score or 100) * 0.6), 1),
        "briefing": (level.description
                     or f"完成《{level.name}》战役以通关本关卡。"),
    }


# ---------------------------------------------------------------------------
# Mission-pack resolution (FPS Mission DSL v1)
# ---------------------------------------------------------------------------
#
# Mission packs live as static JSON under
#   backend/static/game/missions/<id>.json
# A platform Level can reference one via ``Level.config``::
#
#   { "mission_pack": "smartx-hci-iops-fps-v1" }                     # preferred
#   { "fps_mission":  { "missionPack": "smartx-v2v-fps-v1", ... } }  # legacy
#
# When neither is set, the implicit default is ``smartx-v2v-fps-v1`` (the
# original built-in topic), so existing courses keep working unchanged.

import json as _json
import os as _os
from functools import lru_cache as _lru_cache

_DEFAULT_MISSION_PACK_ID = "smartx-v2v-fps-v1"


def _missions_dir() -> str:
    here = _os.path.dirname(_os.path.abspath(__file__))
    # apps/api/routes/ → backend/
    backend = _os.path.abspath(_os.path.join(here, "..", "..", ".."))
    return _os.path.join(backend, "static", "game", "missions")


@_lru_cache(maxsize=32)
def _load_mission_pack(pack_id: str) -> Optional[dict]:
    """Read a mission-pack JSON by id. Returns ``None`` when not found.

    Cached because mission packs are immutable per release. ``pack_id`` is
    validated against ``[a-z0-9-]`` to prevent path traversal.
    """
    if not pack_id or not all(c.isalnum() or c == "-" for c in pack_id):
        return None
    path = _os.path.join(_missions_dir(), pack_id + ".json")
    if not _os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            return _json.load(fh)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("failed to load mission pack %s: %s", pack_id, exc)
        return None


def _list_mission_packs() -> list[dict]:
    out: list[dict] = []
    base = _missions_dir()
    if not _os.path.isdir(base):
        return out
    for name in sorted(_os.listdir(base)):
        if not name.endswith(".json") or name.startswith("_"):
            continue
        pack_id = name[:-5]
        pack = _load_mission_pack(pack_id)
        if not pack:
            continue
        meta = pack.get("meta") or {}
        out.append({
            "id":       pack.get("id") or pack_id,
            "name":     meta.get("name") or pack_id,
            "subtitle": meta.get("subtitle"),
            "domain":   meta.get("domain"),
            "version":  meta.get("version"),
            "language": meta.get("language"),
            "actCount": len(pack.get("acts") or []),
        })
    return out


def _resolve_mission_pack_for(level: Level) -> Optional[dict]:
    cfg = level.config if isinstance(level.config, dict) else {}
    pack_id = cfg.get("mission_pack")
    if not pack_id and isinstance(cfg.get("fps_mission"), dict):
        pack_id = cfg["fps_mission"].get("missionPack")
    if not pack_id:
        pack_id = _DEFAULT_MISSION_PACK_ID
    return _load_mission_pack(pack_id)



def _level_mission(level: Level) -> dict:
    cfg = level.config or {}
    mission = (cfg.get("fps_mission") if isinstance(cfg, dict) else None) or {}
    out = _default_mission_for(level)
    out.update({k: v for k, v in mission.items() if v is not None})
    return out


class LevelCompleteRequest(BaseModel):
    score: int = 0
    durationSec: Optional[float] = None
    taskId: Optional[str] = None
    metadata: Optional[dict] = None


@router.get("/api/migration/levels/{level_id}/mission")
def get_level_mission(level_id: int):
    """Return FPS mission template for a platform level (used by the game on launch)."""
    db = next(database.get_db())
    try:
        level = db.query(Level).filter(Level.id == level_id).first()
        if not level:
            raise HTTPException(status_code=404, detail="level not found")
        mission = _level_mission(level)
        pack = _resolve_mission_pack_for(level)
        return {
            "levelId":     level.id,
            "courseId":    level.course_id,
            "levelName":   level.name,
            "maxScore":    level.max_score or 100,
            "mission":     mission,
            # FPS Mission DSL v1: surfaces the resolved pack id so the game
            # iframe can be opened with ?missionPack=<id>.
            "missionPack": pack.get("id") if pack else None,
        }
    finally:
        db.close()


# ---------------------------------------------------------------------------
# FPS Mission DSL — public read endpoints
# ---------------------------------------------------------------------------

@router.get("/api/missions")
def list_mission_packs():
    """List available FPS mission packs (id + meta only, no full payload)."""
    return {"missions": _list_mission_packs()}


@router.get("/api/missions/{pack_id}")
def get_mission_pack(pack_id: str):
    """Return the full FPS Mission DSL v1 JSON for a given pack id."""
    pack = _load_mission_pack(pack_id)
    if not pack:
        raise HTTPException(status_code=404, detail=f"mission pack '{pack_id}' not found")
    return pack



@router.post("/api/migration/levels/{level_id}/complete")
def complete_level(
    level_id: int,
    body: LevelCompleteRequest,
    x_session_token: Optional[str] = Header(default=None),
):
    """Game reports mission victory → record a LevelAttempt and update leaderboard.

    Requires a session token bound to a platform user (i.e. the player must
    have entered the game via the platform iframe with their JWT).
    """
    session = _require_session(x_session_token)
    if session.user_id is None:
        raise HTTPException(
            status_code=403,
            detail="anonymous session cannot mark platform level complete",
        )

    db = next(database.get_db())
    try:
        level = db.query(Level).filter(Level.id == level_id).first()
        if not level:
            raise HTTPException(status_code=404, detail="level not found")

        score = max(0, int(body.score or 0))
        max_score = int(level.max_score or 100)
        passed = score >= int(_level_mission(level).get("passScore", max_score * 0.6))

        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)

        attempt = LevelAttempt(
            user_id=session.user_id,
            level_id=level.id,
            score=score,
            max_score=max_score,
            completed=passed,
            answers={
                "fps_task_id": body.taskId,
                "duration_sec": body.durationSec,
                "metadata": body.metadata or {},
                "source": "v2v_fps",
            },
            started_at=now,
            completed_at=now if passed else None,
        )
        db.add(attempt)
        db.commit()
        db.refresh(attempt)

        # mirror score into global + course leaderboards (best-effort)
        try:
            leaderboard_service.update_score(
                leaderboard_type=LeaderboardType.GLOBAL,
                user_id=session.user_id, score=score, course_id=None,
            )
            if level.course_id:
                leaderboard_service.update_score(
                    leaderboard_type=LeaderboardType.COURSE,
                    user_id=session.user_id, score=score,
                    course_id=level.course_id,
                )
        except Exception as exc:  # pragma: no cover
            logger.warning("leaderboard mirror failed: %s", exc)

        return {
            "ok": True,
            "passed": passed,
            "attemptId": attempt.id,
            "levelId": level.id,
            "courseId": level.course_id,
            "score": score,
            "maxScore": max_score,
        }
    finally:
        db.close()
