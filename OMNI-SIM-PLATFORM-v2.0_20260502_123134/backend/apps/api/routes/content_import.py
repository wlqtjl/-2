from fastapi import APIRouter, File, UploadFile, Depends, HTTPException, Body
from typing import Optional
from apps.core.content_importer import content_importer, ImportSourceType, ImportResult
from apps.api.deps import get_current_user, require_admin_or_instructor

router = APIRouter(prefix="/import", tags=["内容导入"])
MAX_IMPORT_FILE_BYTES = 20 * 1024 * 1024  # 20MB


@router.post("/file")
def import_from_file(
    file: UploadFile = File(...),
    course_id: Optional[int] = None,
    course_name: Optional[str] = None,
    current_user = Depends(require_admin_or_instructor)
):
    """从文件导入内容并自动生成关卡"""
    # 检查文件类型
    filename = (file.filename or "").lower()
    if not filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")
    if filename.endswith(".pdf"):
        source_type = ImportSourceType.PDF
    elif filename.endswith(".ppt"):
        source_type = ImportSourceType.PPT
    elif filename.endswith(".pptx"):
        source_type = ImportSourceType.PPTX
    else:
        raise HTTPException(status_code=400, detail="不支持的文件类型，支持PDF、PPT、PPTX")
    
    # 保存文件临时文件
    import tempfile
    import os

    content = file.file.read()
    if len(content) > MAX_IMPORT_FILE_BYTES:
        raise HTTPException(status_code=413, detail="文件过大，最大支持 20MB")
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as temp_file:
        temp_file.write(content)
        temp_path = temp_file.name
    
    try:
        result = content_importer.import_from_file(
            file_path=temp_path,
            source_type=source_type,
            course_id=course_id,
            course_name=course_name
        )
        
        if not result.success:
            raise HTTPException(status_code=400, detail=result.message)
        
        return {
            "success": result.success,
            "message": result.message,
            "course_id": result.course_id,
            "levels_created": result.levels_created,
            "questions_created": result.questions_created,
            "warnings": result.warnings
        }
    finally:
        os.unlink(temp_path)


@router.post("/text")
def import_from_text(
    text: str = Body(..., media_type="text/plain", max_length=500_000),
    course_id: Optional[int] = None,
    course_name: Optional[str] = None,
    current_user = Depends(require_admin_or_instructor)
):
    """从文本内容导入并自动生成关卡"""
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="文本内容不能为空")
    
    result = content_importer.import_from_text(
        text=text,
        course_id=course_id,
        course_name=course_name
    )
    
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    
    return {
        "success": result.success,
        "message": result.message,
        "course_id": result.course_id,
        "levels_created": result.levels_created,
        "questions_created": result.questions_created,
        "warnings": result.warnings
    }


@router.post("/preview")
def preview_import(
    text: str = Body(..., media_type="text/plain", max_length=200_000),
    current_user = Depends(get_current_user)
):
    """预览文本解析结果（需登录）"""
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="文本内容不能为空")
    if len(text) > 200_000:
        raise HTTPException(status_code=413, detail="预览文本过长，最多 200KB")
    
    # 简单解析预览
    lines = text.split('\n')
    sections = []
    for line in lines[:20]:
        line = line.strip()
        if line:
            sections.append(line[:50] + "..." if len(line) > 50 else line)
    
    return {
        "preview": sections,
        "total_lines": len(lines),
        "estimated_sections": len([l for l in lines if l.strip() and (l.startswith('1') or l.startswith('一') or l.startswith('第'))])
    }


@router.get("/supported-formats")
def get_supported_formats():
    """获取支持的导入格式"""
    return {
        "formats": [
            {
                "name": "PDF",
                "extension": ".pdf",
                "description": "支持从PDF文档提取文本内容"
            },
            {
                "name": "PPT/PPTX",
                "extension": ".ppt, .pptx",
                "description": "支持从PowerPoint演示文稿提取文本"
            },
            {
                "name": "Text",
                "extension": ".txt",
                "description": "支持直接导入文本内容"
            }
        ],
        "format_requirements": [
            "PDF文件需要包含可提取的文本内容",
            "PPT文件需要使用标准文本框格式",
            "文本内容建议使用结构化格式（如带编号的章节）"
        ]
    }
