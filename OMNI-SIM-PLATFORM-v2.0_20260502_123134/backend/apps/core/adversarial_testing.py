import random
import string
import asyncio
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta, timezone
from enum import Enum
from pydantic import BaseModel
from apps.core.config import settings
import logging

logger = logging.getLogger(__name__)


class AttackType(str, Enum):
    """攻击类型"""
    SQL_INJECTION = "sql_injection"
    XSS = "xss"
    CSRF = "csrf"
    RATE_LIMIT = "rate_limit"
    INPUT_VALIDATION = "input_validation"
    AUTH_BYPASS = "auth_bypass"
    DATA_CORRUPTION = "data_corruption"
    API_FUZZING = "api_fuzzing"


class AttackSeverity(str, Enum):
    """攻击严重程度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AttackResult(BaseModel):
    """攻击测试结果"""
    attack_type: AttackType
    severity: AttackSeverity
    success: bool
    payload: str
    response_code: int
    response_time: float
    vulnerability_found: bool
    description: str
    timestamp: datetime = datetime.now(timezone.utc)


class TestReport(BaseModel):
    """测试报告"""
    test_id: str
    start_time: datetime
    end_time: datetime
    total_attacks: int
    successful_attacks: int
    vulnerabilities_found: int
    results: List[AttackResult]
    summary: Dict[str, Any]


class AdversarialTester:
    """对抗性测试器"""
    
    def __init__(self):
        self.payloads = self._load_payloads()
        self.test_results: List[TestReport] = []
    
    def _load_payloads(self) -> Dict[AttackType, List[str]]:
        """加载攻击载荷"""
        return {
            AttackType.SQL_INJECTION: [
                "' OR '1'='1",
                "' OR 1=1--",
                "' UNION SELECT NULL,USER(),NULL--",
                "'); DROP TABLE users--",
                "' AND SLEEP(5)--",
                "1'; EXEC sp_helpdb--"
            ],
            AttackType.XSS: [
                "<script>alert('XSS')</script>",
                "<img src=x onerror=alert(1)>",
                "<svg/onload=alert(1)>",
                "\" onmouseover=\"alert(1)",
                "<iframe src=javascript:alert(1)>",
                "<body onload=alert(1)>"
            ],
            AttackType.INPUT_VALIDATION: [
                "",
                " " * 1000,
                "a" * 10000,
                "{" + "a" * 100 + "}",
                "<>" * 500,
                "\x00" * 100,
                "\x7f" * 100
            ],
            AttackType.API_FUZZING: [
                "NaN",
                "Infinity",
                "-Infinity",
                "null",
                "undefined",
                "true",
                "false",
                "[object Object]",
                "Array(10000).join('x')",
                "%20",
                "%00",
                "%0d%0a"
            ]
        }
    
    def generate_random_string(self, length: int = 10) -> str:
        """生成随机字符串"""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
    
    def generate_random_email(self) -> str:
        """生成随机邮箱"""
        return f"{self.generate_random_string(8)}@{self.generate_random_string(5)}.com"
    
    def generate_random_payload(self, attack_type: AttackType) -> str:
        """生成随机攻击载荷"""
        if attack_type in self.payloads:
            return random.choice(self.payloads[attack_type])
        return self.generate_random_string(50)
    
    async def test_sql_injection(
        self,
        target_func: Callable,
        input_field: str = "email"
    ) -> AttackResult:
        """测试SQL注入"""
        payload = self.generate_random_payload(AttackType.SQL_INJECTION)
        try:
            start_time = datetime.now()
            result = await target_func({input_field: payload})
            response_time = (datetime.now() - start_time).total_seconds()
            
            # 检查是否存在SQL注入漏洞
            vulnerability_found = False
            if isinstance(result, dict):
                if 'error' in result and ('SQL' in result['error'] or 'database' in result['error'].lower()):
                    vulnerability_found = True
            
            return AttackResult(
                attack_type=AttackType.SQL_INJECTION,
                severity=AttackSeverity.HIGH,
                success=True,
                payload=payload,
                response_code=200,
                response_time=response_time,
                vulnerability_found=vulnerability_found,
                description="SQL注入测试"
            )
        except Exception as e:
            return AttackResult(
                attack_type=AttackType.SQL_INJECTION,
                severity=AttackSeverity.HIGH,
                success=False,
                payload=payload,
                response_code=500,
                response_time=0,
                vulnerability_found=True,
                description=f"SQL注入测试失败: {str(e)}"
            )
    
    async def test_xss(
        self,
        target_func: Callable,
        input_field: str = "content"
    ) -> AttackResult:
        """测试XSS攻击"""
        payload = self.generate_random_payload(AttackType.XSS)
        try:
            start_time = datetime.now()
            result = await target_func({input_field: payload})
            response_time = (datetime.now() - start_time).total_seconds()
            
            # 检查响应中是否包含原始脚本（表示XSS漏洞存在）
            vulnerability_found = False
            if isinstance(result, dict) and 'message' in result:
                if '<script>' in result['message'] or 'onerror=' in result['message']:
                    vulnerability_found = True
            
            return AttackResult(
                attack_type=AttackType.XSS,
                severity=AttackSeverity.HIGH,
                success=True,
                payload=payload,
                response_code=200,
                response_time=response_time,
                vulnerability_found=vulnerability_found,
                description="XSS攻击测试"
            )
        except Exception as e:
            return AttackResult(
                attack_type=AttackType.XSS,
                severity=AttackSeverity.HIGH,
                success=False,
                payload=payload,
                response_code=500,
                response_time=0,
                vulnerability_found=False,
                description=f"XSS测试失败: {str(e)}"
            )
    
    async def test_input_validation(
        self,
        target_func: Callable,
        input_field: str = "input"
    ) -> AttackResult:
        """测试输入验证"""
        payload = self.generate_random_payload(AttackType.INPUT_VALIDATION)
        try:
            start_time = datetime.now()
            result = await target_func({input_field: payload})
            response_time = (datetime.now() - start_time).total_seconds()
            
            # 检查是否正确处理异常输入
            vulnerability_found = response_time > 3  # 响应时间过长可能表示DoS风险
            
            return AttackResult(
                attack_type=AttackType.INPUT_VALIDATION,
                severity=AttackSeverity.MEDIUM,
                success=True,
                payload=f"{payload[:20]}...",
                response_code=200,
                response_time=response_time,
                vulnerability_found=vulnerability_found,
                description="输入验证测试"
            )
        except Exception as e:
            return AttackResult(
                attack_type=AttackType.INPUT_VALIDATION,
                severity=AttackSeverity.MEDIUM,
                success=False,
                payload=f"{payload[:20]}...",
                response_code=500,
                response_time=0,
                vulnerability_found=False,
                description=f"输入验证测试失败: {str(e)}"
            )
    
    async def test_api_fuzzing(
        self,
        target_func: Callable,
        input_field: str = "data"
    ) -> AttackResult:
        """测试API模糊测试"""
        payload = self.generate_random_payload(AttackType.API_FUZZING)
        try:
            start_time = datetime.now()
            result = await target_func({input_field: payload})
            response_time = (datetime.now() - start_time).total_seconds()
            
            # 检查是否正确处理异常输入
            vulnerability_found = False
            if isinstance(result, dict) and 'error' in result:
                if 'Internal Server Error' in result['error']:
                    vulnerability_found = True
            
            return AttackResult(
                attack_type=AttackType.API_FUZZING,
                severity=AttackSeverity.MEDIUM,
                success=True,
                payload=payload,
                response_code=200,
                response_time=response_time,
                vulnerability_found=vulnerability_found,
                description="API模糊测试"
            )
        except Exception as e:
            return AttackResult(
                attack_type=AttackType.API_FUZZING,
                severity=AttackSeverity.MEDIUM,
                success=False,
                payload=payload,
                response_code=500,
                response_time=0,
                vulnerability_found=True,
                description=f"API模糊测试失败: {str(e)}"
            )
    
    async def run_test_suite(
        self,
        target_funcs: Dict[AttackType, Callable],
        test_count: int = 5
    ) -> TestReport:
        """运行测试套件"""
        test_id = f"test-{datetime.now().timestamp()}"
        start_time = datetime.now()
        results: List[AttackResult] = []
        
        for attack_type, target_func in target_funcs.items():
            for _ in range(test_count):
                if attack_type == AttackType.SQL_INJECTION:
                    result = await self.test_sql_injection(target_func)
                elif attack_type == AttackType.XSS:
                    result = await self.test_xss(target_func)
                elif attack_type == AttackType.INPUT_VALIDATION:
                    result = await self.test_input_validation(target_func)
                elif attack_type == AttackType.API_FUZZING:
                    result = await self.test_api_fuzzing(target_func)
                else:
                    continue
                
                results.append(result)
        
        end_time = datetime.now()
        
        # 生成总结
        summary = {
            "total_attacks": len(results),
            "successful_attacks": sum(1 for r in results if r.success),
            "vulnerabilities_found": sum(1 for r in results if r.vulnerability_found),
            "avg_response_time": sum(r.response_time for r in results) / len(results),
            "by_severity": {
                "critical": sum(1 for r in results if r.severity == AttackSeverity.CRITICAL),
                "high": sum(1 for r in results if r.severity == AttackSeverity.HIGH),
                "medium": sum(1 for r in results if r.severity == AttackSeverity.MEDIUM),
                "low": sum(1 for r in results if r.severity == AttackSeverity.LOW)
            }
        }
        
        report = TestReport(
            test_id=test_id,
            start_time=start_time,
            end_time=end_time,
            total_attacks=len(results),
            successful_attacks=summary["successful_attacks"],
            vulnerabilities_found=summary["vulnerabilities_found"],
            results=results,
            summary=summary
        )
        
        self.test_results.append(report)
        
        # 记录日志
        logger.info(f"对抗性测试完成: {test_id}, 发现漏洞: {summary['vulnerabilities_found']}")
        
        return report


# 全局实例
adversarial_tester = AdversarialTester()


# API路由
from fastapi import APIRouter, HTTPException, Depends
from apps.api.deps import require_admin_role

router = APIRouter(prefix="/security", tags=["安全测试"])


@router.post("/test/run")
async def run_security_tests(
    test_types: List[str] = None,
    test_count: int = 5,
    current_user = Depends(require_admin_role)
):
    """运行安全测试"""
    # 构建目标函数映射（这里使用示例函数）
    async def sample_func(data: Dict[str, Any]) -> Dict[str, Any]:
        """示例目标函数"""
        return {"message": "OK", "data": data}
    
    target_funcs: Dict[AttackType, Callable] = {}
    
    if not test_types:
        test_types = ["sql_injection", "xss", "input_validation", "api_fuzzing"]
    
    if "sql_injection" in test_types:
        target_funcs[AttackType.SQL_INJECTION] = sample_func
    if "xss" in test_types:
        target_funcs[AttackType.XSS] = sample_func
    if "input_validation" in test_types:
        target_funcs[AttackType.INPUT_VALIDATION] = sample_func
    if "api_fuzzing" in test_types:
        target_funcs[AttackType.API_FUZZING] = sample_func
    
    report = await adversarial_tester.run_test_suite(target_funcs, test_count)
    return {"success": True, "report": report.dict()}


@router.get("/test/reports")
async def get_test_reports(
    limit: int = 10,
    current_user = Depends(require_admin_role)
):
    """获取测试报告列表"""
    reports = adversarial_tester.test_results[-limit:]
    return {"reports": [r.dict() for r in reports]}


@router.get("/test/reports/{test_id}")
async def get_test_report(
    test_id: str,
    current_user = Depends(require_admin_role)
):
    """获取单个测试报告"""
    report = next((r for r in adversarial_tester.test_results if r.test_id == test_id), None)
    if not report:
        raise HTTPException(status_code=404, detail="测试报告不存在")
    return {"report": report.dict()}


@router.get("/health")
async def security_health_check():
    """安全模块健康检查"""
    return {"status": "healthy", "module": "adversarial-testing"}