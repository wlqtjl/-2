from typing import List, Dict, Any, Optional, Set
from enum import Enum
from dataclasses import dataclass, field
import uuid
from datetime import datetime, timezone
import asyncio
from concurrent.futures import ThreadPoolExecutor, Future


class TaskPriority(Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3


class TaskStatus(Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskDependency:
    task_id: str
    dependency_type: str = "complete"


@dataclass
class ScheduledTask:
    id: str
    name: str
    task_type: str
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    dependencies: List[TaskDependency] = field(default_factory=list)
    payload: Dict[str, Any] = field(default_factory=dict)
    result: Any = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    timeout_seconds: Optional[int] = None
    is_read_operation: bool = False


class DependencyGraph:
    def __init__(self):
        self.tasks: Dict[str, ScheduledTask] = {}
        self.dependencies: Dict[str, Set[str]] = {}

    def add_task(self, task: ScheduledTask):
        self.tasks[task.id] = task
        self.dependencies[task.id] = set()

    def add_dependency(self, task_id: str, dependency_id: str):
        if task_id not in self.tasks or dependency_id not in self.tasks:
            raise ValueError("Task not found in graph")
        self.dependencies[task_id].add(dependency_id)

    def get_ready_tasks(self) -> List[ScheduledTask]:
        ready = []
        for task_id, task in self.tasks.items():
            if task.status != TaskStatus.PENDING:
                continue
            all_deps_complete = all(
                self.tasks[dep_id].status in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]
                for dep_id in self.dependencies[task_id]
            )
            if all_deps_complete:
                ready.append(task)
        return sorted(ready, key=lambda t: -t.priority.value)

    def has_cycle(self) -> bool:
        visited = set()
        rec_stack = set()

        def dfs(task_id: str) -> bool:
            visited.add(task_id)
            rec_stack.add(task_id)
            for dep_id in self.dependencies.get(task_id, []):
                if dep_id not in visited:
                    if dfs(dep_id):
                        return True
                elif dep_id in rec_stack:
                    return True
            rec_stack.remove(task_id)
            return False

        for task_id in self.tasks:
            if task_id not in visited:
                if dfs(task_id):
                    return True
        return False


class TaskScheduler:
    def __init__(self, max_workers: int = 4):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.graph = DependencyGraph()
        self.read_queue: List[ScheduledTask] = []
        self.write_queue: List[ScheduledTask] = []
        self.running_tasks: Dict[str, Future] = {}
        self.task_handlers: Dict[str, callable] = {}
        self._is_running = False

    def register_handler(self, task_type: str, handler: callable):
        self.task_handlers[task_type] = handler

    def schedule_task(
        self,
        name: str,
        task_type: str,
        payload: Dict[str, Any] = None,
        dependencies: List[str] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        is_read_operation: bool = False,
        timeout_seconds: int = None,
    ) -> str:
        task_id = str(uuid.uuid4())
        task = ScheduledTask(
            id=task_id,
            name=name,
            task_type=task_type,
            payload=payload or {},
            priority=priority,
            is_read_operation=is_read_operation,
            timeout_seconds=timeout_seconds,
        )

        self.graph.add_task(task)
        if dependencies:
            for dep_id in dependencies:
                self.graph.add_dependency(task_id, dep_id)

        if is_read_operation:
            self.read_queue.append(task)
        else:
            self.write_queue.append(task)

        return task_id

    def start(self):
        self._is_running = True
        asyncio.create_task(self._scheduler_loop())

    def stop(self):
        self._is_running = False
        self.executor.shutdown(wait=False)

    async def _scheduler_loop(self):
        while self._is_running:
            await self._process_queue()
            await asyncio.sleep(0.1)

    async def _process_queue(self):
        ready_tasks = self.graph.get_ready_tasks()

        for task in ready_tasks:
            if task.id in self.running_tasks:
                continue

            if task.task_type not in self.task_handlers:
                print(f"No handler for task type: {task.task_type}")
                continue

            task.status = TaskStatus.QUEUED
            future = self.executor.submit(self._execute_task, task)
            future.add_done_callback(lambda f, tid=task.id: self._on_task_complete(tid, f))
            self.running_tasks[task.id] = future

    def _execute_task(self, task: ScheduledTask):
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now(timezone.utc)

        try:
            handler = self.task_handlers[task.task_type]
            result = handler(task.payload)
            task.result = result
            task.status = TaskStatus.COMPLETED
            return result
        except Exception as e:
            task.error = str(e)
            task.status = TaskStatus.FAILED
            raise
        finally:
            task.completed_at = datetime.now(timezone.utc)

    def _on_task_complete(self, task_id: str, future: Future):
        if task_id in self.running_tasks:
            del self.running_tasks[task_id]

    def get_task_status(self, task_id: str) -> Optional[ScheduledTask]:
        return self.graph.tasks.get(task_id)

    def cancel_task(self, task_id: str):
        task = self.graph.tasks.get(task_id)
        if task and task.status in [TaskStatus.PENDING, TaskStatus.QUEUED]:
            task.status = TaskStatus.CANCELLED
        if task_id in self.running_tasks:
            self.running_tasks[task_id].cancel()


_scheduler_instance = None


def get_scheduler() -> TaskScheduler:
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = TaskScheduler()
    return _scheduler_instance


def init_scheduler(max_workers: int = 4):
    global _scheduler_instance
    _scheduler_instance = TaskScheduler(max_workers=max_workers)
    return _scheduler_instance
