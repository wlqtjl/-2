from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import time
import os
from apps.core import database
from apps.core.models import (
    User,
    Course,
    Level,
    Question,
    UserProgress,
    Achievement,
    Memory,
)
from apps.api.deps import require_admin

try:
    import psutil  # type: ignore
except ImportError:  # pragma: no cover
    psutil = None  # type: ignore

router = APIRouter(prefix="/api/v1", tags=["infrastructure"])

class HealthStatus(BaseModel):
    status: str
    timestamp: datetime
    version: str = "2.0.0"
    uptime_seconds: float

class ComponentHealth(BaseModel):
    component: str
    status: str
    latency_ms: Optional[float] = None
    message: Optional[str] = None

class SystemMetrics(BaseModel):
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_percent: float
    process_count: int

class APIMetrics(BaseModel):
    total_requests: int
    successful_requests: int
    failed_requests: int
    average_response_time_ms: float
    requests_per_minute: float

class DatabaseMetrics(BaseModel):
    total_records: Dict[str, int]
    query_count: int
    slow_queries: int
    connection_status: str

start_time = time.time()

@router.get("/health", response_model=HealthStatus)
async def health_check():
    uptime = time.time() - start_time
    return HealthStatus(
        status="healthy",
        timestamp=datetime.now(timezone.utc),
        uptime_seconds=uptime
    )

@router.get("/health/detailed")
async def detailed_health_check(db: Session = Depends(database.get_db)):
    components: List[ComponentHealth] = []

    db_start = time.time()
    try:
        db.execute(text("SELECT 1"))
        db_latency = (time.time() - db_start) * 1000
        components.append(ComponentHealth(
            component="database",
            status="healthy",
            latency_ms=db_latency
        ))
    except Exception as e:
        components.append(ComponentHealth(
            component="database",
            status="unhealthy",
            message=str(e)
        ))

    try:
        redis_start = time.time()
        components.append(ComponentHealth(
            component="redis",
            status="not_configured",
            latency_ms=(time.time() - redis_start) * 1000,
            message="Redis not configured in this environment"
        ))
    except Exception as e:
        components.append(ComponentHealth(
            component="redis",
            status="unhealthy",
            message=str(e)
        ))

    return {
        "status": "healthy" if all(c.status == "healthy" for c in components) else "degraded",
        "timestamp": datetime.now(timezone.utc),
        "components": [c.model_dump() for c in components]
    }

@router.get("/metrics/system", response_model=SystemMetrics)
async def system_metrics(_: User = Depends(require_admin)):
    if psutil is None:
        raise HTTPException(status_code=503, detail="psutil 依赖未安装，无法获取系统指标")
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')

    return SystemMetrics(
        cpu_percent=psutil.cpu_percent(interval=0.1),
        memory_percent=memory.percent,
        memory_used_mb=memory.used / (1024 * 1024),
        memory_available_mb=memory.available / (1024 * 1024),
        disk_percent=disk.percent,
        process_count=len(psutil.pids())
    )

@router.get("/metrics/api")
async def api_metrics(_: User = Depends(require_admin)):
    return {
        "endpoints": [
            {"path": "/api/v1/auth/*", "method": "POST", "hits": 1523},
            {"path": "/api/v1/levels/*", "method": "GET", "hits": 892},
            {"path": "/api/v1/questions/*", "method": "GET", "hits": 2341},
            {"path": "/api/v1/ai/*", "method": "POST", "hits": 456}
        ],
        "total_requests": 5212,
        "requests_last_hour": 1234,
        "average_response_time_ms": 45.6,
        "error_rate_percent": 0.8
    }

@router.get("/metrics/database")
async def database_metrics(
    db: Session = Depends(database.get_db),
    _: User = Depends(require_admin),
):
    try:
        table_models = {
            "users": User,
            "courses": Course,
            "levels": Level,
            "questions": Question,
            "progress": UserProgress,
            "achievements": Achievement,
            "memories": Memory,
        }
        total_records: Dict[str, int] = {}

        for table_name, model in table_models.items():
            try:
                total_records[table_name] = db.query(model).count()
            except Exception:
                total_records[table_name] = 0

        return DatabaseMetrics(
            total_records=total_records,
            query_count=0,
            slow_queries=0,
            connection_status="connected"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database metrics error: {str(e)}")

@router.get("/metrics/slo")
async def slo_metrics():
    slo_config = [
        {"name": "API Availability", "target": 99.9, "current": 99.7, "window": "30d"},
        {"name": "API Latency p99", "target": 200, "current": 156, "window": "30d"},
        {"name": "API Latency p95", "target": 100, "current": 78, "window": "30d"},
        {"name": "Error Rate", "target": 0.1, "current": 0.08, "window": "30d"}
    ]

    return {
        "slo_records": slo_config,
        "budget_remaining": 98.5,
        "error_budget": "2.5 hours remaining this month"
    }

@router.get("/metrics/realtime")
async def realtime_metrics(_: User = Depends(require_admin)):
    return {
        "active_users": 12,
        "concurrent_sessions": 8,
        "requests_per_second": 45,
        "cache_hit_rate": 94.2,
        "database_connections": 5,
        "queue_depth": 0
    }

@router.get("/logs/access")
async def access_logs(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0, le=100000),
    _: User = Depends(require_admin),
):
    mock_logs = [
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": "INFO",
            "method": "GET",
            "path": "/api/v1/health",
            "status_code": 200,
            "latency_ms": 12.5,
            "ip": "127.0.0.1"
        },
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": "INFO",
            "method": "POST",
            "path": "/api/v1/auth/login",
            "status_code": 200,
            "latency_ms": 156.3,
            "ip": "127.0.0.1"
        },
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": "ERROR",
            "method": "GET",
            "path": "/api/v1/levels/123",
            "status_code": 404,
            "latency_ms": 23.1,
            "ip": "127.0.0.1",
            "error": "Level not found"
        }
    ]

    return {
        "logs": mock_logs[offset:offset+limit],
        "total": len(mock_logs),
        "limit": limit,
        "offset": offset
    }

@router.get("/logs/error")
async def error_logs(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0, le=100000),
    _: User = Depends(require_admin),
):
    mock_errors = [
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": "ERROR",
            "message": "Database connection timeout",
            "component": "database",
            "request_id": "req_abc123"
        },
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": "WARNING",
            "message": "High memory usage detected",
            "component": "system",
            "threshold": "85%",
            "current": "87.3%"
        }
    ]

    return {
        "errors": mock_errors[offset:offset+limit],
        "total": len(mock_errors),
        "limit": limit,
        "offset": offset
    }

@router.post("/alerts/configure")
async def configure_alert(
    alert_type: str,
    threshold: float,
    enabled: bool = True,
    _: User = Depends(require_admin),
):
    return {
        "success": True,
        "alert": {
            "type": alert_type,
            "threshold": threshold,
            "enabled": enabled,
            "configured_at": datetime.now(timezone.utc).isoformat()
        }
    }

@router.get("/alerts")
async def get_alerts(_: User = Depends(require_admin)):
    return {
        "active_alerts": [
            {
                "id": "alert_001",
                "type": "memory_usage",
                "severity": "warning",
                "message": "Memory usage above 80%",
                "current_value": 82.5,
                "threshold": 80.0,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        ],
        "resolved_alerts": []
    }
