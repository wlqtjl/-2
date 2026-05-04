from aiokafka import AIOKafkaProducer
from typing import Optional, Dict, Any
import json
import logging
from apps.core.config import settings

logger = logging.getLogger(__name__)


class KafkaProducer:
    """Kafka消息生产者"""
    
    def __init__(self):
        self.producer: Optional[AIOKafkaProducer] = None
        self.bootstrap_servers = settings.KAFKA_BOOTSTRAP_SERVERS or "localhost:9092"
    
    async def start(self):
        """启动生产者"""
        try:
            self.producer = AIOKafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=self._serialize_message,
                retries=3,
                acks="all"
            )
            await self.producer.start()
            logger.info("Kafka producer started successfully")
        except Exception as e:
            logger.error(f"Failed to start Kafka producer: {str(e)}")
            raise
    
    async def stop(self):
        """停止生产者"""
        if self.producer:
            await self.producer.stop()
            logger.info("Kafka producer stopped")
    
    def _serialize_message(self, message: Dict[str, Any]) -> bytes:
        """序列化消息为JSON字节"""
        return json.dumps(message).encode("utf-8")
    
    async def send_message(self, topic: str, message: Dict[str, Any], key: Optional[str] = None):
        """发送消息到指定主题"""
        if not self.producer:
            logger.warning("Kafka producer not started, skipping message")
            return
        
        try:
            key_bytes = key.encode("utf-8") if key else None
            await self.producer.send_and_wait(topic, message, key=key_bytes)
            logger.debug(f"Message sent to topic {topic}: {message}")
        except Exception as e:
            logger.error(f"Failed to send message to topic {topic}: {str(e)}")
            raise


kafka_producer = KafkaProducer()


# 消息主题定义
class KafkaTopics:
    USER_REGISTERED = "user.registered"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"
    
    COURSE_CREATED = "course.created"
    COURSE_UPDATED = "course.updated"
    COURSE_DELETED = "course.deleted"
    
    LEVEL_COMPLETED = "level.completed"
    LEVEL_ATTEMPT = "level.attempt"
    
    ACHIEVEMENT_UNLOCKED = "achievement.unlocked"
    
    LEADERBOARD_UPDATED = "leaderboard.updated"
    
    EMAIL_NOTIFICATION = "email.notification"
    
    # AI任务
    AI_TASK_SUBMITTED = "ai.task.submitted"
    AI_TASK_COMPLETED = "ai.task.completed"
    AI_TASK_FAILED = "ai.task.failed"
    
    # 导入任务
    IMPORT_TASK_SUBMITTED = "import.task.submitted"
    IMPORT_TASK_COMPLETED = "import.task.completed"
    
    # 系统日志
    SYSTEM_LOG = "system.log"
    AUDIT_LOG = "audit.log"


# 消息发布便捷方法
async def publish_user_registered(user_id: int, email: str, tenant_id: int = None):
    """发布用户注册消息"""
    message = {
        "event_type": "user_registered",
        "user_id": user_id,
        "email": email,
        "tenant_id": tenant_id,
        "timestamp": None
    }
    await kafka_producer.send_message(KafkaTopics.USER_REGISTERED, message)


async def publish_level_completed(user_id: int, level_id: int, score: int, completed_at: str):
    """发布关卡完成消息"""
    message = {
        "event_type": "level_completed",
        "user_id": user_id,
        "level_id": level_id,
        "score": score,
        "completed_at": completed_at
    }
    await kafka_producer.send_message(KafkaTopics.LEVEL_COMPLETED, message)


async def publish_achievement_unlocked(user_id: int, achievement_name: str, unlocked_at: str):
    """发布成就解锁消息"""
    message = {
        "event_type": "achievement_unlocked",
        "user_id": user_id,
        "achievement_name": achievement_name,
        "unlocked_at": unlocked_at
    }
    await kafka_producer.send_message(KafkaTopics.ACHIEVEMENT_UNLOCKED, message)


async def publish_audit_log(user_id: int, action: str, resource_type: str, resource_id: int = None, details: Dict = None):
    """发布审计日志消息"""
    message = {
        "event_type": "audit_log",
        "user_id": user_id,
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "details": details or {},
        "timestamp": None
    }
    await kafka_producer.send_message(KafkaTopics.AUDIT_LOG, message)


async def publish_email_notification(to_email: str, subject: str, template: str, context: Dict = None):
    """发布邮件通知消息"""
    message = {
        "event_type": "email_notification",
        "to_email": to_email,
        "subject": subject,
        "template": template,
        "context": context or {}
    }
    await kafka_producer.send_message(KafkaTopics.EMAIL_NOTIFICATION, message)