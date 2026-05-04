from fastapi import APIRouter, Depends
from typing import Optional
from apps.core.analytics import DashboardService, analytics_data
from apps.api.deps import get_current_user, require_admin, require_admin_or_instructor

router = APIRouter(prefix="/analytics", tags=["数据分析"])

dashboard_service = DashboardService(analytics_data)


@router.get("/summary")
async def get_summary(current_user = Depends(require_admin_or_instructor)):
    cards = dashboard_service.get_summary_cards()
    return {
        "cards": [
            {
                "id": c.id,
                "title": c.title,
                "value": c.value,
                "change": c.change,
                "change_type": c.change_type
            }
            for c in cards
        ]
    }


@router.get("/user-growth")
async def get_user_growth(
    days: int = 30,
    current_user = Depends(require_admin_or_instructor)
):
    return dashboard_service.get_user_growth(days)


@router.get("/level-popularity")
async def get_level_popularity(current_user = Depends(require_admin_or_instructor)):
    return {"levels": dashboard_service.get_level_popularity()}


@router.get("/learning-path")
async def get_learning_path(current_user = Depends(require_admin_or_instructor)):
    return dashboard_service.get_learning_path()


@router.get("/error-distribution")
async def get_error_distribution(current_user = Depends(require_admin_or_instructor)):
    return {"errors": dashboard_service.get_error_distribution()}


@router.get("/performance-trends")
async def get_performance_trends(
    period: str = "daily",
    current_user = Depends(require_admin_or_instructor)
):
    trends = dashboard_service.get_performance_trends()
    return trends.get(period, trends["daily"])


@router.post("/metrics/{metric_name}")
async def record_metric(
    metric_name: str,
    value: float,
    label: Optional[str] = None,
    current_user = Depends(require_admin)
):
    analytics_data.record_metric(metric_name, value, label=label)
    return {"status": "recorded"}


@router.get("/metrics/{metric_name}")
async def get_metric(
    metric_name: str,
    hours: int = 24,
    current_user = Depends(require_admin_or_instructor)
):
    data = analytics_data.get_metric(metric_name, hours)
    return {
        "metric_name": metric_name,
        "data": [
            {"timestamp": m.timestamp.isoformat(), "value": m.value, "label": m.label}
            for m in data
        ],
        "average": analytics_data.calculate_average(metric_name, hours),
        "total": analytics_data.calculate_total(metric_name, hours)
    }
