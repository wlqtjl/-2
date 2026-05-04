from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel
from dataclasses import dataclass


@dataclass
class MetricDataPoint:
    timestamp: datetime
    value: float
    label: Optional[str] = None


@dataclass
class DashboardCard:
    id: str
    title: str
    value: float | str
    change: Optional[float] = None
    change_type: Optional[str] = None
    trend: Optional[List[float]] = None


class AnalyticsData:
    def __init__(self):
        self.metrics: Dict[str, List[MetricDataPoint]] = {}

    def record_metric(
        self,
        metric_name: str,
        value: float,
        timestamp: Optional[datetime] = None,
        label: Optional[str] = None
    ):
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)

        if metric_name not in self.metrics:
            self.metrics[metric_name] = []

        self.metrics[metric_name].append(MetricDataPoint(
            timestamp=timestamp,
            value=value,
            label=label
        ))

        if len(self.metrics[metric_name]) > 1000:
            self.metrics[metric_name] = self.metrics[metric_name][-1000:]

    def get_metric(
        self,
        metric_name: str,
        hours: int = 24
    ) -> List[MetricDataPoint]:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        metric_data = self.metrics.get(metric_name, [])
        return [m for m in metric_data if m.timestamp >= cutoff]

    def calculate_average(
        self,
        metric_name: str,
        hours: int = 24
    ) -> float:
        data = self.get_metric(metric_name, hours)
        if not data:
            return 0.0
        return sum(m.value for m in data) / len(data)

    def calculate_total(
        self,
        metric_name: str,
        hours: int = 24
    ) -> float:
        data = self.get_metric(metric_name, hours)
        return sum(m.value for m in data)


class DashboardService:
    def __init__(self, analytics: AnalyticsData):
        self.analytics = analytics

    def get_summary_cards(self) -> List[DashboardCard]:
        return [
            DashboardCard(
                id="total_users",
                title="总用户数",
                value=1247,
                change=12.5,
                change_type="increase"
            ),
            DashboardCard(
                id="active_users",
                title="活跃用户",
                value=342,
                change=8.2,
                change_type="increase"
            ),
            DashboardCard(
                id="completion_rate",
                title="关卡完成率",
                value="78.5%",
                change=3.1,
                change_type="increase"
            ),
            DashboardCard(
                id="avg_score",
                title="平均分数",
                value=85.6,
                change=2.4,
                change_type="increase"
            )
        ]

    def get_user_growth(self, days: int = 30) -> Dict[str, Any]:
        growth_data = []
        for i in range(days):
            date = datetime.now(timezone.utc) - timedelta(days=days - i - 1)
            growth_data.append({
                "date": date.strftime("%Y-%m-%d"),
                "value": 1000 + i * 15 + (i % 3) * 10
            })
        return {
            "data": growth_data,
            "total_growth": "15.2%"
        }

    def get_level_popularity(self) -> List[Dict[str, Any]]:
        return [
            {"level_id": 1, "name": "入门训练", "completions": 1245, "avg_score": 92.3},
            {"level_id": 2, "name": "进阶挑战", "completions": 987, "avg_score": 85.1},
            {"level_id": 3, "name": "专家考核", "completions": 654, "avg_score": 78.9},
            {"level_id": 4, "name": "实战演练", "completions": 432, "avg_score": 72.4},
            {"level_id": 5, "name": "最终测试", "completions": 321, "avg_score": 68.2}
        ]

    def get_learning_path(self) -> Dict[str, Any]:
        return {
            "stages": [
                {"name": "基础入门", "progress": 100, "avg_time": "2小时"},
                {"name": "技能进阶", "progress": 78, "avg_time": "4小时"},
                {"name": "实战应用", "progress": 45, "avg_time": "6小时"},
                {"name": "综合考核", "progress": 12, "avg_time": "3小时"}
            ],
            "total_estimate": "15小时"
        }

    def get_error_distribution(self) -> List[Dict[str, Any]]:
        return [
            {"error_type": "超时错误", "count": 234, "percentage": 35.2},
            {"error_type": "答案错误", "count": 189, "percentage": 28.4},
            {"error_type": "网络异常", "count": 145, "percentage": 21.8},
            {"error_type": "其他错误", "count": 97, "percentage": 14.6}
        ]

    def get_performance_trends(self) -> Dict[str, Any]:
        return {
            "daily": self._generate_trend_data(24, "小时"),
            "weekly": self._generate_trend_data(7, "天"),
            "monthly": self._generate_trend_data(30, "天")
        }

    def _generate_trend_data(self, points: int, unit: str) -> List[Dict[str, Any]]:
        data = []
        for i in range(points):
            data.append({
                "label": f"{i}{unit}" if unit == "小时" else f"第{i+1}{unit}",
                "value": 70 + (i % 10) * 2 + (points - i) * 0.5
            })
        return data


analytics_data = AnalyticsData()
dashboard_service = DashboardService(analytics_data)
