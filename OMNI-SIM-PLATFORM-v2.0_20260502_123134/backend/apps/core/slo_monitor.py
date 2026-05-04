from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel
from dataclasses import dataclass, field
import asyncio
from collections import defaultdict
import logging


@dataclass
class SLOTarget:
    name: str
    target_type: str
    target_value: float
    window_seconds: int


@dataclass
class SLIResult:
    name: str
    sli_value: float
    target: float
    status: str
    timestamp: datetime
    breach: bool


@dataclass
class ErrorBudget:
    total_budget: float
    spent: float
    remaining: float
    percentage_remaining: float


@dataclass
class SLOReport:
    generated_at: datetime
    period_start: datetime
    period_end: datetime
    sli_results: List[SLIResult]
    error_budgets: Dict[str, ErrorBudget]
    overall_status: str


@dataclass
class SystemMetric:
    name: str
    value: float
    unit: str
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)


class SLOCalculator:
    def __init__(self):
        self.slo_targets = {
            "availability": SLOTarget(
                name="availability",
                target_type="availability",
                target_value=0.995,
                window_seconds=86400 * 30
            ),
            "latency_p50": SLOTarget(
                name="latency_p50",
                target_type="latency",
                target_value=200,
                window_seconds=86400 * 30
            ),
            "latency_p99": SLOTarget(
                name="latency_p99",
                target_type="latency",
                target_value=1000,
                window_seconds=86400 * 30
            ),
            "error_rate": SLOTarget(
                name="error_rate",
                target_type="error_rate",
                target_value=0.01,
                window_seconds=86400 * 30
            ),
            "throughput": SLOTarget(
                name="throughput",
                target_type="throughput",
                target_value=100,
                window_seconds=60
            )
        }

    def calculate_availability(
        self,
        total_requests: int,
        failed_requests: int
    ) -> float:
        if total_requests == 0:
            return 1.0
        return (total_requests - failed_requests) / total_requests

    def calculate_latency_score(
        self,
        latencies: List[float],
        target_p99: float
    ) -> float:
        if not latencies:
            return 1.0
        latencies.sort()
        p99_idx = int(len(latencies) * 0.99)
        p99_latency = latencies[p99_idx] if latencies else 0
        if p99_latency <= target_p99:
            return 1.0
        return max(0, 1 - (p99_latency - target_p99) / target_p99)

    def check_slo_status(self, sli_value: float, target: float, target_type: str) -> tuple[bool, str]:
        if target_type == "availability":
            if sli_value >= target:
                return False, "healthy"
            elif sli_value >= target * 0.95:
                return False, "warning"
            return True, "breached"
        elif target_type == "throughput":
            if sli_value >= target:
                return False, "healthy"
            elif sli_value >= target * 0.8:
                return False, "warning"
            return True, "breached"
        elif target_type in ["latency", "error_rate"]:
            if sli_value <= target:
                return False, "healthy"
            elif sli_value <= target * 1.1:
                return False, "warning"
            return True, "breached"
        return False, "unknown"

    def calculate_error_budget(
        self,
        total_budget: float,
        sli_value: float,
        target_type: str
    ) -> ErrorBudget:
        if target_type == "availability":
            spent = (1 - sli_value) * total_budget
        elif target_type == "error_rate":
            spent = sli_value * total_budget
        else:
            spent = 0

        remaining = total_budget - spent
        return ErrorBudget(
            total_budget=total_budget,
            spent=max(0, spent),
            remaining=max(0, remaining),
            percentage_remaining=max(0, (remaining / total_budget * 100)) if total_budget > 0 else 100
        )


class LogEntry(BaseModel):
    timestamp: datetime
    level: str
    message: str
    module: Optional[str] = None
    request_id: Optional[str] = None
    endpoint: Optional[str] = None
    user_id: Optional[int] = None
    status_code: Optional[int] = None
    latency_ms: Optional[float] = None


class SLOMonitor:
    def __init__(self, calculator: SLOCalculator):
        self.calculator = calculator
        self.metrics_store: Dict[str, List[Dict[str, Any]]] = {}
        self.alerts: List[Dict[str, Any]] = []
        self.log_entries: List[LogEntry] = []
        self.system_metrics: List[SystemMetric] = []
        self.max_log_entries = 10000
        self.max_metrics_entries = 100000
        self.logger = logging.getLogger("slo_monitor")

    async def record_request(
        self,
        endpoint: str,
        latency_ms: float,
        success: bool,
        timestamp: Optional[datetime] = None,
        status_code: Optional[int] = None,
        request_id: Optional[str] = None,
        user_id: Optional[int] = None
    ):
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)

        if endpoint not in self.metrics_store:
            self.metrics_store[endpoint] = []

        self.metrics_store[endpoint].append({
            "timestamp": timestamp,
            "latency_ms": latency_ms,
            "success": success,
            "status_code": status_code,
            "request_id": request_id,
            "user_id": user_id
        })

        if len(self.metrics_store[endpoint]) > self.max_metrics_entries:
            self.metrics_store[endpoint] = self.metrics_store[endpoint][-self.max_metrics_entries:]

        await self._check_alerts(endpoint)

    async def record_log(self, entry: LogEntry):
        self.log_entries.append(entry)
        if len(self.log_entries) > self.max_log_entries:
            self.log_entries = self.log_entries[-self.max_log_entries:]

    def log(self, level: str, message: str, **kwargs):
        entry = LogEntry(
            timestamp=datetime.now(timezone.utc),
            level=level,
            message=message,
            **kwargs
        )
        asyncio.create_task(self.record_log(entry))

    async def record_system_metric(self, name: str, value: float, unit: str, labels: Dict[str, str] = None):
        metric = SystemMetric(
            name=name,
            value=value,
            unit=unit,
            timestamp=datetime.now(timezone.utc),
            labels=labels or {}
        )
        self.system_metrics.append(metric)
        if len(self.system_metrics) > self.max_metrics_entries:
            self.system_metrics = self.system_metrics[-self.max_metrics_entries:]

    async def _check_alerts(self, endpoint: str):
        recent = datetime.now(timezone.utc) - timedelta(minutes=5)
        recent_requests = [
            m for m in self.metrics_store.get(endpoint, [])
            if m["timestamp"] >= recent
        ]

        if len(recent_requests) >= 10:
            failed = sum(1 for r in recent_requests if not r["success"])
            error_rate = failed / len(recent_requests)

            if error_rate > 0.05:
                alert_exists = any(
                    a for a in self.alerts
                    if a["endpoint"] == endpoint and
                    a["type"] == "high_error_rate" and
                    a["timestamp"] > datetime.now(timezone.utc) - timedelta(minutes=1)
                )
                if not alert_exists:
                    self.alerts.append({
                        "type": "high_error_rate",
                        "endpoint": endpoint,
                        "error_rate": round(error_rate, 4),
                        "timestamp": datetime.now(timezone.utc),
                        "severity": "critical" if error_rate > 0.1 else "warning",
                        "message": f"高错误率告警: {endpoint} 的错误率达到 {error_rate:.2%}"
                    })

            avg_latency = sum(r["latency_ms"] for r in recent_requests) / len(recent_requests)
            if avg_latency > 500:
                alert_exists = any(
                    a for a in self.alerts
                    if a["endpoint"] == endpoint and
                    a["type"] == "high_latency" and
                    a["timestamp"] > datetime.now(timezone.utc) - timedelta(minutes=1)
                )
                if not alert_exists:
                    self.alerts.append({
                        "type": "high_latency",
                        "endpoint": endpoint,
                        "avg_latency_ms": round(avg_latency, 2),
                        "timestamp": datetime.now(timezone.utc),
                        "severity": "warning",
                        "message": f"高延迟告警: {endpoint} 的平均延迟达到 {avg_latency:.2f}ms"
                    })

    async def get_sli_results(
        self,
        window_start: Optional[datetime] = None,
        window_end: Optional[datetime] = None
    ) -> List[SLIResult]:
        if window_start is None:
            window_start = datetime.now(timezone.utc) - timedelta(days=30)
        if window_end is None:
            window_end = datetime.now(timezone.utc)

        results = []
        all_requests = []

        for endpoint, metrics in self.metrics_store.items():
            endpoint_requests = [
                m for m in metrics
                if window_start <= m["timestamp"] <= window_end
            ]
            all_requests.extend(endpoint_requests)

        if not all_requests:
            return results

        total_requests = len(all_requests)
        failed_requests = sum(1 for r in all_requests if not r["success"])
        availability = self.calculator.calculate_availability(total_requests, failed_requests)

        latencies = [r["latency_ms"] for r in all_requests]
        latencies.sort()

        window_seconds = (window_end - window_start).total_seconds()
        throughput = total_requests / window_seconds if window_seconds > 0 else 0

        for target_name, target in self.calculator.slo_targets.items():
            if target_name == "availability":
                sli_value = availability
                breach, status = self.calculator.check_slo_status(
                    sli_value, target.target_value, target.target_type
                )
                results.append(SLIResult(
                    name=target_name,
                    sli_value=sli_value,
                    target=target.target_value,
                    status=status,
                    timestamp=datetime.now(timezone.utc),
                    breach=breach
                ))
            elif target_name == "latency_p50":
                p_idx = int(len(latencies) * 0.50) if latencies else 0
                p_latency = latencies[p_idx] if latencies else 0
                breach, status = self.calculator.check_slo_status(
                    p_latency, target.target_value, target.target_type
                )
                results.append(SLIResult(
                    name=target_name,
                    sli_value=p_latency,
                    target=target.target_value,
                    status=status,
                    timestamp=datetime.now(timezone.utc),
                    breach=breach
                ))
            elif target_name == "latency_p99":
                p_idx = int(len(latencies) * 0.99) if latencies else 0
                p_latency = latencies[p_idx] if latencies else 0
                breach, status = self.calculator.check_slo_status(
                    p_latency, target.target_value, target.target_type
                )
                results.append(SLIResult(
                    name=target_name,
                    sli_value=p_latency,
                    target=target.target_value,
                    status=status,
                    timestamp=datetime.now(timezone.utc),
                    breach=breach
                ))
            elif target_name == "error_rate":
                error_rate = failed_requests / total_requests if total_requests > 0 else 0
                breach, status = self.calculator.check_slo_status(
                    error_rate, target.target_value, target.target_type
                )
                results.append(SLIResult(
                    name=target_name,
                    sli_value=error_rate,
                    target=target.target_value,
                    status=status,
                    timestamp=datetime.now(timezone.utc),
                    breach=breach
                ))
            elif target_name == "throughput":
                breach, status = self.calculator.check_slo_status(
                    throughput, target.target_value, target.target_type
                )
                results.append(SLIResult(
                    name=target_name,
                    sli_value=throughput,
                    target=target.target_value,
                    status=status,
                    timestamp=datetime.now(timezone.utc),
                    breach=breach
                ))

        return results

    async def generate_report(
        self,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None
    ) -> SLOReport:
        if period_start is None:
            period_start = datetime.now(timezone.utc) - timedelta(days=30)
        if period_end is None:
            period_end = datetime.now(timezone.utc)

        sli_results = await self.get_sli_results(period_start, period_end)

        error_budgets = {}
        for target_name, target in self.calculator.slo_targets.items():
            budget_size = target.window_seconds * (1 - target.target_value)
            if target.target_type == "error_rate":
                budget_size = target.window_seconds * target.target_value
            elif target.target_type == "throughput":
                budget_size = target.target_value

            result = next((r for r in sli_results if r.name == target_name), None)
            current_value = result.sli_value if result else (0 if target.target_type == "throughput" else 1.0)

            error_budget = self.calculator.calculate_error_budget(
                budget_size, current_value, target.target_type
            )
            error_budgets[target_name] = error_budget

        breached_count = sum(1 for r in sli_results if r.breach)
        warning_count = sum(1 for r in sli_results if r.status == "warning")
        
        if breached_count > 0:
            overall_status = "breached"
        elif warning_count > 0:
            overall_status = "warning"
        else:
            overall_status = "healthy"

        return SLOReport(
            generated_at=datetime.now(timezone.utc),
            period_start=period_start,
            period_end=period_end,
            sli_results=sli_results,
            error_budgets=error_budgets,
            overall_status=overall_status
        )

    def get_alerts(self, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        if since is None:
            since = datetime.now(timezone.utc) - timedelta(hours=1)
        return [
            alert for alert in self.alerts
            if alert["timestamp"] >= since
        ]

    def clear_alerts(self):
        self.alerts = []

    def get_logs(self, since: Optional[datetime] = None, level: Optional[str] = None, limit: int = 100) -> List[LogEntry]:
        filtered = self.log_entries
        if since:
            filtered = [l for l in filtered if l.timestamp >= since]
        if level:
            filtered = [l for l in filtered if l.level.lower() == level.lower()]
        return filtered[-limit:]

    def get_recent_logs(self, minutes: int = 10) -> List[LogEntry]:
        since = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        return self.get_logs(since=since)

    def get_log_summary(self, hours: int = 24) -> Dict[str, Any]:
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        filtered = [l for l in self.log_entries if l.timestamp >= since]
        
        level_counts = defaultdict(int)
        endpoint_counts = defaultdict(int)
        status_counts = defaultdict(int)
        
        for entry in filtered:
            level_counts[entry.level] += 1
            if entry.endpoint:
                endpoint_counts[entry.endpoint] += 1
            if entry.status_code:
                status_counts[entry.status_code] += 1
        
        return {
            "total_entries": len(filtered),
            "level_counts": dict(level_counts),
            "endpoint_counts": dict(sorted(endpoint_counts.items(), key=lambda x: -x[1])[:10]),
            "status_counts": dict(status_counts),
            "period_hours": hours
        }

    def get_system_metrics(self, names: Optional[List[str]] = None) -> List[SystemMetric]:
        if names:
            return [m for m in self.system_metrics if m.name in names]
        return self.system_metrics

    def get_metric_summary(self) -> Dict[str, Any]:
        all_requests = []
        for metrics in self.metrics_store.values():
            all_requests.extend(metrics)
        
        if not all_requests:
            return {
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "error_rate": 0,
                "avg_latency_ms": 0,
                "p50_latency_ms": 0,
                "p99_latency_ms": 0,
                "throughput_rps": 0
            }
        
        total_requests = len(all_requests)
        failed_requests = sum(1 for r in all_requests if not r["success"])
        error_rate = failed_requests / total_requests
        latencies = sorted([r["latency_ms"] for r in all_requests])
        
        p50_idx = int(len(latencies) * 0.50)
        p99_idx = int(len(latencies) * 0.99)
        
        timestamps = [r["timestamp"] for r in all_requests]
        if timestamps:
            duration = (max(timestamps) - min(timestamps)).total_seconds() or 1
            throughput = total_requests / duration
        else:
            throughput = 0
        
        return {
            "total_requests": total_requests,
            "successful_requests": total_requests - failed_requests,
            "failed_requests": failed_requests,
            "error_rate": round(error_rate, 4),
            "avg_latency_ms": round(sum(latencies) / len(latencies), 2),
            "p50_latency_ms": latencies[p50_idx] if latencies else 0,
            "p99_latency_ms": latencies[p99_idx] if latencies else 0,
            "throughput_rps": round(throughput, 2)
        }

    def get_endpoint_metrics(self, limit: int = 10) -> List[Dict[str, Any]]:
        endpoint_stats = []
        
        for endpoint, metrics in self.metrics_store.items():
            if not metrics:
                continue
            
            total = len(metrics)
            failed = sum(1 for m in metrics if not m["success"])
            avg_latency = sum(m["latency_ms"] for m in metrics) / total
            latencies = sorted([m["latency_ms"] for m in metrics])
            p99_idx = int(len(latencies) * 0.99)
            
            endpoint_stats.append({
                "endpoint": endpoint,
                "total_requests": total,
                "failed_requests": failed,
                "success_rate": round((total - failed) / total, 4),
                "avg_latency_ms": round(avg_latency, 2),
                "p99_latency_ms": latencies[p99_idx] if latencies else 0
            })
        
        return sorted(endpoint_stats, key=lambda x: -x["total_requests"])[:limit]


calculator = SLOCalculator()
slo_monitor = SLOMonitor(calculator)
