from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.trace import Tracer
from apps.core.config import settings
import logging

logger = logging.getLogger(__name__)

tracer_provider = None
tracer = None


def init_otel():
    """初始化OpenTelemetry追踪"""
    global tracer_provider, tracer
    
    if not settings.OTEL_ENABLED:
        logger.info("OpenTelemetry is disabled")
        return
    
    try:
        resource = Resource(attributes={
            "service.name": settings.APP_NAME,
            "service.version": "2.0.0",
            "environment": settings.APP_ENV
        })
        
        tracer_provider = TracerProvider(resource=resource)
        
        # 添加OTLP导出器
        if settings.OTEL_COLLECTOR_URL:
            exporter = OTLPSpanExporter(endpoint=settings.OTEL_COLLECTOR_URL)
            span_processor = BatchSpanProcessor(exporter)
            tracer_provider.add_span_processor(span_processor)
            logger.info(f"OTLP exporter configured: {settings.OTEL_COLLECTOR_URL}")
        
        # 设置全局tracer provider
        trace.set_tracer_provider(tracer_provider)
        tracer = trace.get_tracer(settings.APP_NAME)
        
        logger.info("OpenTelemetry initialized successfully")
        
        return tracer
    except Exception as e:
        logger.error(f"Failed to initialize OpenTelemetry: {str(e)}")
        return None


def instrument_app(app):
    """为FastAPI应用添加追踪"""
    if not settings.OTEL_ENABLED or not tracer_provider:
        return
    
    try:
        FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer_provider)
        RequestsInstrumentor().instrument(tracer_provider=tracer_provider)
        RedisInstrumentor().instrument(tracer_provider=tracer_provider)
        logger.info("Application instrumented with OpenTelemetry")
    except Exception as e:
        logger.error(f"Failed to instrument application: {str(e)}")


def get_tracer() -> Tracer:
    """获取tracer实例"""
    return tracer or trace.get_tracer(settings.APP_NAME)


def trace_span(name: str, **kwargs):
    """创建追踪装饰器"""
    def decorator(func):
        if not settings.OTEL_ENABLED:
            return func
        
        async def async_wrapper(*args, **async_kwargs):
            with get_tracer().start_as_current_span(name, attributes=kwargs):
                return await func(*args, **async_kwargs)
        
        def sync_wrapper(*args, **sync_kwargs):
            with get_tracer().start_as_current_span(name, attributes=kwargs):
                return func(*args, **sync_kwargs)
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


# 追踪工具函数
class TraceContext:
    """追踪上下文管理器"""
    
    def __init__(self, span_name: str, **attributes):
        self.span_name = span_name
        self.attributes = attributes
    
    def __enter__(self):
        if not settings.OTEL_ENABLED:
            return self
        self.span = get_tracer().start_span(self.span_name, attributes=self.attributes)
        self.span.__enter__()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if not settings.OTEL_ENABLED:
            return
        self.span.__exit__(exc_type, exc_val, exc_tb)
    
    async def __aenter__(self):
        return self.__enter__()
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.__exit__(exc_type, exc_val, exc_tb)
    
    def set_attribute(self, key: str, value):
        """设置span属性"""
        if settings.OTEL_ENABLED and self.span:
            self.span.set_attribute(key, value)