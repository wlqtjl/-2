"""SmartX V2V migration state machine + in-memory task store.

This service is consumed by the bundled FPS game (`/game/`) which expects the
following endpoints:

  POST /api/auth/session
  POST /api/migration/tasks
  POST /api/migration/tasks/{id}/transition
  POST /api/migration/tasks/{id}/score/apply
  POST /api/migration/tasks/{id}/resume
  GET  /api/migration/tasks/{id}/checkpoints
  POST /api/leaderboard
  GET  /api/leaderboard

The store is intentionally in-memory because each game session is short-lived
and the real persistence layer (course attempts, leaderboard entries, audit
log) is wired up in :mod:`apps.api.routes.migration`.
"""

from __future__ import annotations

import secrets
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional


# Linear V2V flow expected by the game UI. Each state may also transition
# back to ``failed`` (recoverable error) which is then resumable.
TRANSITIONS: Dict[str, List[str]] = {
    "created": ["scanning", "failed"],
    "scanning": ["compatibility", "failed"],
    "compatibility": ["network_mapping", "failed"],
    "network_mapping": ["storage_mapping", "failed"],
    "storage_mapping": ["data_sync", "failed"],
    "data_sync": ["driver_injection", "failed"],
    "driver_injection": ["cutover", "failed"],
    "cutover": ["verification", "failed"],
    "verification": ["completed", "failed"],
    "completed": [],
    "failed": ["scanning", "compatibility", "network_mapping",
               "storage_mapping", "data_sync", "driver_injection",
               "cutover", "verification"],
}


@dataclass
class MigrationTask:
    id: str
    vm_id: str
    vm_name: str
    data_total_gb: float
    state: str = "created"
    note: str = ""
    score: int = 0
    score_breakdown: List[dict] = field(default_factory=list)
    checkpoints: List[dict] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    owner_session: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "vmId": self.vm_id,
            "vmName": self.vm_name,
            "dataTotalGB": self.data_total_gb,
            "state": self.state,
            "note": self.note,
            "score": self.score,
            "scoreBreakdown": list(self.score_breakdown),
            "createdAt": self.created_at.isoformat() + "Z",
            "updatedAt": self.updated_at.isoformat() + "Z",
        }


@dataclass
class GameSession:
    token: str
    player_name: str
    user_id: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: datetime = field(
        default_factory=lambda: datetime.utcnow() + timedelta(hours=8)
    )

    def is_expired(self) -> bool:
        return datetime.utcnow() >= self.expires_at


class MigrationStore:
    """Process-local store. Safe for single-worker dev; for multi-worker
    deploys swap to Redis (interface intentionally minimal)."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._tasks: Dict[str, MigrationTask] = {}
        self._sessions: Dict[str, GameSession] = {}

    # ----- sessions -----

    def create_session(self, player_name: str,
                       user_id: Optional[int] = None) -> GameSession:
        with self._lock:
            token = secrets.token_urlsafe(24)
            session = GameSession(token=token,
                                  player_name=player_name or f"guest-{token[:6]}",
                                  user_id=user_id)
            self._sessions[token] = session
            return session

    def get_session(self, token: Optional[str]) -> Optional[GameSession]:
        if not token:
            return None
        with self._lock:
            session = self._sessions.get(token)
            if session and session.is_expired():
                self._sessions.pop(token, None)
                return None
            return session

    # ----- tasks -----

    def create_task(self, vm_id: str, vm_name: str, data_total_gb: float,
                    owner_session: Optional[str] = None) -> MigrationTask:
        with self._lock:
            task_id = secrets.token_urlsafe(12)
            task = MigrationTask(
                id=task_id, vm_id=vm_id, vm_name=vm_name,
                data_total_gb=float(data_total_gb or 0.0),
                owner_session=owner_session,
            )
            task.checkpoints.append({
                "ts": task.created_at.isoformat() + "Z",
                "state": task.state,
                "note": "task created",
            })
            self._tasks[task_id] = task
            return task

    def get_task(self, task_id: str) -> Optional[MigrationTask]:
        with self._lock:
            return self._tasks.get(task_id)

    def can_transition(self, current: str, target: str) -> bool:
        return target in TRANSITIONS.get(current, [])

    def transition(self, task_id: str, target: str,
                   note: str = "") -> MigrationTask:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                raise KeyError(task_id)
            if not self.can_transition(task.state, target):
                raise ValueError(
                    f"illegal transition: {task.state} -> {target}"
                )
            task.state = target
            task.note = note or ""
            task.updated_at = datetime.utcnow()
            task.checkpoints.append({
                "ts": task.updated_at.isoformat() + "Z",
                "state": target,
                "note": note or "",
            })
            return task

    def resume(self, task_id: str) -> MigrationTask:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                raise KeyError(task_id)
            if task.state != "failed":
                # No-op resume from non-failed state simply records a checkpoint.
                task.checkpoints.append({
                    "ts": datetime.utcnow().isoformat() + "Z",
                    "state": task.state,
                    "note": "resume requested (no-op)",
                })
                return task
            # Resume returns to scanning by default; the next /transition call
            # from the client picks the right step.
            task.state = "scanning"
            task.updated_at = datetime.utcnow()
            task.checkpoints.append({
                "ts": task.updated_at.isoformat() + "Z",
                "state": task.state,
                "note": "resumed from failure",
            })
            return task

    def apply_score(self, task_id: str, rule: str,
                    examples: Optional[list] = None,
                    delta: Optional[int] = None) -> MigrationTask:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                raise KeyError(task_id)
            # Default scoring rule: each successful step contributes 100 pts;
            # callers can override by passing an explicit ``delta``.
            if delta is None:
                rule_key = (rule or "").lower()
                table = {
                    "scan_complete": 100,
                    "compat_pass": 100,
                    "network_mapped": 100,
                    "storage_mapped": 100,
                    "sync_complete": 200,
                    "driver_injected": 100,
                    "cutover_done": 200,
                    "verify_pass": 200,
                    "perfect_run": 500,
                }
                delta = table.get(rule_key, 50)
            task.score = max(0, task.score + int(delta))
            entry = {
                "ts": datetime.utcnow().isoformat() + "Z",
                "rule": rule,
                "examples": examples or [],
                "delta": int(delta),
                "total": task.score,
            }
            task.score_breakdown.append(entry)
            task.updated_at = datetime.utcnow()
            return task


store = MigrationStore()
