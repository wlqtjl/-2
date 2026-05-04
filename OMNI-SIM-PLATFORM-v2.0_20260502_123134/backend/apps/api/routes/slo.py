from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from apps.core.slo_monitor import SLOMonitor, SLOCalculator, SLIResult, SLOReport, slo_monitor
from apps.api.deps import get_current_user, require_admin
from apps.core.models import User
from apps.core.database import SessionLocal
import os

try:
    import psutil  # type: ignore
except ImportError:  # pragma: no cover
    psutil = None  # type: ignore

router = APIRouter(prefix="/slo", tags=["SLO 监控"])


class MetricRecord(BaseModel):
    endpoint: str
    latency_ms: float
    success: bool
    timestamp: Optional[datetime] = None
    status_code: Optional[int] = None
    request_id: Optional[str] = None


class SLOStatusResponse(BaseModel):
    status: str
    sli_results: List[SLIResult]
    error_budgets: dict
    alerts: List[dict]


class HealthCheckResponse(BaseModel):
    status: str
    timestamp: datetime
    uptime: float
    components: Dict[str, str]
    system_info: Dict[str, Any]


class LogQueryParams(BaseModel):
    level: Optional[str] = None
    since_minutes: int = 10
    limit: int = 100


@router.post("/metrics", status_code=201)
async def record_metric(
    metric: MetricRecord,
    current_user: User = Depends(get_current_user)
):
    await slo_monitor.record_request(
        endpoint=metric.endpoint,
        latency_ms=metric.latency_ms,
        success=metric.success,
        timestamp=metric.timestamp,
        status_code=metric.status_code,
        request_id=metric.request_id,
        user_id=current_user.id
    )
    return {"status": "recorded"}


@router.get("/status", response_model=SLOStatusResponse)
async def get_slo_status(
    window_hours: int = 24,
    current_user: User = Depends(require_admin)
):
    window_start = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    sli_results = await slo_monitor.get_sli_results(window_start)
    report = await slo_monitor.generate_report(window_start)
    alerts = slo_monitor.get_alerts(since=datetime.now(timezone.utc) - timedelta(hours=window_hours))

    return SLOStatusResponse(
        status=report.overall_status,
        sli_results=sli_results,
        error_budgets={
            name: {
                "total_budget": budget.total_budget,
                "spent": budget.spent,
                "remaining": budget.remaining,
                "percentage_remaining": budget.percentage_remaining
            }
            for name, budget in report.error_budgets.items()
        },
        alerts=alerts
    )


@router.get("/report")
async def get_slo_report(
    period_days: int = 30,
    current_user: User = Depends(require_admin)
):
    period_start = datetime.now(timezone.utc) - timedelta(days=period_days)
    report = await slo_monitor.generate_report(period_start)

    return {
        "generated_at": report.generated_at.isoformat(),
        "period_start": report.period_start.isoformat(),
        "period_end": report.period_end.isoformat(),
        "overall_status": report.overall_status,
        "sli_results": [
            {
                "name": r.name,
                "sli_value": round(r.sli_value, 4),
                "target": r.target,
                "status": r.status,
                "breach": r.breach
            }
            for r in report.sli_results
        ],
        "error_budgets": {
            name: {
                "total_budget": round(budget.total_budget, 2),
                "spent": round(budget.spent, 2),
                "remaining": round(budget.remaining, 2),
                "percentage_remaining": round(budget.percentage_remaining, 2)
            }
            for name, budget in report.error_budgets.items()
        }
    }


@router.get("/alerts")
async def get_alerts(
    since_hours: int = 1,
    current_user: User = Depends(require_admin)
):
    since = datetime.now(timezone.utc) - timedelta(hours=since_hours)
    alerts = slo_monitor.get_alerts(since)
    return {"alerts": alerts, "count": len(alerts)}


@router.delete("/alerts")
async def clear_alerts(current_user: User = Depends(require_admin)):
    slo_monitor.clear_alerts()
    return {"status": "cleared"}


@router.get("/health", response_model=HealthCheckResponse)
async def health_check(current_user: User = Depends(require_admin)):
    """综合健康检查（含主机信息，仅管理员可访问）"""
    if psutil is None:
        raise HTTPException(status_code=503, detail="psutil 依赖未安装")
    uptime = psutil.Process(os.getpid()).create_time()
    uptime_hours = (datetime.now().timestamp() - uptime) / 3600
    
    components = {
        "api": "healthy",
        "database": "healthy",
        "redis": "healthy",
        "vector_db": "healthy"
    }
    
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
    except Exception as e:
        components["database"] = f"unhealthy: {str(e)}"
    
    system_info = {
        "cpu_percent": psutil.cpu_percent(),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage('/').percent,
        "network_io": {
            "bytes_sent": psutil.net_io_counters().bytes_sent,
            "bytes_recv": psutil.net_io_counters().bytes_recv
        },
        "process_count": len(psutil.pids()),
        "uptime_hours": round(uptime_hours, 2)
    }
    
    overall_status = "healthy" if all(v == "healthy" for v in components.values()) else "degraded"
    
    return HealthCheckResponse(
        status=overall_status,
        timestamp=datetime.now(timezone.utc),
        uptime=uptime_hours,
        components=components,
        system_info=system_info
    )


@router.get("/health/detailed")
async def detailed_health_check(current_user: User = Depends(require_admin)):
    """详细健康检查（仅管理员）"""
    if psutil is None:
        raise HTTPException(status_code=503, detail="psutil 依赖未安装")
    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "system": {
            "cpu": {
                "percent": psutil.cpu_percent(),
                "cores": psutil.cpu_count(),
                "frequency": psutil.cpu_freq().current if psutil.cpu_freq() else None
            },
            "memory": {
                "total": psutil.virtual_memory().total,
                "available": psutil.virtual_memory().available,
                "used": psutil.virtual_memory().used,
                "percent": psutil.virtual_memory().percent
            },
            "disk": {
                "total": psutil.disk_usage('/').total,
                "used": psutil.disk_usage('/').used,
                "free": psutil.disk_usage('/').free,
                "percent": psutil.disk_usage('/').percent
            },
            "network": {
                "bytes_sent": psutil.net_io_counters().bytes_sent,
                "bytes_recv": psutil.net_io_counters().bytes_recv,
                "packets_sent": psutil.net_io_counters().packets_sent,
                "packets_recv": psutil.net_io_counters().packets_recv
            },
            "process": {
                "pid": os.getpid(),
                "memory_percent": psutil.Process(os.getpid()).memory_percent(),
                "cpu_percent": psutil.Process(os.getpid()).cpu_percent()
            }
        },
        "services": {}
    }
    
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        results["services"]["database"] = {"status": "healthy"}
    except Exception as e:
        results["services"]["database"] = {"status": "unhealthy", "error": str(e)}
    
    try:
        import redis
        r = redis.Redis.from_url("redis://localhost:6379/0")
        r.ping()
        results["services"]["redis"] = {"status": "healthy"}
    except Exception as e:
        results["services"]["redis"] = {"status": "unhealthy", "error": str(e)}
    
    return results


@router.get("/logs")
async def get_logs(
    level: Optional[str] = None,
    since_minutes: int = 10,
    limit: int = 100,
    current_user: User = Depends(require_admin)
):
    """获取日志条目"""
    since = datetime.now(timezone.utc) - timedelta(minutes=since_minutes)
    logs = slo_monitor.get_logs(since=since, level=level, limit=limit)
    
    return {
        "logs": [
            {
                "timestamp": log.timestamp.isoformat(),
                "level": log.level,
                "message": log.message,
                "module": log.module,
                "endpoint": log.endpoint,
                "status_code": log.status_code,
                "latency_ms": log.latency_ms
            }
            for log in logs
        ],
        "count": len(logs)
    }


@router.get("/logs/summary")
async def get_log_summary(
    hours: int = 24,
    current_user: User = Depends(require_admin)
):
    """获取日志摘要"""
    summary = slo_monitor.get_log_summary(hours)
    return summary


@router.get("/metrics/summary")
async def get_metrics_summary(current_user: User = Depends(require_admin)):
    """获取指标摘要"""
    return slo_monitor.get_metric_summary()


@router.get("/metrics/endpoints")
async def get_endpoint_metrics(
    limit: int = 10,
    current_user: User = Depends(require_admin)
):
    """获取端点指标"""
    return {"endpoints": slo_monitor.get_endpoint_metrics(limit)}


@router.get("/dashboard")
async def get_monitoring_dashboard(current_user: User = Depends(require_admin)):
    """获取监控仪表盘数据"""
    summary = slo_monitor.get_metric_summary()
    endpoint_metrics = slo_monitor.get_endpoint_metrics(10)
    log_summary = slo_monitor.get_log_summary(24)
    recent_alerts = slo_monitor.get_alerts(datetime.now(timezone.utc) - timedelta(hours=24))
    
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "overview": summary,
        "top_endpoints": endpoint_metrics,
        "log_summary": log_summary,
        "recent_alerts": recent_alerts,
        "alert_count": len(recent_alerts)
    }


@router.post("/log")
async def log_message(
    level: str = "INFO",
    message: str = "",
    endpoint: Optional[str] = None,
    status_code: Optional[int] = None,
    latency_ms: Optional[float] = None,
    current_user: User = Depends(get_current_user)
):
    """记录日志消息"""
    slo_monitor.log(
        level=level,
        message=message,
        endpoint=endpoint,
        status_code=status_code,
        latency_ms=latency_ms,
        user_id=current_user.id
    )
    return {"status": "logged"}


@router.get("/system/metrics")
async def get_system_metrics(
    names: Optional[List[str]] = None,
    current_user: User = Depends(require_admin)
):
    """获取系统指标"""
    metrics = slo_monitor.get_system_metrics(names)
    return {
        "metrics": [
            {
                "name": m.name,
                "value": m.value,
                "unit": m.unit,
                "timestamp": m.timestamp.isoformat(),
                "labels": m.labels
            }
            for m in metrics
        ]
    }
