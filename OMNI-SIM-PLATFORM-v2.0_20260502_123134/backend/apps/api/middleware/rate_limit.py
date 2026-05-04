"""轻量进程内速率限制中间件。

仅用于保护未认证端点（登录 / 注册）抵御暴力破解和注册轰炸。
生产部署若有多副本，应替换为 Redis-backed slowapi。
"""
from __future__ import annotations

import time
from collections import deque
from typing import Deque, Dict, Tuple

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.requests import Request


class AuthRateLimitMiddleware(BaseHTTPMiddleware):
    """对登录/注册按客户端 IP 限速。

    默认：每个 IP 每 60 秒最多 10 次请求。超过返回 429。
    """

    PROTECTED_PATHS: Tuple[str, ...] = ("/auth/token", "/auth/register")

    def __init__(self, app, max_requests: int = 10, window_seconds: int = 60) -> None:
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._buckets: Dict[str, Deque[float]] = {}

    def _client_key(self, request: Request) -> str:
        # 优先 X-Forwarded-For 第一段（仅当反向代理已被信任设置）
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        client = request.client
        return client.host if client else "unknown"

    def _is_protected(self, path: str) -> bool:
        return any(path.endswith(p) for p in self.PROTECTED_PATHS)

    async def dispatch(self, request: Request, call_next):
        if request.method not in ("POST", "PUT") or not self._is_protected(request.url.path):
            return await call_next(request)

        now = time.monotonic()
        key = f"{self._client_key(request)}|{request.url.path}"
        bucket = self._buckets.setdefault(key, deque())

        # 丢弃过期条目
        while bucket and (now - bucket[0]) > self.window_seconds:
            bucket.popleft()

        if len(bucket) >= self.max_requests:
            retry_after = int(self.window_seconds - (now - bucket[0])) + 1
            return JSONResponse(
                status_code=429,
                content={
                    "code": "RATE_LIMITED",
                    "message": "请求过于频繁，请稍后再试",
                },
                headers={"Retry-After": str(max(1, retry_after))},
            )

        bucket.append(now)
        return await call_next(request)
