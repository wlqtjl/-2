from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any, Optional
from apps.core.vector_db import vector_db, memory_store
from apps.core.recommendation_engine import recommendation_engine
from apps.api.deps import get_current_user, require_admin
from apps.core.models import User

router = APIRouter(prefix="/vector", tags=["向量数据库"])


@router.post("/initialize")
async def initialize_vector_db(current_user: User = Depends(require_admin)):
    """初始化向量数据库集合"""
    try:
        vector_db.initialize_collection()
        memory_store.initialize_collection()
        return {"status": "success", "message": "向量数据库集合初始化成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents")
async def add_documents(
    documents: List[Dict[str, Any]],
    current_user: User = Depends(require_admin)
):
    """批量添加文档"""
    try:
        vector_db.add_documents(documents)
        return {"status": "success", "count": len(documents)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/document")
async def add_document(
    document_id: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None,
    current_user: User = Depends(require_admin)
):
    """添加单个文档"""
    try:
        vector_db.add_document(document_id, content, metadata)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_documents(
    query: str,
    top_k: int = 5,
    current_user: User = Depends(get_current_user)
):
    """搜索相似文档"""
    try:
        results = vector_db.search(query, top_k=top_k)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/document/{document_id}")
async def get_document(document_id: str, current_user: User = Depends(get_current_user)):
    """获取单个文档"""
    try:
        result = vector_db.get_document(document_id)
        if not result:
            raise HTTPException(status_code=404, detail="文档不存在")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/document/{document_id}")
async def delete_document(document_id: str, current_user: User = Depends(require_admin)):
    """删除文档"""
    try:
        vector_db.delete_document(document_id)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/memory")
async def add_memory(
    user_id: Optional[int] = None,
    memory_type: str = "learning",
    content: str = "",
    context: Optional[Dict[str, Any]] = None,
    current_user: User = Depends(get_current_user)
):
    """添加用户记忆"""
    try:
        # 限定只能写自己，除非是管理员
        if user_id is not None and user_id != current_user.id and current_user.role != "admin":
            raise HTTPException(status_code=403, detail="只能写入自己的记忆")
        target_user_id = user_id or current_user.id
        memory_store.add_memory(target_user_id, memory_type, content, context)
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memories")
async def get_user_memories(
    user_id: Optional[int] = None,
    memory_type: Optional[str] = None,
    limit: int = 100,
    current_user: User = Depends(get_current_user)
):
    """获取用户记忆"""
    try:
        if user_id is not None and user_id != current_user.id and current_user.role != "admin":
            raise HTTPException(status_code=403, detail="只能读取自己的记忆")
        target_user_id = user_id or current_user.id
        memories = memory_store.get_user_memories(target_user_id, memory_type, limit)
        return memories
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memories/search")
async def search_memories(
    query: str,
    user_id: Optional[int] = None,
    top_k: int = 10,
    current_user: User = Depends(get_current_user)
):
    """搜索用户记忆"""
    try:
        if user_id is not None and user_id != current_user.id and current_user.role != "admin":
            raise HTTPException(status_code=403, detail="只能搜索自己的记忆")
        target_user_id = user_id or current_user.id
        results = memory_store.search_memories(target_user_id, query, top_k)
        return results
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_vector_db_stats(current_user: User = Depends(get_current_user)):
    """获取向量数据库统计信息"""
    try:
        return vector_db.get_collection_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/clear")
async def clear_vector_db(current_user: User = Depends(require_admin)):
    """清空向量数据库"""
    try:
        vector_db.clear_collection()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recommend/courses")
async def recommend_courses(
    limit: int = 5,
    current_user: User = Depends(get_current_user)
):
    """推荐课程"""
    try:
        recommendations = recommendation_engine.recommend_courses(current_user.id, limit)
        return {"recommendations": recommendations}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recommend/levels")
async def recommend_levels(
    course_id: Optional[int] = None,
    limit: int = 5,
    current_user: User = Depends(get_current_user)
):
    """推荐关卡"""
    try:
        recommendations = recommendation_engine.recommend_levels(current_user.id, course_id, limit)
        return {"recommendations": recommendations}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recommend/questions")
async def recommend_questions(
    topic: Optional[str] = None,
    limit: int = 10,
    current_user: User = Depends(get_current_user)
):
    """推荐练习题"""
    try:
        questions = recommendation_engine.recommend_questions(current_user.id, topic, limit)
        return {"questions": questions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recommend/learning-path")
async def get_learning_path(
    course_id: Optional[int] = None,
    current_user: User = Depends(get_current_user)
):
    """获取个性化学习路径"""
    try:
        path = recommendation_engine.generate_learning_path(current_user.id, course_id)
        suggestions = recommendation_engine.get_learning_suggestions(current_user.id)
        return {"learning_path": path, "suggestions": suggestions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/track-action")
async def track_user_action(
    action_type: str,
    content: str,
    context: Optional[Dict[str, Any]] = None,
    current_user: User = Depends(get_current_user)
):
    """追踪用户行为"""
    try:
        recommendation_engine.track_user_action(current_user.id, action_type, content, context)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user-profile")
async def get_user_profile(current_user: User = Depends(get_current_user)):
    """获取用户学习画像"""
    try:
        profile = recommendation_engine.get_user_profile(current_user.id)
        return profile
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
