from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, Dict, Any
from apps.ai.coordinator import coordinator
from apps.ai.claude_client import claude_client
from apps.ai.workers import document_parser, question_generator, verification_worker, npc_worker, recommendation_worker, evaluation_worker
from apps.api.deps import get_current_user, require_admin_or_instructor

router = APIRouter(prefix="/ai", tags=["AI智能层"])


@router.post("/process-document")
async def process_document(
    document_content: str,
    metadata: Optional[Dict[str, Any]] = None,
    course_id: Optional[int] = None,
    current_user = Depends(require_admin_or_instructor)
):
    """处理文档并生成游戏化学习内容"""
    if not document_content or not document_content.strip():
        raise HTTPException(status_code=400, detail="文档内容不能为空")
    
    result = await coordinator.process_document(
        document_content=document_content,
        metadata=metadata or {},
        course_id=course_id
    )
    
    return result


@router.post("/generate-questions")
async def generate_questions(
    content: str,
    num_questions: int = 5,
    difficulty: str = "medium",
    current_user = Depends(require_admin_or_instructor)
):
    """生成题目"""
    if not content or not content.strip():
        raise HTTPException(status_code=400, detail="内容不能为空")
    
    questions = await question_generator.generate(content, num_questions, difficulty)
    return {"questions": questions}


@router.post("/verify-questions")
async def verify_questions(
    questions: list,
    content: Optional[str] = "",
    current_user = Depends(require_admin_or_instructor)
):
    """验证题目质量"""
    if not questions:
        raise HTTPException(status_code=400, detail="题目列表不能为空")
    
    result = await verification_worker.verify(questions, content)
    return result


@router.post("/npc-chat")
async def npc_chat(
    message: str,
    context: Optional[Dict[str, Any]] = None,
    current_user = Depends(get_current_user)
):
    """与NPC导师对话"""
    if not message or not message.strip():
        raise HTTPException(status_code=400, detail="消息不能为空")
    
    result = await npc_worker.chat(str(current_user.id), message, context)
    return result


@router.get("/recommend")
async def get_recommendations(
    user_id: Optional[int] = None,
    current_user = Depends(get_current_user)
):
    """获取个性化学习推荐"""
    if user_id is not None and user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="只能查看自己的推荐")
    target_user_id = user_id or current_user.id
    result = await recommendation_worker.recommend(target_user_id)
    return result


@router.get("/recommend/learning-path")
async def get_learning_path(
    course_id: Optional[int] = None,
    current_user = Depends(get_current_user)
):
    """获取学习路径"""
    result = await recommendation_worker.get_learning_path(current_user.id, course_id)
    return result


@router.post("/evaluate")
async def evaluate_performance(
    attempt_data: Dict[str, Any],
    current_user = Depends(get_current_user)
):
    """评估学习表现"""
    if not attempt_data:
        raise HTTPException(status_code=400, detail="评估数据不能为空")
    
    result = await evaluation_worker.evaluate(current_user.id, attempt_data)
    return result


@router.get("/evaluate/report")
async def get_evaluation_report(
    course_id: Optional[int] = None,
    current_user = Depends(get_current_user)
):
    """获取学习报告"""
    result = await evaluation_worker.generate_report(current_user.id, course_id)
    return result


@router.post("/generate")
async def generate_content(
    prompt: str,
    system: Optional[str] = "",
    current_user = Depends(require_admin_or_instructor)
):
    """直接调用Claude生成内容"""
    if not prompt or not prompt.strip():
        raise HTTPException(status_code=400, detail="提示词不能为空")
    
    result = await claude_client.generate(prompt, system)
    return {"result": result}


@router.get("/health")
async def ai_health_check():
    """检查AI服务状态"""
    return {
        "status": "healthy",
        "services": {
            "claude": "configured" if claude_client.api_key else "not configured",
            "workers": {
                "document_parser": "active",
                "question_generator": "active",
                "verification_worker": "active",
                "npc_worker": "active",
                "recommendation_worker": "active",
                "evaluation_worker": "active"
            }
        }
    }
