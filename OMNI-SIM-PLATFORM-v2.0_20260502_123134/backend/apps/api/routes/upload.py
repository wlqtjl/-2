from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from typing import List, Optional
from apps.core.s3_storage import s3_storage, FilePathGenerator, FileTypes
from apps.core.models import Course, User
from apps.api.deps import get_current_active_user, require_admin_role
from apps.core.database import SessionLocal
from apps.core import tenant_context
import uuid
import os
import io

router = APIRouter(prefix="/upload", tags=["文件上传"])


ALLOWED_EXTENSIONS = {
    'pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx',
    'jpg', 'jpeg', 'png', 'gif', 'webp', 'svg',
    'mp4', 'mp3', 'zip', 'tar', 'json', 'csv', 'txt'
}

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# Magic bytes for common dangerous file types to reject
_BLOCKED_MAGIC: list[tuple[bytes, str]] = [
    (b'MZ', 'Windows PE可执行文件'),
    (b'\x7fELF', 'ELF可执行文件'),
    (b'#!/', 'Shell脚本'),
    (b'#!', 'Shell脚本'),
]


def _check_magic_bytes(header: bytes) -> None:
    """测试文件头部屗节，拒绝已知危险类型。"""
    for magic, label in _BLOCKED_MAGIC:
        if header.startswith(magic):
            raise HTTPException(status_code=400, detail=f"不允许上传该文件类型: {label}")


async def _read_and_validate(file: UploadFile) -> bytes:
    """读取文件内容并执行大小/魔数字验证。"""
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail=f"文件过大，最大支持 {MAX_FILE_SIZE // 1024 // 1024}MB")
    if content:
        _check_magic_bytes(content[:8])
    # 重置读指针以便后续传输
    file.file = io.BytesIO(content)
    return content


def validate_file(file: UploadFile) -> bool:
    """验证文件"""
    # 检查扩展名
    filename = file.filename.lower()
    ext = filename.split('.')[-1] if '.' in filename else ''
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {ext}")
    return True


@router.post("/course/{course_id}")
async def upload_course_file(
    course_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(require_admin_role)
):
    """上传课程相关文件"""
    validate_file(file)
    content = await _read_and_validate(file)
    
    db = SessionLocal()
    try:
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            raise HTTPException(status_code=404, detail="课程不存在")
        
        # 检查租户权限
        if current_user.role != "admin" and course.tenant_id != current_user.tenant_id:
            raise HTTPException(status_code=403, detail="无权上传文件到其他租户的课程")
        
        # 生成文件名
        ext = file.filename.split('.')[-1]
        new_filename = f"{uuid.uuid4()}.{ext}"
        key = FilePathGenerator.generate_course_upload_path(course_id, new_filename)
        
        # 上传文件
        url = s3_storage.upload_file(file.file, key, file.content_type, acl='private')
        
        return {
            "success": True,
            "url": url,
            "key": key,
            "filename": file.filename,
            "content_type": file.content_type
        }
    finally:
        db.close()


@router.post("/avatar")
async def upload_user_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user)
):
    """上传用户头像"""
    # 验证文件类型
    ext = file.filename.lower().split('.')[-1]
    if ext not in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
        raise HTTPException(status_code=400, detail="只支持图片格式")
    content = await _read_and_validate(file)
    
    # 生成文件名
    new_filename = f"avatar_{uuid.uuid4()}.{ext}"
    key = FilePathGenerator.generate_user_avatar_path(current_user.id, new_filename)
    
    # 上传文件
    url = s3_storage.upload_file(file.file, key, file.content_type, acl='public-read')
    
    return {
        "success": True,
        "url": url,
        "key": key
    }


@router.post("/import")
async def upload_import_file(
    file: UploadFile = File(...),
    current_user: User = Depends(require_admin_role)
):
    """上传导入文件（PDF/PPT等）"""
    # 验证文件类型
    ext = file.filename.lower().split('.')[-1]
    if ext not in ['pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx']:
        raise HTTPException(status_code=400, detail="只支持PDF、Word、Excel、PPT格式")
    content = await _read_and_validate(file)
    
    # 生成任务ID
    task_id = str(uuid.uuid4())
    key = FilePathGenerator.generate_import_path(task_id, file.filename)
    
    # 上传文件
    url = s3_storage.upload_file(file.file, key, file.content_type, acl='private')
    
    return {
        "success": True,
        "url": url,
        "key": key,
        "task_id": task_id,
        "filename": file.filename
    }


@router.get("/presigned-url")
async def get_presigned_url(
    key: str = Query(..., description="文件路径"),
    expires_in: int = Query(3600, description="过期时间（秒）"),
    current_user: User = Depends(require_admin_role)
):
    """获取预签名下载URL（仅管理员/讲师）"""
    if expires_in < 60 or expires_in > 24 * 3600:
        raise HTTPException(status_code=400, detail="expires_in 必须在 60~86400 秒之间")
    url = s3_storage.get_presigned_url(key, expires_in)
    
    if not url:
        raise HTTPException(status_code=500, detail="无法生成预签名URL")
    
    return {"url": url}


@router.delete("/file")
async def delete_file(
    key: str = Query(..., description="文件路径"),
    current_user: User = Depends(require_admin_role)
):
    """删除文件"""
    # 检查文件是否存在
    if not s3_storage.file_exists(key):
        raise HTTPException(status_code=404, detail="文件不存在")
    
    s3_storage.delete_file(key)
    
    return {"success": True, "message": "文件删除成功"}


@router.get("/list")
async def list_files(
    prefix: str = Query("", description="文件前缀"),
    current_user: User = Depends(require_admin_role)
):
    """列出文件"""
    files = s3_storage.list_files(prefix)
    
    return {"files": files}


@router.get("/health")
async def check_storage_health(current_user: User = Depends(require_admin_role)):
    """检查存储服务健康状态（仅管理员/讲师）"""
    if not s3_storage.enabled:
        return {"status": "disabled", "message": "S3存储未启用"}
    
    try:
        # 尝试列出文件来验证连接
        s3_storage.list_files()
        return {"status": "healthy", "bucket": s3_storage.bucket_name}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}