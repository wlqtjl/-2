from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from ..core.models import Memory, MemoryType
import json

class MemoryService:
    def __init__(self, db: Session):
        self.db = db
    
    def store_memory(
        self,
        user_id: int,
        memory_type: MemoryType,
        key: str,
        value: Any,
        metadata: Optional[Dict] = None,
        vector_embedding: Optional[List[float]] = None
    ) -> Memory:
        existing = self.db.query(Memory).filter(
            and_(
                Memory.user_id == user_id,
                Memory.memory_type == memory_type,
                Memory.key == key
            )
        ).first()
        
        if existing:
            existing.value = value
            existing.metadata = metadata or existing.metadata
            existing.vector_embedding = vector_embedding
            existing.updated_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(existing)
            return existing
        
        memory = Memory(
            user_id=user_id,
            memory_type=memory_type,
            key=key,
            value=value,
            metadata=metadata or {},
            vector_embedding=vector_embedding
        )
        self.db.add(memory)
        self.db.commit()
        self.db.refresh(memory)
        return memory
    
    def get_memory(
        self,
        user_id: int,
        memory_type: MemoryType,
        key: str
    ) -> Optional[Memory]:
        return self.db.query(Memory).filter(
            and_(
                Memory.user_id == user_id,
                Memory.memory_type == memory_type,
                Memory.key == key,
                Memory.is_active == True
            )
        ).first()
    
    def get_memories_by_type(
        self,
        user_id: int,
        memory_type: MemoryType,
        limit: int = 100
    ) -> List[Memory]:
        return self.db.query(Memory).filter(
            and_(
                Memory.user_id == user_id,
                Memory.memory_type == memory_type,
                Memory.is_active == True
            )
        ).order_by(Memory.updated_at.desc()).limit(limit).all()
    
    def search_memories(
        self,
        user_id: int,
        query: str,
        memory_types: Optional[List[MemoryType]] = None,
        limit: int = 20
    ) -> List[Memory]:
        query_filter = [
            Memory.user_id == user_id,
            Memory.is_active == True
        ]
        
        if memory_types:
            query_filter.append(Memory.memory_type.in_(memory_types))
        
        memories = self.db.query(Memory).filter(*query_filter).all()
        
        query_lower = query.lower()
        filtered = []
        for mem in memories:
            if (query_lower in mem.key.lower() or
                query_lower in json.dumps(mem.value, ensure_ascii=False).lower()):
                filtered.append(mem)
        
        return filtered[:limit]
    
    def delete_memory(
        self,
        user_id: int,
        memory_type: MemoryType,
        key: str
    ) -> bool:
        memory = self.get_memory(user_id, memory_type, key)
        if memory:
            memory.is_active = False
            self.db.commit()
            return True
        return False
    
    def clear_old_memories(
        self,
        user_id: int,
        older_than_days: int = 90
    ) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
        memories = self.db.query(Memory).filter(
            and_(
                Memory.user_id == user_id,
                Memory.updated_at < cutoff
            )
        ).all()
        
        for mem in memories:
            mem.is_active = False
        
        self.db.commit()
        return len(memories)
    
    def store_user_memory(
        self,
        user_id: int,
        key: str,
        value: Any,
        metadata: Optional[Dict] = None
    ) -> Memory:
        return self.store_memory(user_id, MemoryType.USER, key, value, metadata)
    
    def store_feedback_memory(
        self,
        user_id: int,
        key: str,
        feedback: Dict,
        metadata: Optional[Dict] = None
    ) -> Memory:
        return self.store_memory(user_id, MemoryType.FEEDBACK, key, feedback, metadata)
    
    def store_project_memory(
        self,
        user_id: int,
        key: str,
        project_data: Dict,
        metadata: Optional[Dict] = None
    ) -> Memory:
        return self.store_memory(user_id, MemoryType.PROJECT, key, project_data, metadata)
    
    def store_reference_memory(
        self,
        user_id: int,
        key: str,
        reference_data: Dict,
        metadata: Optional[Dict] = None
    ) -> Memory:
        return self.store_memory(user_id, MemoryType.REFERENCE, key, reference_data, metadata)
    
    def get_user_profile(self, user_id: int) -> Dict:
        memory = self.get_memory(user_id, MemoryType.USER, "profile")
        if memory:
            return memory.value
        return {
            "learning_style": "visual",
            "difficulty_preference": "medium",
            "goal": "complete_courses",
            "preferred_topics": []
        }
    
    def update_user_profile(self, user_id: int, profile_data: Dict) -> Memory:
        existing = self.get_user_profile(user_id)
        existing.update(profile_data)
        return self.store_user_memory(user_id, "profile", existing)
    
    def record_learning_feedback(
        self,
        user_id: int,
        level_id: int,
        feedback_type: str,
        feedback_content: str,
        score: Optional[int] = None
    ) -> Memory:
        key = f"feedback_{level_id}_{datetime.now(timezone.utc).isoformat()}"
        return self.store_feedback_memory(user_id, key, {
            "level_id": level_id,
            "feedback_type": feedback_type,
            "feedback_content": feedback_content,
            "score": score,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    def get_learning_insights(self, user_id: int) -> Dict:
        user_profile = self.get_user_profile(user_id)
        recent_feedback = self.get_memories_by_type(user_id, MemoryType.FEEDBACK, 20)
        
        strengths = []
        weaknesses = []
        for feedback in recent_feedback:
            val = feedback.value
            if val.get("score", 0) > 80:
                strengths.append(val.get("level_id"))
            elif val.get("score", 0) < 50:
                weaknesses.append(val.get("level_id"))
        
        return {
            "profile": user_profile,
            "recent_feedback_count": len(recent_feedback),
            "strength_level_ids": strengths,
            "weakness_level_ids": weaknesses
        }
    
    def store_course_reference(
        self,
        user_id: int,
        course_id: int,
        content: Dict,
        metadata: Optional[Dict] = None
    ) -> Memory:
        key = f"course_{course_id}"
        return self.store_reference_memory(user_id, key, content, metadata)
    
    def get_course_reference(self, user_id: int, course_id: int) -> Optional[Dict]:
        memory = self.get_memory(user_id, MemoryType.REFERENCE, f"course_{course_id}")
        return memory.value if memory else None
