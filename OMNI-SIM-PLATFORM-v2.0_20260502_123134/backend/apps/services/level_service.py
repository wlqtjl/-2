from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from ..core.level_engine import LevelStateMachine, LevelState, LevelEvent, create_level_context_from_dsl, LevelContext
from ..core.event_bus import EventBus, EventType
from ..core.database import SessionLocal
from ..core.models import Level, LevelAttempt, User
from datetime import datetime


class LevelService:
    def __init__(self, db: Session):
        self.db = db
        self.event_bus = EventBus()
        self._active_sessions: Dict[str, LevelStateMachine] = {}

    def start_level(self, user_id: int, course_id: int, level_id: int) -> Dict:
        level = self.db.query(Level).filter(Level.id == level_id, Level.course_id == course_id).first()
        if not level:
            raise ValueError(f"Level {level_id} not found")

        session_id = f"{user_id}_{level_id}"

        if session_id in self._active_sessions:
            return {"success": False, "message": "Level already in progress"}

        level_dsl = level.config or self._get_default_level_dsl(level)
        context = create_level_context_from_dsl(level_dsl, user_id, level_id, course_id)
        state_machine = LevelStateMachine(context)

        state_machine.register_callback(self._on_state_change)

        self._active_sessions[session_id] = state_machine

        state_machine.send_event(LevelEvent.START)
        state_machine.send_event(LevelEvent.START)

        event = self.event_bus.create_event(
            EventType.LEVEL_START,
            user_id, level_id, course_id,
            {"level_name": level.name}
        )
        self.event_bus.publish(event)

        return {
            "success": True,
            "session_id": session_id,
            "context": self._serialize_context(context),
        }

    def get_level_session(self, session_id: str) -> Optional[Dict]:
        state_machine = self._active_sessions.get(session_id)
        if not state_machine:
            return None
        return self._serialize_context(state_machine.context)

    def answer_task(self, session_id: str, user_answer: Any, task_index: Optional[int] = None) -> Dict:
        state_machine = self._active_sessions.get(session_id)
        if not state_machine:
            raise ValueError("Session not found")

        context = state_machine.context
        current_task = state_machine.get_current_task()

        if not current_task:
            return {"success": False, "message": "No active task"}

        is_correct = self._check_answer(current_task, user_answer)

        if is_correct:
            state_machine.send_event(
                LevelEvent.COMPLETE_TASK,
                task_index=task_index,
                user_answer=user_answer,
                is_correct=is_correct
            )
            event_type = EventType.TASK_COMPLETE
        else:
            state_machine.send_event(
                LevelEvent.FAIL_TASK,
                task_index=task_index,
                user_answer=user_answer
            )
            event_type = EventType.TASK_FAIL

        event = self.event_bus.create_event(
            event_type,
            context.user_id,
            context.level_id,
            context.course_id,
            {
                "task_id": current_task.id,
                "task_content": current_task.content,
                "user_answer": user_answer,
                "is_correct": is_correct,
                "points": current_task.points if is_correct else 0,
            }
        )
        self.event_bus.publish(event)

        if state_machine.get_progress() == 1.0:
            state_machine.send_event(LevelEvent.END)
            self._save_attempt(context)

        return {
            "success": True,
            "is_correct": is_correct,
            "context": self._serialize_context(context),
        }

    def next_task(self, session_id: str) -> Dict:
        state_machine = self._active_sessions.get(session_id)
        if not state_machine:
            raise ValueError("Session not found")

        state_machine.send_event(LevelEvent.NEXT_TASK)
        return {
            "success": True,
            "context": self._serialize_context(state_machine.context),
        }

    def pause_level(self, session_id: str) -> Dict:
        state_machine = self._active_sessions.get(session_id)
        if not state_machine:
            raise ValueError("Session not found")

        state_machine.send_event(LevelEvent.PAUSE)
        return {"success": True}

    def resume_level(self, session_id: str) -> Dict:
        state_machine = self._active_sessions.get(session_id)
        if not state_machine:
            raise ValueError("Session not found")

        state_machine.send_event(LevelEvent.RESUME)
        return {"success": True}

    def _check_answer(self, task, user_answer):
        correct = task.correct_answer
        if task.type == "multiple_choice":
            return set(user_answer) == set(correct)
        elif task.type == "true_false":
            return user_answer == correct
        elif task.type == "fill_blank":
            return str(user_answer).strip() == str(correct).strip()
        else:
            return user_answer == correct

    def _save_attempt(self, context: LevelContext):
        attempt = LevelAttempt(
            user_id=context.user_id,
            level_id=context.level_id,
            score=context.score,
            max_score=context.max_score,
            completed=context.state == LevelState.COMPLETED,
            answers=self._serialize_answers(context),
            started_at=context.started_at,
            completed_at=context.completed_at,
        )
        self.db.add(attempt)
        self.db.commit()

    def _serialize_answers(self, context: LevelContext):
        answers = {}
        for task in context.tasks:
            answers[task.id] = {
                "user_answer": task.user_answer,
                "is_correct": task.is_correct,
                "state": task.state.value,
                "points": task.points,
            }
        return answers

    def _serialize_context(self, context: LevelContext):
        return {
            "user_id": context.user_id,
            "level_id": context.level_id,
            "course_id": context.course_id,
            "current_task_index": context.current_task_index,
            "score": context.score,
            "max_score": context.max_score,
            "state": context.state.value,
            "progress": context.get_progress(),
            "started_at": context.started_at.isoformat() if context.started_at else None,
            "completed_at": context.completed_at.isoformat() if context.completed_at else None,
            "tasks": [
                {
                    "id": t.id,
                    "type": t.type,
                    "content": t.content,
                    "options": t.options,
                    "state": t.state.value,
                    "points": t.points,
                    "is_correct": t.is_correct,
                    "user_answer": t.user_answer,
                }
                for t in context.tasks
            ],
            "npcs": [
                {
                    "id": n.id,
                    "name": n.name,
                    "role": n.role,
                    "dialogue_tree": n.dialogue_tree,
                    "position": n.position,
                }
                for n in context.npcs
            ],
        }

    def _get_default_level_dsl(self, level: Level) -> Dict:
        return {
            "id": str(level.id),
            "name": level.name,
            "description": level.description or "",
            "type": "quiz",
            "difficulty": 1,
            "max_score": level.max_score or 100,
            "tasks": [
                {
                    "id": "1",
                    "type": "single_choice",
                    "content": f"欢迎来到关卡：{level.name}",
                    "options": ["选项 A", "选项 B", "选项 C", "选项 D"],
                    "correct_answer": "选项 A",
                    "points": 10,
                }
            ],
            "npcs": [
                {
                    "id": "guide",
                    "name": "智能导师",
                    "role": "guide",
                    "dialogue_tree": [],
                }
            ],
        }

    def _on_state_change(self, event: LevelEvent, old_state: LevelState, new_state: LevelState):
        pass
