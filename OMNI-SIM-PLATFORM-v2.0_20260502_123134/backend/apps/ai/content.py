from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from apps.core import database
from apps.ai.coordinator import coordinator, claude_client
from apps.ai.workers import document_parser, question_generator, verification_worker

router = APIRouter(prefix="/ai", tags=["ai"])

@router.post("/parse-document")
async def parse_document(
    file: UploadFile = File(...),
    db: Session = Depends(database.get_db)
):
    content = await file.read()

    format = file.filename.split(".")[-1].lower() if "." in file.filename else "txt"

    result = await document_parser.parse(content, format)

    return {
        "success": True,
        "data": result
    }

@router.post("/generate-questions")
async def generate_questions(
    content: str,
    num_questions: int = 5,
    difficulty: str = "medium"
):
    questions = await question_generator.generate(content, num_questions, difficulty)

    return {
        "success": True,
        "questions": questions
    }

@router.post("/verify-questions")
async def verify_questions(
    questions: list,
    content: str
):
    result = await verification_worker.verify(questions, content)

    return {
        "success": True,
        **result
    }

@router.post("/generate-level")
async def generate_level(
    document_content: str,
    metadata: dict = {}
):
    result = await coordinator.process_document(document_content, metadata)

    return {
        "success": True,
        **result
    }

@router.post("/chat")
async def chat_with_npc(
    message: str,
    context: dict = {}
):
    prompt = f"""
你是一个培训NPC角色，基于以下上下文回复学员的问题。

上下文信息：
{context}

学员问题：{message}

请用简洁、友好的方式回答问题。
"""

    response = await claude_client.generate(prompt)

    return {
        "success": True,
        "response": response
    }
