from aiokafka import AIOKafkaConsumer, ConsumerRecord
from typing import Optional, Dict, Any, Callable
import json
import logging
from apps.core.config import settings
from apps.core.kafka_producer import KafkaTopics

logger = logging.getLogger(__name__)


class KafkaConsumer:
    """Kafka消息消费者"""
    
    def __init__(self, topics: list, group_id: str):
        self.consumer: Optional[AIOKafkaConsumer] = None
        self.topics = topics
        self.group_id = group_id
        self.bootstrap_servers = settings.KAFKA_BOOTSTRAP_SERVERS or "localhost:9092"
        self.message_handlers: Dict[str, Callable] = {}
    
    def register_handler(self, topic: str, handler: Callable):
        """注册消息处理器"""
        self.message_handlers[topic] = handler
        logger.info(f"Registered handler for topic: {topic}")
    
    async def start(self):
        """启动消费者"""
        try:
            self.consumer = AIOKafkaConsumer(
                *self.topics,
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.group_id,
                value_deserializer=self._deserialize_message,
                auto_offset_reset="earliest",
                enable_auto_commit=True,
                max_poll_records=100
            )
            await self.consumer.start()
            logger.info(f"Kafka consumer started for topics: {self.topics}")
        except Exception as e:
            logger.error(f"Failed to start Kafka consumer: {str(e)}")
            raise
    
    async def stop(self):
        """停止消费者"""
        if self.consumer:
            await self.consumer.stop()
            logger.info("Kafka consumer stopped")
    
    def _deserialize_message(self, message: bytes) -> Dict[str, Any]:
        """反序列化消息"""
        try:
            return json.loads(message.decode("utf-8"))
        except json.JSONDecodeError:
            logger.error("Failed to deserialize message")
            return {}
    
    async def consume(self):
        """开始消费消息"""
        if not self.consumer:
            logger.error("Consumer not started")
            return
        
        try:
            async for record in self.consumer:
                await self._process_message(record)
        except Exception as e:
            logger.error(f"Error consuming messages: {str(e)}")
    
    async def _process_message(self, record: ConsumerRecord):
        """处理单条消息"""
        topic = record.topic
        message = record.value
        
        logger.debug(f"Received message from topic {topic}: {message}")
        
        handler = self.message_handlers.get(topic)
        if handler:
            try:
                await handler(message)
                logger.debug(f"Message processed successfully for topic {topic}")
            except Exception as e:
                logger.error(f"Error processing message for topic {topic}: {str(e)}")
        else:
            logger.warning(f"No handler registered for topic {topic}")


# 全局消费者实例
consumer_instances = {}


def get_consumer(topics: list, group_id: str = "game_training_group") -> KafkaConsumer:
    """获取或创建消费者实例"""
    key = f"{group_id}_{'_'.join(sorted(topics))}"
    if key not in consumer_instances:
        consumer = KafkaConsumer(topics, group_id)
        consumer_instances[key] = consumer
    return consumer_instances[key]


# 消息处理器示例
async def handle_audit_log(message: Dict[str, Any]):
    """处理审计日志消息"""
    logger.info(f"Audit log received: {message}")
    # 这里可以添加实际的日志存储逻辑


async def handle_email_notification(message: Dict[str, Any]):
    """处理邮件通知消息"""
    logger.info(f"Email notification received: {message}")
    # 这里可以添加实际的邮件发送逻辑


async def handle_user_registered(message: Dict[str, Any]):
    """处理用户注册消息"""
    logger.info(f"User registered: {message}")
    # 这里可以添加用户注册后的后续处理


async def handle_level_completed(message: Dict[str, Any]):
    """处理关卡完成消息"""
    logger.info(f"Level completed: {message}")
    # 这里可以添加关卡完成后的逻辑（如更新排行榜）


async def handle_achievement_unlocked(message: Dict[str, Any]):
    """处理成就解锁消息"""
    logger.info(f"Achievement unlocked: {message}")
    # 这里可以添加成就解锁后的逻辑


# 默认处理器注册
def register_default_handlers(consumer: KafkaConsumer):
    """注册默认消息处理器"""
    consumer.register_handler(KafkaTopics.AUDIT_LOG, handle_audit_log)
    consumer.register_handler(KafkaTopics.EMAIL_NOTIFICATION, handle_email_notification)
    consumer.register_handler(KafkaTopics.USER_REGISTERED, handle_user_registered)
    consumer.register_handler(KafkaTopics.LEVEL_COMPLETED, handle_level_completed)
    consumer.register_handler(KafkaTopics.ACHIEVEMENT_UNLOCKED, handle_achievement_unlocked)