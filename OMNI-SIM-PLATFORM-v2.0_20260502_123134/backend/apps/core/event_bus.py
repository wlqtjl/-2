from typing import Dict, List, Callable, Any, Optional
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
import uuid


class EventType(Enum):
    LEVEL_START = "level_start"
    LEVEL_PAUSE = "level_pause"
    LEVEL_RESUME = "level_resume"
    LEVEL_COMPLETE = "level_complete"
    LEVEL_FAIL = "level_fail"
    TASK_START = "task_start"
    TASK_COMPLETE = "task_complete"
    TASK_FAIL = "task_fail"
    TASK_SKIP = "task_skip"
    NPC_INTERACT = "npc_interact"
    SCORE_CHANGE = "score_change"
    ACHIEVEMENT_UNLOCK = "achievement_unlock"
    PROGRESS_UPDATE = "progress_update"
    USER_FEEDBACK = "user_feedback"


@dataclass
class Event:
    id: str
    type: EventType
    timestamp: datetime
    user_id: int
    level_id: int
    course_id: int
    payload: Dict[str, Any]


class EventBus:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._subscribers: Dict[EventType, List[Callable[[Event], None]]] = {}
            cls._instance._event_history: List[Event] = []
            cls._instance._max_history = 1000
        return cls._instance

    def subscribe(self, event_type: EventType, callback: Callable[[Event], None]):
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: EventType, callback: Callable[[Event], None]):
        if event_type in self._subscribers:
            self._subscribers[event_type].remove(callback)

    def publish(self, event: Event):
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history = self._event_history[-self._max_history:]
        
        if event.type in self._subscribers:
            for callback in self._subscribers[event.type]:
                try:
                    callback(event)
                except Exception as e:
                    print(f"Error in event callback: {e}")

    def create_event(
        self,
        event_type: EventType,
        user_id: int,
        level_id: int,
        course_id: int,
        payload: Dict[str, Any] = None,
    ) -> Event:
        return Event(
            id=str(uuid.uuid4()),
            type=event_type,
            timestamp=datetime.now(timezone.utc),
            user_id=user_id,
            level_id=level_id,
            course_id=course_id,
            payload=payload or {},
        )

    def get_event_history(
        self,
        user_id: Optional[int] = None,
        event_type: Optional[EventType] = None,
        limit: int = 100,
    ) -> List[Event]:
        events = self._event_history
        if user_id is not None:
            events = [e for e in events if e.user_id == user_id]
        if event_type is not None:
            events = [e for e in events if e.type == event_type]
        return events[-limit:]

    def clear_history(self):
        self._event_history = []


class EventHandlers:
    @staticmethod
    def handle_level_start(event: Event):
        print(f"Level started: user={event.user_id}, level={event.level_id}")

    @staticmethod
    def handle_task_complete(event: Event):
        print(f"Task completed: user={event.user_id}, task={event.payload.get('task_id')}, score={event.payload.get('points')}")

    @staticmethod
    def handle_achievement_unlock(event: Event):
        print(f"Achievement unlocked: user={event.user_id}, achievement={event.payload.get('achievement')}")


def setup_default_handlers(event_bus: EventBus):
    event_bus.subscribe(EventType.LEVEL_START, EventHandlers.handle_level_start)
    event_bus.subscribe(EventType.TASK_COMPLETE, EventHandlers.handle_task_complete)
    event_bus.subscribe(EventType.ACHIEVEMENT_UNLOCK, EventHandlers.handle_achievement_unlock)
