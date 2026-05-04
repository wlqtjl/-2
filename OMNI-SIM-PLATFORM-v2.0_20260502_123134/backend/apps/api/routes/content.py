from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional
from apps.core import database, models
from apps.api.deps import get_current_active_user
from apps.ai.coordinator import coordinator
from apps.ai.workers import document_parser, npc_worker
from pydantic import BaseModel, Json
import json

router = APIRouter(prefix="/content", tags=["content"])
MAX_CONTENT_IMPORT_BYTES = 20 * 1024 * 1024  # 20MB
ALLOWED_IMPORT_EXTENSIONS = {"pdf", "ppt", "pptx", "txt", "md"}

class ContentImportRequest(BaseModel):
    course_id: int
    title: Optional[str] = None
    description: Optional[str] = None

class NPCChatRequest(BaseModel):
    message: str
    context: Optional[dict] = None

content_import_jobs = {}

@router.post("/import")
async def import_content(
    background_tasks: BackgroundTasks,
    course_id: int = Form(...),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_active_user)
):
    if current_user.role not in ["admin", "instructor"]:
        raise HTTPException(status_code=403, detail="Not authorized to import content")

    job_id = f"job_{len(content_import_jobs) + 1}"
    content_import_jobs[job_id] = {
        "status": "pending",
        "progress": 0,
        "course_id": course_id
    }

    file_content = await file.read()
    if len(file_content) > MAX_CONTENT_IMPORT_BYTES:
        raise HTTPException(status_code=413, detail="文件过大，最大支持 20MB")
    filename = file.filename or ""
    if "." not in filename:
        raise HTTPException(status_code=400, detail="不支持的文件类型")
    file_extension = filename.split('.')[-1].lower()
    if file_extension not in ALLOWED_IMPORT_EXTENSIONS:
        raise HTTPException(status_code=400, detail="不支持的文件类型")

    async def process_import():
        try:
            content_import_jobs[job_id]["status"] = "parsing"
            content_import_jobs[job_id]["progress"] = 10
            
            parsed_result = await document_parser.parse(file_content, file_extension)
            if "error" in parsed_result:
                content_import_jobs[job_id]["status"] = "error"
                content_import_jobs[job_id]["message"] = parsed_result["error"]
                return
            
            content_import_jobs[job_id]["progress"] = 30
            content_import_jobs[job_id]["status"] = "processing"
            
            document_text = json.dumps(parsed_result, ensure_ascii=False)
            
            result = await coordinator.process_document(
                document_text,
                {"title": title or parsed_result.get("title", file.filename), "file_name": file.filename},
                course_id
            )
            
            content_import_jobs[job_id]["progress"] = 100
            
            if result.get("success"):
                content_import_jobs[job_id]["status"] = "completed"
                content_import_jobs[job_id]["result"] = result
            else:
                content_import_jobs[job_id]["status"] = "error"
                content_import_jobs[job_id]["message"] = "Verification failed"
        except Exception as e:
            content_import_jobs[job_id]["status"] = "error"
            content_import_jobs[job_id]["message"] = str(e)

    background_tasks.add_task(process_import)

    return {
        "job_id": job_id,
        "status": "started",
        "message": "Content import started in background"
    }

@router.get("/import/{job_id}/status")
async def get_import_status(job_id: str, current_user: models.User = Depends(get_current_active_user)):
    if job_id not in content_import_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return content_import_jobs[job_id]

@router.post("/npc/chat")
async def npc_chat(
    request: NPCChatRequest,
    current_user: models.User = Depends(get_current_active_user)
):
    try:
        response = await npc_worker.chat(
            str(current_user.id),
            request.message,
            request.context
        )
        return {
            "success": True,
            "response": response.get("response"),
            "suggestions": response.get("suggestions", []),
            "confidence": response.get("confidence", 0.8)
        }
    except Exception as e:
        return {
            "success": False,
            "response": f"抱歉，我遇到了问题：{str(e)}",
            "suggestions": ["请稍后再试"],
            "confidence": 0
        }

@router.get("/npc/history")
async def get_npc_history(current_user: models.User = Depends(get_current_active_user)):
    history = npc_worker.conversation_history.get(str(current_user.id), [])
    return {
        "success": True,
        "history": history
    }

@router.get("/ai/status")
async def get_ai_status():
    from apps.core.config import settings
    
    api_key_configured = False
    if settings.DEFAULT_AI_MODEL == "claude":
        api_key_configured = bool(settings.CLAUDE_API_KEY and settings.CLAUDE_API_KEY != "your-claude-api-key-here")
    elif settings.DEFAULT_AI_MODEL == "qianwen":
        api_key_configured = bool(settings.QIANWEN_API_KEY and settings.QIANWEN_API_KEY != "your-qianwen-api-key-here")
    elif settings.DEFAULT_AI_MODEL == "deepseek":
        api_key_configured = bool(settings.DEEPSEEK_API_KEY and settings.DEEPSEEK_API_KEY != "your-deepseek-api-key-here")
    
    return {
        "api_configured": api_key_configured,
        "coordinator_ready": True,
        "default_model": settings.DEFAULT_AI_MODEL
    }
