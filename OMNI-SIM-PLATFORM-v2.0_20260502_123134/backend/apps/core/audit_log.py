from datetime import datetime, timezone
from typing import Optional, Dict, Any
from pydantic import BaseModel
from apps.core.database import SessionLocal
from apps.core.models import AuditLog as AuditLogModel
from apps.core.tenant_context import get_current_tenant_id
from apps.core.config import settings
import logging
from enum import Enum

logger = logging.getLogger(__name__)


def _try_kafka_publish(topic: str, payload: dict) -> None:
    """惰性导入 kafka_producer，避免可选依赖未安装时崩溃。"""
    if not settings.KAFKA_ENABLED:
        return
    try:
        from apps.core.kafka_producer import kafka_producer  # noqa: WPS433
        import asyncio

        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(kafka_producer.send_message(topic, payload))
        else:
            loop.run_until_complete(kafka_producer.send_message(topic, payload))
    except Exception as e:  # pragma: no cover
        logger.debug(f"audit_log kafka publish skipped: {e}")


class AuditAction(str, Enum):
    """审计操作类型"""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    IMPORT = "import"
    EXPORT = "export"
    UPLOAD = "upload"
    DOWNLOAD = "download"
    PERMISSION_CHANGE = "permission_change"
    TENANT_CREATE = "tenant_create"
    TENANT_UPDATE = "tenant_update"
    TENANT_DELETE = "tenant_delete"


class AuditResource(str, Enum):
    """审计资源类型"""
    USER = "user"
    COURSE = "course"
    LESSON = "lesson"
    LEVEL = "level"
    ATTEMPT = "attempt"
    ACHIEVEMENT = "achievement"
    TENANT = "tenant"
    ROLE = "role"
    PERMISSION = "permission"
    DOCUMENT = "document"
    UPLOAD = "upload"
    CONFIG = "config"


class AuditLog(BaseModel):
    """审计日志模型"""
    action: AuditAction
    resource_type: AuditResource
    resource_id: Optional[int] = None
    resource_name: Optional[str] = None
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    tenant_id: Optional[int] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    status: str = "success"
    message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = datetime.now(timezone.utc)


class AuditLogger:
    """审计日志记录器"""
    
    @staticmethod
    def log(
        action: AuditAction,
        resource_type: AuditResource,
        resource_id: Optional[int] = None,
        resource_name: Optional[str] = None,
        user_id: Optional[int] = None,
        user_name: Optional[str] = None,
        tenant_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        status: str = "success",
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """记录审计日志"""
        # 从上下文获取租户ID
        if tenant_id is None:
            tenant_id = get_current_tenant_id()
        
        # 创建日志对象
        audit_log = AuditLog(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            user_id=user_id,
            user_name=user_name,
            tenant_id=tenant_id,
            ip_address=ip_address,
            user_agent=user_agent,
            status=status,
            message=message,
            details=details
        )
        
        # 保存到数据库
        AuditLogger._save_to_db(audit_log)
        
        # 发送到Kafka
        AuditLogger._send_to_kafka(audit_log)
        
        # 日志记录
        logger.info(f"Audit log: {action.value} {resource_type.value} {resource_id} by user {user_id}")
    
    @staticmethod
    def _save_to_db(audit_log: AuditLog):
        """保存审计日志到数据库"""
        try:
            db = SessionLocal()
            db_log = AuditLogModel(
                action=audit_log.action.value,
                resource_type=audit_log.resource_type.value,
                resource_id=audit_log.resource_id,
                resource_name=audit_log.resource_name,
                user_id=audit_log.user_id,
                user_name=audit_log.user_name,
                tenant_id=audit_log.tenant_id,
                ip_address=audit_log.ip_address,
                user_agent=audit_log.user_agent,
                status=audit_log.status,
                message=audit_log.message,
                details=audit_log.details,
                timestamp=audit_log.timestamp
            )
            db.add(db_log)
            db.commit()
            db.close()
        except Exception as e:
            logger.error(f"Failed to save audit log to database: {str(e)}")
    
    @staticmethod
    def _send_to_kafka(audit_log: AuditLog):
        """发送审计日志到Kafka"""
        if not settings.KAFKA_ENABLED:
            return
        
        try:
            message = {
                "action": audit_log.action.value,
                "resource_type": audit_log.resource_type.value,
                "resource_id": audit_log.resource_id,
                "resource_name": audit_log.resource_name,
                "user_id": audit_log.user_id,
                "user_name": audit_log.user_name,
                "tenant_id": audit_log.tenant_id,
                "ip_address": audit_log.ip_address,
                "user_agent": audit_log.user_agent,
                "status": audit_log.status,
                "message": audit_log.message,
                "details": audit_log.details,
                "timestamp": audit_log.timestamp.isoformat()
            }
            _try_kafka_publish("audit.log", message)
        except Exception as e:
            logger.error(f"Failed to send audit log to Kafka: {str(e)}")


# 便捷函数
def log_create(resource_type: AuditResource, resource_id: int, resource_name: str = None, **kwargs):
    """记录创建操作"""
    AuditLogger.log(AuditAction.CREATE, resource_type, resource_id, resource_name, **kwargs)


def log_update(resource_type: AuditResource, resource_id: int, resource_name: str = None, **kwargs):
    """记录更新操作"""
    AuditLogger.log(AuditAction.UPDATE, resource_type, resource_id, resource_name, **kwargs)


def log_delete(resource_type: AuditResource, resource_id: int, resource_name: str = None, **kwargs):
    """记录删除操作"""
    AuditLogger.log(AuditAction.DELETE, resource_type, resource_id, resource_name, **kwargs)


def log_login(user_id: int, user_name: str, ip_address: str = None, status: str = "success"):
    """记录登录操作"""
    AuditLogger.log(
        AuditAction.LOGIN,
        AuditResource.USER,
        resource_id=user_id,
        resource_name=user_name,
        user_id=user_id,
        user_name=user_name,
        ip_address=ip_address,
        status=status
    )


def log_logout(user_id: int, user_name: str):
    """记录登出操作"""
    AuditLogger.log(
        AuditAction.LOGOUT,
        AuditResource.USER,
        resource_id=user_id,
        resource_name=user_name,
        user_id=user_id,
        user_name=user_name
    )


def log_upload(resource_type: AuditResource, resource_id: int = None, resource_name: str = None, **kwargs):
    """记录上传操作"""
    AuditLogger.log(AuditAction.UPLOAD, resource_type, resource_id, resource_name, **kwargs)


def log_permission_change(user_id: int, role: str, **kwargs):
    """记录权限变更"""
    AuditLogger.log(
        AuditAction.PERMISSION_CHANGE,
        AuditResource.ROLE,
        resource_id=user_id,
        resource_name=role,
        **kwargs
    )