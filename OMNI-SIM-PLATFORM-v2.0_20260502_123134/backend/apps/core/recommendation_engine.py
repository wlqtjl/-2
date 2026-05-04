from typing import List, Dict, Any, Optional
from apps.core.vector_db import vector_db, memory_store
from apps.core.models import User, Level, Course, UserProgress
from apps.core.database import SessionLocal
import json


class RecommendationEngine:
    """个性化学习推荐引擎"""

    def __init__(self):
        pass  # 不在构造时持有会话，避免陈旧连接

    def get_user_profile(self, user_id: int) -> Dict[str, Any]:
        """获取用户学习画像"""
        db = SessionLocal()
        try:
            return self._get_user_profile_db(user_id, db)
        finally:
            db.close()

    def _get_user_profile_db(self, user_id: int, db) -> Dict[str, Any]:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {}

        progress = db.query(UserProgress).filter(UserProgress.user_id == user_id).all()
        
        completed_levels = []
        scores = []
        learning_paths = []
        
        for p in progress:
            completed_levels.append(p.level_id)
            if p.score is not None:
                scores.append(p.score)
            if p.path:
                learning_paths.extend(p.path.split(','))
        
        return {
            "user_id": user.id,
            "username": user.full_name or user.email,
            "role": user.role,
            "completed_levels": completed_levels,
            "average_score": sum(scores) / len(scores) if scores else 0,
            "total_progress": len(completed_levels),
            "learning_paths": list(set(learning_paths))
        }
    
    def recommend_courses(self, user_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        """推荐课程"""
        db = SessionLocal()
        try:
            return self._recommend_courses_db(user_id, limit, db)
        finally:
            db.close()

    def _recommend_courses_db(self, user_id: int, limit: int, db) -> List[Dict[str, Any]]:
        user_profile = self._get_user_profile_db(user_id, db)

        # 基于用户已完成的关卡和学习路径推荐
        query = " ".join([
            f"course about {path}" for path in user_profile.get("learning_paths", [])[:3]
        ]) or "popular training courses"

        # 从向量数据库搜索相关课程
        results = vector_db.search(query, top_k=limit * 2)

        # 获取所有可用课程
        courses = db.query(Course).all()
        course_dict = {str(c.id): c for c in courses}
        
        recommendations = []
        seen_courses = set()
        
        for result in results:
            course_id = result.get("metadata", {}).get("course_id") or result.get("document_id")
            if course_id and course_id not in seen_courses and course_id in course_dict:
                course = course_dict[course_id]
                recommendations.append({
                    "type": "course",
                    "id": course.id,
                    "name": course.name,
                    "description": course.description,
                    "confidence": result.get("score", 0.7),
                    "priority": len(recommendations) + 1
                })
                seen_courses.add(course_id)
            
            if len(recommendations) >= limit:
                break
        
        # 如果推荐不足，补充最新课程（Course无popularity列，按创建时间降序）
        if len(recommendations) < limit:
            popular_courses = db.query(Course).order_by(Course.created_at.desc()).limit(limit).all()
            for course in popular_courses:
                if str(course.id) not in seen_courses:
                    recommendations.append({
                        "type": "course",
                        "id": course.id,
                        "name": course.name,
                        "description": course.description,
                        "confidence": 0.6,
                        "priority": len(recommendations) + 1
                    })
                if len(recommendations) >= limit:
                    break
        
        return recommendations
    
    def recommend_levels(self, user_id: int, course_id: Optional[int] = None, limit: int = 5) -> List[Dict[str, Any]]:
        """推荐关卡"""
        db = SessionLocal()
        try:
            return self._recommend_levels_db(user_id, course_id, limit, db)
        finally:
            db.close()

    def _recommend_levels_db(self, user_id: int, course_id: Optional[int], limit: int, db) -> List[Dict[str, Any]]:
        user_profile = self._get_user_profile_db(user_id, db)
        completed_levels = user_profile.get("completed_levels", [])

        # 构建查询
        query_parts = []
        if course_id:
            course = db.query(Course).filter(Course.id == course_id).first()
            if course:
                query_parts.append(course.name)
                query_parts.append(course.description)
        
        # 添加用户学习过的内容主题
        memories = memory_store.search_memories(user_id, "learning topic", top_k=5)
        for memory in memories:
            query_parts.append(memory.get("content", ""))
        
        query = " ".join(query_parts) or "next learning level"
        
        # 搜索相关内容
        filters = {}
        if course_id:
            filters["course_id"] = str(course_id)
        
        results = vector_db.search(query, top_k=limit * 2, filters=filters)
        
        # 获取可用关卡
        levels_query = db.query(Level)
        if course_id:
            levels_query = levels_query.filter(Level.course_id == course_id)
        levels = levels_query.all()
        level_dict = {str(l.id): l for l in levels}
        
        recommendations = []
        seen_levels = set(completed_levels)
        
        for result in results:
            level_id = result.get("metadata", {}).get("level_id") or result.get("document_id")
            if level_id and level_id not in seen_levels and level_id in level_dict:
                level = level_dict[level_id]
                recommendations.append({
                    "type": "level",
                    "id": level.id,
                    "name": level.name,
                    "description": level.description,
                    "course_id": level.course_id,
                    "order": level.order,
                    "confidence": result.get("score", 0.7),
                    "priority": len(recommendations) + 1
                })
                seen_levels.add(level_id)
            
            if len(recommendations) >= limit:
                break
        
        # 补充推荐未完成的关卡
        if len(recommendations) < limit:
            remaining_levels = [l for l in levels if l.id not in completed_levels]
            for level in remaining_levels[:limit - len(recommendations)]:
                recommendations.append({
                    "type": "level",
                    "id": level.id,
                    "name": level.name,
                    "description": level.description,
                    "course_id": level.course_id,
                    "order": level.order,
                    "confidence": 0.5,
                    "priority": len(recommendations) + 1
                })
        
        return recommendations
    
    def recommend_questions(self, user_id: int, topic: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """推荐练习题"""
        # 基于用户薄弱点推荐题目
        memories = memory_store.search_memories(user_id, "wrong answer", top_k=10)
        
        # 分析错误模式
        weak_topics = []
        for memory in memories:
            content = memory.get("content", "")
            if "wrong" in content.lower() or "incorrect" in content.lower():
                weak_topics.append(content)
        
        query = topic or " ".join(weak_topics)[:200] or "practice questions"
        
        results = vector_db.search(query, top_k=limit)
        
        questions = []
        for result in results:
            questions.append({
                "type": "question",
                "content": result.get("content", ""),
                "score": result.get("score", 0.5),
                "metadata": result.get("metadata", {})
            })
        
        return questions[:limit]
    
    def generate_learning_path(self, user_id: int, course_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """生成个性化学习路径"""
        db = SessionLocal()
        try:
            user_profile = self._get_user_profile_db(user_id, db)

            if course_id:
                levels = db.query(Level).filter(Level.course_id == course_id).order_by(Level.order).all()
            else:
                levels = db.query(Level).order_by(Level.order).all()

            completed_levels = set(user_profile.get("completed_levels", []))
            learning_path = []

            for level in levels:
                if level.id in completed_levels:
                    continue

                learning_path.append({
                    "step": len(learning_path) + 1,
                    "level_id": level.id,
                    "level_name": level.name,
                    "course_id": level.course_id,
                    "order": level.order,
                    "estimated_time_minutes": 25
                })

                if len(learning_path) >= 5:
                    break

            return learning_path
        finally:
            db.close()
    
    def get_learning_suggestions(self, user_id: int) -> List[str]:
        """获取学习建议"""
        user_profile = self.get_user_profile(user_id)
        suggestions = []
        
        avg_score = user_profile.get("average_score", 0)
        total_progress = user_profile.get("total_progress", 0)
        
        # 基于分数的建议
        if avg_score < 60:
            suggestions.append("建议复习已学内容，巩固基础知识")
        elif avg_score >= 80:
            suggestions.append("表现优秀！可以尝试更高难度的关卡")
        
        # 基于进度的建议
        if total_progress == 0:
            suggestions.append("开始您的学习之旅，从第一关开始吧！")
        elif total_progress < 5:
            suggestions.append("继续保持，完成更多关卡解锁新成就")
        
        # 基于记忆的建议
        memories = memory_store.search_memories(user_id, "learning", top_k=5)
        if len(memories) > 0:
            suggestions.append("回顾最近的学习内容，加强记忆")
        
        # 默认建议
        if not suggestions:
            suggestions = [
                "继续学习当前课程",
                "尝试新的挑战关卡",
                "复习已学内容巩固知识"
            ]
        
        return suggestions[:3]
    
    def track_user_action(self, user_id: int, action_type: str, content: str, context: Dict[str, Any] = None):
        """追踪用户行为并存储到记忆系统"""
        memory_store.add_memory(
            user_id=user_id,
            memory_type=action_type,
            content=content,
            context=context
        )


recommendation_engine = RecommendationEngine()
