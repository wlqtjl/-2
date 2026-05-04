from enum import Enum
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
import uuid


class LevelState(Enum):
    PENDING = "pending"
    LOADING = "loading"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class TaskState(Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"


class LevelEvent(Enum):
    START = "start"
    PAUSE = "pause"
    RESUME = "resume"
    COMPLETE_TASK = "complete_task"
    FAIL_TASK = "fail_task"
    SKIP_TASK = "skip_task"
    NEXT_TASK = "next_task"
    RESTART = "restart"
    END = "end"
    TIMEOUT = "timeout"
    COLLECT_ITEM = "collect_item"
    USE_ITEM = "use_item"
    UNLOCK_ACHIEVEMENT = "unlock_achievement"
    TRIGGER_EVENT = "trigger_event"


class AchievementType(Enum):
    SCORE = "score"
    COMPLETION = "completion"
    SPEED = "speed"
    ACCURACY = "accuracy"
    COLLECTION = "collection"
    SPECIAL = "special"


class AchievementRarity(Enum):
    COMMON = "common"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"


@dataclass
class Task:
    id: str
    type: str
    content: str
    options: Optional[List[str]] = None
    correct_answer: Any = None
    explanation: Optional[str] = None
    difficulty: int = 1
    points: int = 10
    required: bool = True
    hint: Optional[str] = None
    state: TaskState = TaskState.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    user_answer: Any = None
    is_correct: Optional[bool] = None


@dataclass
class Achievement:
    id: str
    name: str
    description: str
    icon: Optional[str] = None
    type: AchievementType = AchievementType.SPECIAL
    rarity: AchievementRarity = AchievementRarity.COMMON
    condition: Optional[Dict[str, Any]] = None
    unlocked: bool = False
    unlocked_at: Optional[datetime] = None
    points: int = 0
    rewards: Optional[List[str]] = None


@dataclass
class CollectibleItem:
    id: str
    name: str
    type: str
    description: Optional[str] = None
    icon: Optional[str] = None
    collected: bool = False
    collected_at: Optional[datetime] = None
    effect: Optional[Dict[str, Any]] = None


@dataclass
class NPC:
    id: str
    name: str
    role: Optional[str] = None
    avatar: Optional[str] = None
    dialogue_tree: List[Dict] = field(default_factory=list)
    position: Optional[Dict[str, float]] = None
    triggered: bool = False


@dataclass
class LevelContext:
    user_id: int
    level_id: int
    course_id: int
    current_task_index: int = 0
    score: int = 0
    max_score: int = 100
    tasks: List[Task] = field(default_factory=list)
    npcs: List[NPC] = field(default_factory=list)
    achievements: List[Achievement] = field(default_factory=list)
    collectibles: List[CollectibleItem] = field(default_factory=list)
    collected_items: List[str] = field(default_factory=list)
    unlocked_achievements: List[str] = field(default_factory=list)
    state: LevelState = LevelState.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    lives: int = 3
    hints_used: int = 0
    time_elapsed: int = 0
    combo_streak: int = 0
    max_combo_streak: int = 0


class StateTransition:
    def __init__(self, from_state: LevelState, event: LevelEvent, to_state: LevelState, action: Optional[Callable] = None):
        self.from_state = from_state
        self.event = event
        self.to_state = to_state
        self.action = action


class LevelStateMachine:
    def __init__(self, context: LevelContext):
        self.context = context
        self.transitions: List[StateTransition] = self._build_transitions()
        self._state_history: List[LevelState] = [LevelState.PENDING]
        self._event_callbacks: List[Callable[[LevelEvent, LevelState, LevelState, Dict], None]] = []
        self._achievement_callbacks: List[Callable[[Achievement], None]] = []
        self._collectible_callbacks: List[Callable[[CollectibleItem], None]] = []

    def _build_transitions(self) -> List[StateTransition]:
        return [
            StateTransition(LevelState.PENDING, LevelEvent.START, LevelState.LOADING, self._on_loading),
            StateTransition(LevelState.LOADING, LevelEvent.START, LevelState.READY, self._on_ready),
            StateTransition(LevelState.READY, LevelEvent.START, LevelState.IN_PROGRESS, self._on_start),
            StateTransition(LevelState.IN_PROGRESS, LevelEvent.PAUSE, LevelState.PAUSED, self._on_pause),
            StateTransition(LevelState.PAUSED, LevelEvent.RESUME, LevelState.IN_PROGRESS, self._on_resume),
            StateTransition(LevelState.IN_PROGRESS, LevelEvent.COMPLETE_TASK, LevelState.IN_PROGRESS, self._on_task_complete),
            StateTransition(LevelState.IN_PROGRESS, LevelEvent.FAIL_TASK, LevelState.IN_PROGRESS, self._on_task_fail),
            StateTransition(LevelState.IN_PROGRESS, LevelEvent.SKIP_TASK, LevelState.IN_PROGRESS, self._on_task_skip),
            StateTransition(LevelState.IN_PROGRESS, LevelEvent.NEXT_TASK, LevelState.IN_PROGRESS, self._on_next_task),
            StateTransition(LevelState.IN_PROGRESS, LevelEvent.END, LevelState.COMPLETED, self._on_complete),
            StateTransition(LevelState.IN_PROGRESS, LevelEvent.TIMEOUT, LevelState.TIMEOUT, self._on_timeout),
            StateTransition(LevelState.IN_PROGRESS, LevelEvent.COLLECT_ITEM, LevelState.IN_PROGRESS, self._on_collect_item),
            StateTransition(LevelState.IN_PROGRESS, LevelEvent.USE_ITEM, LevelState.IN_PROGRESS, self._on_use_item),
            StateTransition(LevelState.IN_PROGRESS, LevelEvent.UNLOCK_ACHIEVEMENT, LevelState.IN_PROGRESS, self._on_unlock_achievement),
            StateTransition(LevelState.COMPLETED, LevelEvent.RESTART, LevelState.PENDING, self._on_restart),
            StateTransition(LevelState.FAILED, LevelEvent.RESTART, LevelState.PENDING, self._on_restart),
            StateTransition(LevelState.TIMEOUT, LevelEvent.RESTART, LevelState.PENDING, self._on_restart),
        ]

    def register_callback(self, callback: Callable[[LevelEvent, LevelState, LevelState, Dict], None]):
        self._event_callbacks.append(callback)

    def register_achievement_callback(self, callback: Callable[[Achievement], None]):
        self._achievement_callbacks.append(callback)

    def register_collectible_callback(self, callback: Callable[[CollectibleItem], None]):
        self._collectible_callbacks.append(callback)

    def send_event(self, event: LevelEvent, **kwargs) -> bool:
        result = {"success": False, "message": ""}
        for transition in self.transitions:
            if transition.from_state == self.context.state and transition.event == event:
                old_state = self.context.state
                self.context.state = transition.to_state
                self._state_history.append(transition.to_state)
                
                if transition.action:
                    action_result = transition.action(**kwargs)
                    if action_result:
                        result.update(action_result)
                
                result["success"] = True
                for callback in self._event_callbacks:
                    callback(event, old_state, self.context.state, result)
                return True
        return False

    def _on_loading(self, **kwargs):
        pass

    def _on_ready(self, **kwargs):
        self._initialize_achievements()

    def _on_start(self, **kwargs):
        self.context.started_at = datetime.now(timezone.utc)
        self.context.current_task_index = 0
        self.context.lives = 3
        self.context.score = 0
        self.context.combo_streak = 0
        self.context.max_combo_streak = 0
        self.context.time_elapsed = 0
        
        if self.context.tasks:
            self.context.tasks[0].state = TaskState.ACTIVE
            self.context.tasks[0].started_at = datetime.now(timezone.utc)

    def _on_pause(self, **kwargs):
        pass

    def _on_resume(self, **kwargs):
        pass

    def _on_task_complete(self, task_index: Optional[int] = None, user_answer: Any = None, is_correct: bool = True, **kwargs):
        idx = task_index or self.context.current_task_index
        if 0 <= idx < len(self.context.tasks):
            task = self.context.tasks[idx]
            task.state = TaskState.COMPLETED
            task.completed_at = datetime.now(timezone.utc)
            task.user_answer = user_answer
            task.is_correct = is_correct
            
            if is_correct:
                self.context.combo_streak += 1
                self.context.max_combo_streak = max(self.context.max_combo_streak, self.context.combo_streak)
                
                combo_multiplier = min(1 + (self.context.combo_streak - 1) * 0.1, 2.0)
                points_earned = int(task.points * combo_multiplier)
                self.context.score += points_earned
                
                self._check_achievements()
            else:
                self.context.combo_streak = 0
                self.context.lives -= 1
                
                if self.context.lives <= 0:
                    self.send_event(LevelEvent.END)

    def _on_task_fail(self, task_index: Optional[int] = None, user_answer: Any = None, **kwargs):
        idx = task_index or self.context.current_task_index
        if 0 <= idx < len(self.context.tasks):
            task = self.context.tasks[idx]
            task.state = TaskState.FAILED
            task.completed_at = datetime.now(timezone.utc)
            task.user_answer = user_answer
            task.is_correct = False
            
            self.context.combo_streak = 0
            self.context.lives -= 1
            
            if self.context.lives <= 0:
                self.send_event(LevelEvent.END)

    def _on_task_skip(self, task_index: Optional[int] = None, **kwargs):
        idx = task_index or self.context.current_task_index
        if 0 <= idx < len(self.context.tasks):
            task = self.context.tasks[idx]
            if not task.required:
                task.state = TaskState.SKIPPED

    def _on_next_task(self, **kwargs):
        if self.context.current_task_index < len(self.context.tasks) - 1:
            self.context.current_task_index += 1
            next_task = self.context.tasks[self.context.current_task_index]
            next_task.state = TaskState.ACTIVE
            next_task.started_at = datetime.now(timezone.utc)
        else:
            self.send_event(LevelEvent.END)

    def _on_complete(self, **kwargs):
        self.context.completed_at = datetime.now(timezone.utc)
        self._check_achievements()
        self._check_final_achievements()

    def _on_timeout(self, **kwargs):
        self.context.completed_at = datetime.now(timezone.utc)

    def _on_collect_item(self, item_id: str, **kwargs):
        item = next((c for c in self.context.collectibles if c.id == item_id), None)
        if item and not item.collected:
            item.collected = True
            item.collected_at = datetime.now(timezone.utc)
            self.context.collected_items.append(item_id)
            
            if item.effect:
                self._apply_item_effect(item)
            
            for callback in self._collectible_callbacks:
                callback(item)
            
            self._check_achievements()

    def _on_use_item(self, item_id: str, **kwargs):
        if item_id in self.context.collected_items:
            item = next((c for c in self.context.collectibles if c.id == item_id), None)
            if item and item.effect:
                self._apply_item_effect(item)

    def _on_unlock_achievement(self, achievement_id: str, **kwargs):
        achievement = next((a for a in self.context.achievements if a.id == achievement_id), None)
        if achievement and not achievement.unlocked:
            achievement.unlocked = True
            achievement.unlocked_at = datetime.now(timezone.utc)
            self.context.unlocked_achievements.append(achievement_id)
            self.context.score += achievement.points
            
            for callback in self._achievement_callbacks:
                callback(achievement)

    def _on_restart(self, **kwargs):
        self.context.current_task_index = 0
        self.context.score = 0
        self.context.lives = 3
        self.context.combo_streak = 0
        self.context.max_combo_streak = 0
        self.context.hints_used = 0
        self.context.time_elapsed = 0
        self.context.started_at = None
        self.context.completed_at = None
        
        for task in self.context.tasks:
            task.state = TaskState.PENDING
            task.started_at = None
            task.completed_at = None
            task.user_answer = None
            task.is_correct = None
        
        for item in self.context.collectibles:
            item.collected = False
            item.collected_at = None
        
        self.context.collected_items = []
        
        for achievement in self.context.achievements:
            if achievement.type != AchievementType.SPECIAL:
                achievement.unlocked = False
                achievement.unlocked_at = None
        
        self.context.unlocked_achievements = []

    def _initialize_achievements(self):
        default_achievements = [
            Achievement(
                id="perfect_score",
                name="完美通关",
                description="获得满分",
                icon="🏆",
                type=AchievementType.SCORE,
                rarity=AchievementRarity.EPIC,
                condition={"min_score": 100},
                points=100,
            ),
            Achievement(
                id="speed_demon",
                name="极速通关",
                description="在规定时间内完成关卡",
                icon="⚡",
                type=AchievementType.SPEED,
                rarity=AchievementRarity.RARE,
                condition={"max_time": 300},
                points=50,
            ),
            Achievement(
                id="combo_master",
                name="连击大师",
                description="保持10连击",
                icon="🔥",
                type=AchievementType.ACCURACY,
                rarity=AchievementRarity.RARE,
                condition={"min_combo": 10},
                points=50,
            ),
            Achievement(
                id="no_mistakes",
                name="零失误",
                description="一次都没有答错",
                icon="💎",
                type=AchievementType.ACCURACY,
                rarity=AchievementRarity.EPIC,
                condition={"max_errors": 0},
                points=100,
            ),
            Achievement(
                id="treasure_hunter",
                name="寻宝专家",
                description="收集所有道具",
                icon="💎",
                type=AchievementType.COLLECTION,
                rarity=AchievementRarity.RARE,
                condition={"collect_all": True},
                points=50,
            ),
            Achievement(
                id="first_try",
                name="初次通关",
                description="第一次尝试就通关",
                icon="⭐",
                type=AchievementType.COMPLETION,
                rarity=AchievementRarity.COMMON,
                condition={"attempts": 1},
                points=25,
            ),
        ]
        
        for ach in default_achievements:
            if ach.id not in [a.id for a in self.context.achievements]:
                self.context.achievements.append(ach)

    def _check_achievements(self):
        for achievement in self.context.achievements:
            if achievement.unlocked:
                continue
            
            condition = achievement.condition
            if not condition:
                continue
            
            unlocked = False
            
            if achievement.type == AchievementType.SCORE:
                min_score = condition.get("min_score")
                if min_score and self.context.score >= min_score:
                    unlocked = True
            
            elif achievement.type == AchievementType.SPEED:
                max_time = condition.get("max_time")
                if max_time and self.context.time_elapsed <= max_time:
                    unlocked = True
            
            elif achievement.type == AchievementType.ACCURACY:
                min_combo = condition.get("min_combo")
                max_errors = condition.get("max_errors")
                
                if min_combo and self.context.max_combo_streak >= min_combo:
                    unlocked = True
                elif max_errors is not None:
                    errors = sum(1 for t in self.context.tasks if t.state == TaskState.FAILED)
                    if errors <= max_errors:
                        unlocked = True
            
            elif achievement.type == AchievementType.COLLECTION:
                collect_all = condition.get("collect_all")
                if collect_all:
                    all_collected = all(c.collected for c in self.context.collectibles)
                    if all_collected:
                        unlocked = True
            
            elif achievement.type == AchievementType.COMPLETION:
                attempts = condition.get("attempts")
                if attempts and attempts == 1:
                    completed_count = sum(1 for t in self.context.tasks if t.state == TaskState.COMPLETED)
                    if completed_count == len(self.context.tasks):
                        unlocked = True
            
            if unlocked:
                self._on_unlock_achievement(achievement.id)

    def _check_final_achievements(self):
        for achievement in self.context.achievements:
            if achievement.unlocked:
                continue
            
            if achievement.type == AchievementType.COMPLETION:
                if self.get_progress() >= 1.0:
                    self._on_unlock_achievement(achievement.id)

    def _apply_item_effect(self, item: CollectibleItem):
        effect = item.effect
        if not effect:
            return
        
        effect_type = effect.get("type")
        
        if effect_type == "score_bonus":
            bonus = effect.get("value", 0)
            self.context.score += bonus
        elif effect_type == "extra_life":
            self.context.lives += 1
        elif effect_type == "hint_refill":
            self.context.hints_used = max(0, self.context.hints_used - 1)
        elif effect_type == "time_extension":
            self.context.time_elapsed = max(0, self.context.time_elapsed - effect.get("value", 0))

    def get_current_task(self) -> Optional[Task]:
        if 0 <= self.context.current_task_index < len(self.context.tasks):
            return self.context.tasks[self.context.current_task_index]
        return None

    def get_progress(self) -> float:
        if not self.context.tasks:
            return 0.0
        completed = sum(1 for task in self.context.tasks if task.state in [TaskState.COMPLETED, TaskState.SKIPPED])
        return completed / len(self.context.tasks)

    def can_proceed(self) -> bool:
        for task in self.context.tasks:
            if task.required and task.state not in [TaskState.COMPLETED, TaskState.SKIPPED]:
                return False
        return True

    def get_stats(self) -> Dict[str, Any]:
        completed_tasks = sum(1 for t in self.context.tasks if t.state == TaskState.COMPLETED)
        failed_tasks = sum(1 for t in self.context.tasks if t.state == TaskState.FAILED)
        total_tasks = len(self.context.tasks)
        
        accuracy = (completed_tasks / total_tasks) * 100 if total_tasks > 0 else 0
        
        return {
            "score": self.context.score,
            "max_score": self.context.max_score,
            "progress": self.get_progress() * 100,
            "lives": self.context.lives,
            "combo_streak": self.context.combo_streak,
            "max_combo_streak": self.context.max_combo_streak,
            "hints_used": self.context.hints_used,
            "time_elapsed": self.context.time_elapsed,
            "completed_tasks": completed_tasks,
            "failed_tasks": failed_tasks,
            "total_tasks": total_tasks,
            "accuracy": accuracy,
            "unlocked_achievements": len(self.context.unlocked_achievements),
            "total_achievements": len(self.context.achievements),
            "collected_items": len(self.context.collected_items),
            "total_collectibles": len(self.context.collectibles),
        }

    def use_hint(self) -> bool:
        current_task = self.get_current_task()
        if current_task and current_task.hint:
            self.context.hints_used += 1
            return True
        return False


def create_level_context_from_dsl(level_dsl: Dict, user_id: int, level_id: int, course_id: int) -> LevelContext:
    tasks = []
    for task_data in level_dsl.get("tasks", []):
        tasks.append(Task(
            id=task_data.get("id", str(uuid.uuid4())),
            type=task_data.get("type", "single_choice"),
            content=task_data.get("content", ""),
            options=task_data.get("options"),
            correct_answer=task_data.get("correct_answer"),
            explanation=task_data.get("explanation"),
            difficulty=task_data.get("difficulty", 1),
            points=task_data.get("points", 10),
            required=task_data.get("required", True),
            hint=task_data.get("hint"),
        ))

    npcs = []
    for npc_data in level_dsl.get("npcs", []):
        npcs.append(NPC(
            id=npc_data.get("id", str(uuid.uuid4())),
            name=npc_data.get("name", "NPC"),
            role=npc_data.get("role"),
            avatar=npc_data.get("avatar"),
            dialogue_tree=npc_data.get("dialogue_tree", []),
            position=npc_data.get("position"),
        ))

    achievements = []
    for achievement_data in level_dsl.get("achievements", []):
        achievements.append(Achievement(
            id=achievement_data.get("id", str(uuid.uuid4())),
            name=achievement_data.get("name", "成就"),
            description=achievement_data.get("description", ""),
            icon=achievement_data.get("icon"),
            type=AchievementType(achievement_data.get("type", "special")),
            rarity=AchievementRarity(achievement_data.get("rarity", "common")),
            condition=achievement_data.get("condition"),
            points=achievement_data.get("points", 0),
            rewards=achievement_data.get("rewards"),
        ))

    collectibles = []
    for collectible_data in level_dsl.get("collectibles", []):
        collectibles.append(CollectibleItem(
            id=collectible_data.get("id", str(uuid.uuid4())),
            name=collectible_data.get("name", "道具"),
            type=collectible_data.get("type", "general"),
            description=collectible_data.get("description"),
            icon=collectible_data.get("icon"),
            effect=collectible_data.get("effect"),
        ))

    return LevelContext(
        user_id=user_id,
        level_id=level_id,
        course_id=course_id,
        tasks=tasks,
        npcs=npcs,
        achievements=achievements,
        collectibles=collectibles,
        max_score=level_dsl.get("max_score", 100),
        lives=level_dsl.get("lives", 3),
        metadata={"level_data": level_dsl},
    )


def load_level_from_db(level_id: int, user_id: int, db_session) -> Optional[LevelContext]:
    from apps.core.models import Level, Course, Question
    
    level = db_session.query(Level).filter(Level.id == level_id).first()
    if not level:
        return None
    
    course = db_session.query(Course).filter(Course.id == level.course_id).first()
    
    level_dsl = {
        "id": level.id,
        "name": level.name,
        "description": level.description,
        "max_score": level.max_score,
        "lives": level.lives or 3,
        "tasks": [],
        "npcs": [],
        "achievements": [],
        "collectibles": [],
    }
    
    questions = db_session.query(Question).filter(Question.level_id == level_id).order_by(Question.order).all()
    for q in questions:
        level_dsl["tasks"].append({
            "id": str(q.id),
            "type": q.type or "single_choice",
            "content": q.content,
            "options": q.options,
            "correct_answer": q.correct_answer,
            "explanation": q.explanation,
            "difficulty": q.difficulty or 1,
            "points": q.points or 10,
            "required": q.required,
            "hint": q.hint,
        })
    
    return create_level_context_from_dsl(level_dsl, user_id, level_id, level.course_id)
