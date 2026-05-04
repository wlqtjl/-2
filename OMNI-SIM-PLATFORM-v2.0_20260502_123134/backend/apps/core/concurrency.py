import asyncio
from typing import Callable, Optional, Dict, Any, List
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import logging
from functools import wraps
from collections import defaultdict
from enum import Enum
from pydantic import BaseModel
from apps.core.config import settings

logger = logging.getLogger(__name__)


class TaskPriority(str, Enum):
    """任务优先级"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ScheduledTask(BaseModel):
    """调度任务"""
    id: str
    func: Callable
    args: tuple = ()
    kwargs: dict = {}
    priority: TaskPriority = TaskPriority.MEDIUM
    scheduled_time: Optional[datetime] = None
    interval: Optional[timedelta] = None  # 定时任务间隔
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: datetime = datetime.now(timezone.utc)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class TaskScheduler:
    """任务调度器"""
    
    def __init__(self, max_workers: int = 10):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.scheduled_tasks: Dict[str, ScheduledTask] = {}
        self.running_tasks: set = set()
        self.priority_queues = {
            TaskPriority.HIGH: asyncio.PriorityQueue(),
            TaskPriority.MEDIUM: asyncio.PriorityQueue(),
            TaskPriority.LOW: asyncio.PriorityQueue()
        }
        self._shutdown = False
        self._scheduler_task = None
    
    def schedule_task(
        self,
        func: Callable,
        *args,
        priority: TaskPriority = TaskPriority.MEDIUM,
        scheduled_time: Optional[datetime] = None,
        interval: Optional[timedelta] = None,
        **kwargs
    ) -> str:
        """调度任务"""
        task_id = f"task-{datetime.now().timestamp()}"
        
        task = ScheduledTask(
            id=task_id,
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority,
            scheduled_time=scheduled_time,
            interval=interval
        )
        
        self.scheduled_tasks[task_id] = task
        
        # 根据优先级加入队列
        priority_value = {TaskPriority.HIGH: 0, TaskPriority.MEDIUM: 1, TaskPriority.LOW: 2}[priority]
        self.priority_queues[priority].put_nowait((priority_value, task_id))
        
        logger.info(f"Scheduled task {task_id} with priority {priority}")
        return task_id
    
    async def _process_tasks(self):
        """处理任务队列"""
        while not self._shutdown:
            # 按优先级顺序处理
            for priority in [TaskPriority.HIGH, TaskPriority.MEDIUM, TaskPriority.LOW]:
                queue = self.priority_queues[priority]
                if not queue.empty():
                    try:
                        _, task_id = queue.get_nowait()
                        task = self.scheduled_tasks.get(task_id)
                        
                        if task and task.status == TaskStatus.PENDING:
                            await self._execute_task(task)
                    except asyncio.QueueEmpty:
                        continue
            
            await asyncio.sleep(0.1)
    
    async def _execute_task(self, task: ScheduledTask):
        """执行单个任务"""
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now(timezone.utc)
        self.running_tasks.add(task.id)
        
        logger.info(f"Starting task {task.id}")
        
        try:
            if asyncio.iscoroutinefunction(task.func):
                task.result = await task.func(*task.args, **task.kwargs)
            else:
                # 在线程池中执行同步函数
                loop = asyncio.get_event_loop()
                task.result = await loop.run_in_executor(
                    self.executor,
                    lambda: task.func(*task.args, **task.kwargs)
                )
            
            task.status = TaskStatus.COMPLETED
            logger.info(f"Completed task {task.id}")
            
            # 如果是定时任务，重新调度
            if task.interval:
                task.status = TaskStatus.PENDING
                task.scheduled_time = datetime.now(timezone.utc) + task.interval
                priority_value = {TaskPriority.HIGH: 0, TaskPriority.MEDIUM: 1, TaskPriority.LOW: 2}[task.priority]
                self.priority_queues[task.priority].put_nowait((priority_value, task.id))
                
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            logger.error(f"Failed task {task.id}: {str(e)}")
        
        finally:
            task.completed_at = datetime.now(timezone.utc)
            self.running_tasks.discard(task.id)
    
    def start(self):
        """启动调度器"""
        if self._scheduler_task is None:
            self._scheduler_task = asyncio.create_task(self._process_tasks())
            logger.info("Task scheduler started")
    
    def stop(self):
        """停止调度器"""
        self._shutdown = True
        if self._scheduler_task:
            self._scheduler_task.cancel()
        self.executor.shutdown(wait=True)
        logger.info("Task scheduler stopped")
    
    def get_task_status(self, task_id: str) -> Optional[ScheduledTask]:
        """获取任务状态"""
        return self.scheduled_tasks.get(task_id)
    
    def get_running_tasks(self) -> List[ScheduledTask]:
        """获取正在运行的任务"""
        return [self.scheduled_tasks[t] for t in self.running_tasks if t in self.scheduled_tasks]


class RateLimiter:
    """速率限制器"""
    
    def __init__(self, max_requests: int, time_window: timedelta):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests: Dict[str, List[datetime]] = defaultdict(list)
    
    def is_allowed(self, key: str) -> bool:
        """检查是否允许请求"""
        now = datetime.now()
        
        # 清理过期请求记录
        self.requests[key] = [
            req_time for req_time in self.requests[key]
            if now - req_time < self.time_window
        ]
        
        if len(self.requests[key]) < self.max_requests:
            self.requests[key].append(now)
            return True
        
        return False
    
    def get_remaining(self, key: str) -> int:
        """获取剩余请求数"""
        now = datetime.now()
        self.requests[key] = [
            req_time for req_time in self.requests[key]
            if now - req_time < self.time_window
        ]
        return max(0, self.max_requests - len(self.requests[key]))


class SemaphorePool:
    """信号量池"""
    
    def __init__(self, max_concurrent: int = 100):
        self.semaphores: Dict[str, asyncio.Semaphore] = {}
        self.max_concurrent = max_concurrent
    
    def get_semaphore(self, key: str, max_concurrent: int = None) -> asyncio.Semaphore:
        """获取或创建信号量"""
        if key not in self.semaphores:
            self.semaphores[key] = asyncio.Semaphore(max_concurrent or self.max_concurrent)
        return self.semaphores[key]
    
    async def acquire(self, key: str, max_concurrent: int = None):
        """获取信号量"""
        semaphore = self.get_semaphore(key, max_concurrent)
        await semaphore.acquire()
    
    def release(self, key: str):
        """释放信号量"""
        semaphore = self.semaphores.get(key)
        if semaphore:
            semaphore.release()


# 全局实例
task_scheduler = TaskScheduler(max_workers=settings.MAX_WORKERS or 10)
rate_limiter = RateLimiter(max_requests=100, time_window=timedelta(minutes=1))
semaphore_pool = SemaphorePool(max_concurrent=50)


# 装饰器
def async_task(priority: TaskPriority = TaskPriority.MEDIUM):
    """异步任务装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        wrapper._is_async_task = True
        wrapper._priority = priority
        return wrapper
    return decorator


def rate_limited(max_requests: int = 100, time_window_minutes: int = 1):
    """速率限制装饰器"""
    limiter = RateLimiter(max_requests, timedelta(minutes=time_window_minutes))
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 使用请求来源作为key（简化实现）
            key = "global"
            if not limiter.is_allowed(key):
                raise HTTPException(status_code=429, detail="请求过于频繁")
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def concurrent_limited(key: str, max_concurrent: int = 10):
    """并发限制装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            semaphore = semaphore_pool.get_semaphore(key, max_concurrent)
            async with semaphore:
                return await func(*args, **kwargs)
        return wrapper
    return decorator

from fastapi import HTTPException