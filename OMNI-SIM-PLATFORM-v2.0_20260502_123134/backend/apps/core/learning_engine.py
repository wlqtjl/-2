from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel
from apps.core.database import SessionLocal
from apps.core.models import User, Course, Level, UserProgress, Achievement
from apps.core import tenant_context
import logging

logger = logging.getLogger(__name__)


class LearningPathStatus(str, Enum):
    """学习路径状态"""
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class LearningNodeType(str, Enum):
    """学习节点类型"""
    COURSE = "course"
    LEVEL = "level"
    ASSESSMENT = "assessment"
    SURVEY = "survey"
    CONTENT = "content"


class LearningNode(BaseModel):
    """学习节点"""
    id: str
    type: LearningNodeType
    title: str
    description: Optional[str] = None
    course_id: Optional[int] = None
    level_id: Optional[int] = None
    duration: Optional[int] = None  # 预计时长（分钟）
    prerequisites: List[str] = []
    rewards: Dict[str, Any] = {}


class LearningPath(BaseModel):
    """学习路径"""
    id: str
    name: str
    description: Optional[str] = None
    status: LearningPathStatus = LearningPathStatus.DRAFT
    nodes: List[LearningNode] = []
    created_at: datetime = datetime.now(timezone.utc)
    updated_at: datetime = datetime.now(timezone.utc)


class LearningPathManager:
    """学习路径管理器"""
    
    def __init__(self):
        self.paths: Dict[str, LearningPath] = {}
    
    def create_path(self, name: str, description: str = None) -> LearningPath:
        """创建学习路径"""
        path = LearningPath(
            id=f"path-{datetime.now().timestamp()}",
            name=name,
            description=description
        )
        self.paths[path.id] = path
        return path
    
    def get_path(self, path_id: str) -> Optional[LearningPath]:
        """获取学习路径"""
        return self.paths.get(path_id)
    
    def update_path(self, path_id: str, **kwargs) -> Optional[LearningPath]:
        """更新学习路径"""
        path = self.paths.get(path_id)
        if not path:
            return None
        
        for key, value in kwargs.items():
            if hasattr(path, key):
                setattr(path, key, value)
        
        path.updated_at = datetime.now(timezone.utc)
        return path
    
    def delete_path(self, path_id: str) -> bool:
        """删除学习路径"""
        if path_id in self.paths:
            del self.paths[path_id]
            return True
        return False
    
    def add_node(self, path_id: str, node: LearningNode) -> bool:
        """添加节点到路径"""
        path = self.paths.get(path_id)
        if not path:
            return False
        
        node.id = f"node-{datetime.now().timestamp()}"
        path.nodes.append(node)
        path.updated_at = datetime.now(timezone.utc)
        return True
    
    def remove_node(self, path_id: str, node_id: str) -> bool:
        """从路径中移除节点"""
        path = self.paths.get(path_id)
        if not path:
            return False
        
        path.nodes = [n for n in path.nodes if n.id != node_id]
        path.updated_at = datetime.now(timezone.utc)
        return True
    
    def reorder_nodes(self, path_id: str, node_ids: List[str]) -> bool:
        """重新排序节点"""
        path = self.paths.get(path_id)
        if not path:
            return False
        
        node_map = {n.id: n for n in path.nodes}
        path.nodes = [node_map.get(id) for id in node_ids if node_map.get(id)]
        path.updated_at = datetime.now(timezone.utc)
        return True
    
    def activate_path(self, path_id: str) -> bool:
        """激活学习路径"""
        path = self.paths.get(path_id)
        if not path:
            return False
        
        path.status = LearningPathStatus.ACTIVE
        path.updated_at = datetime.now(timezone.utc)
        return True


class UserLearningProgress:
    """用户学习进度"""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.db = SessionLocal()
    
    def get_progress(self, course_id: int = None, level_id: int = None) -> Dict[str, Any]:
        """获取用户学习进度"""
        query = self.db.query(UserProgress).filter(UserProgress.user_id == self.user_id)
        
        if course_id:
            query = query.filter(UserProgress.course_id == course_id)
        if level_id:
            query = query.filter(UserProgress.level_id == level_id)
        
        progress_list = query.all()
        
        result = {}
        for progress in progress_list:
            key = f"{progress.course_id}-{progress.level_id}" if progress.level_id else str(progress.course_id)
            result[key] = {
                "course_id": progress.course_id,
                "level_id": progress.level_id,
                "status": progress.status,
                "score": progress.score,
                "completed_at": progress.completed_at,
                "attempts": progress.attempts
            }
        
        return result
    
    def update_progress(self, course_id: int, level_id: int = None, status: str = "in_progress", score: int = 0):
        """更新用户学习进度"""
        progress = self.db.query(UserProgress).filter(
            UserProgress.user_id == self.user_id,
            UserProgress.course_id == course_id,
            UserProgress.level_id == level_id
        ).first()
        
        if progress:
            progress.status = status
            progress.score = score
            progress.attempts += 1
            if status == "completed":
                progress.completed_at = datetime.now(timezone.utc)
        else:
            progress = UserProgress(
                user_id=self.user_id,
                course_id=course_id,
                level_id=level_id,
                status=status,
                score=score,
                attempts=1,
                completed_at=datetime.now(timezone.utc) if status == "completed" else None
            )
            self.db.add(progress)
        
        self.db.commit()
    
    def get_recommendations(self, limit: int = 5) -> List[Dict[str, Any]]:
        """获取个性化学习推荐"""
        # 根据用户进度和历史行为生成推荐
        recommendations = []
        
        # 获取用户已完成的课程
        completed_courses = set()
        progresses = self.db.query(UserProgress).filter(
            UserProgress.user_id == self.user_id,
            UserProgress.status == "completed"
        ).all()
        
        for p in progresses:
            if p.course_id:
                completed_courses.add(p.course_id)
        
        # 获取所有可用课程，排除已完成的
        courses = self.db.query(Course).filter(
            Course.id.notin_(completed_courses)
        ).limit(limit).all()
        
        for course in courses:
            recommendations.append({
                "course_id": course.id,
                "course_name": course.title,
                "description": course.description,
                "estimated_duration": course.duration or 60
            })
        
        return recommendations


# 全局实例
learning_path_manager = LearningPathManager()


# API路由
from fastapi import APIRouter, HTTPException, Depends
from apps.api.deps import get_current_active_user

router = APIRouter(prefix="/learning", tags=["学习路径"])


@router.post("/paths")
async def create_learning_path(
    name: str,
    description: str = None,
    current_user = Depends(get_current_active_user)
):
    """创建学习路径"""
    path = learning_path_manager.create_path(name, description)
    return {"success": True, "path": path.dict()}


@router.get("/paths")
async def get_learning_paths():
    """获取所有学习路径"""
    paths = list(learning_path_manager.paths.values())
    return {"paths": [p.dict() for p in paths]}


@router.get("/paths/{path_id}")
async def get_learning_path(path_id: str):
    """获取学习路径详情"""
    path = learning_path_manager.get_path(path_id)
    if not path:
        raise HTTPException(status_code=404, detail="学习路径不存在")
    return {"path": path.dict()}


@router.put("/paths/{path_id}")
async def update_learning_path(
    path_id: str,
    name: str = None,
    description: str = None,
    current_user = Depends(get_current_active_user)
):
    """更新学习路径"""
    updates = {}
    if name:
        updates["name"] = name
    if description:
        updates["description"] = description
    
    path = learning_path_manager.update_path(path_id, **updates)
    if not path:
        raise HTTPException(status_code=404, detail="学习路径不存在")
    return {"success": True, "path": path.dict()}


@router.delete("/paths/{path_id}")
async def delete_learning_path(
    path_id: str,
    current_user = Depends(get_current_active_user)
):
    """删除学习路径"""
    success = learning_path_manager.delete_path(path_id)
    if not success:
        raise HTTPException(status_code=404, detail="学习路径不存在")
    return {"success": True}


@router.post("/paths/{path_id}/nodes")
async def add_node_to_path(
    path_id: str,
    node: LearningNode,
    current_user = Depends(get_current_active_user)
):
    """添加节点到学习路径"""
    success = learning_path_manager.add_node(path_id, node)
    if not success:
        raise HTTPException(status_code=404, detail="学习路径不存在")
    return {"success": True}


@router.delete("/paths/{path_id}/nodes/{node_id}")
async def remove_node_from_path(
    path_id: str,
    node_id: str,
    current_user = Depends(get_current_active_user)
):
    """从学习路径移除节点"""
    success = learning_path_manager.remove_node(path_id, node_id)
    if not success:
        raise HTTPException(status_code=404, detail="路径或节点不存在")
    return {"success": True}


@router.post("/paths/{path_id}/activate")
async def activate_learning_path(
    path_id: str,
    current_user = Depends(get_current_active_user)
):
    """激活学习路径"""
    success = learning_path_manager.activate_path(path_id)
    if not success:
        raise HTTPException(status_code=404, detail="学习路径不存在")
    return {"success": True}


@router.get("/progress")
async def get_user_progress(
    course_id: int = None,
    level_id: int = None,
    current_user = Depends(get_current_active_user)
):
    """获取用户学习进度"""
    progress_manager = UserLearningProgress(current_user.id)
    progress = progress_manager.get_progress(course_id, level_id)
    return {"progress": progress}


@router.post("/progress")
async def update_user_progress(
    course_id: int,
    level_id: int = None,
    status: str = "in_progress",
    score: int = 0,
    current_user = Depends(get_current_active_user)
):
    """更新用户学习进度"""
    progress_manager = UserLearningProgress(current_user.id)
    progress_manager.update_progress(course_id, level_id, status, score)
    return {"success": True}


@router.get("/recommendations")
async def get_learning_recommendations(
    limit: int = 5,
    current_user = Depends(get_current_active_user)
):
    """获取个性化学习推荐"""
    progress_manager = UserLearningProgress(current_user.id)
    recommendations = progress_manager.get_recommendations(limit)
    return {"recommendations": recommendations}