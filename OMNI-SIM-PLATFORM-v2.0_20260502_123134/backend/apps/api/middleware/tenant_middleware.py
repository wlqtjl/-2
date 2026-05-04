from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from apps.core.database import SessionLocal
from apps.core.models import User, Tenant
from apps.core import tenant_context
from apps.core.security import decode_access_token
import logging

logger = logging.getLogger(__name__)


class TenantMiddleware(BaseHTTPMiddleware):
    """租户隔离中间件"""

    async def dispatch(self, request: Request, call_next):
        # 使用 contextvar 的 set/reset 方式，避免请求间相互污染
        token_id = tenant_context.current_tenant_id.set(None)
        token_slug = tenant_context.current_tenant_slug.set(None)

        bearer = None
        authorization = request.headers.get("Authorization")
        if authorization and authorization.startswith("Bearer "):
            bearer = authorization[7:]

        if bearer:
            try:
                payload = decode_access_token(bearer)
                if payload:
                    email = payload.get("sub")
                    if email:
                        db = SessionLocal()
                        try:
                            user = db.query(User).filter(User.email == email).first()
                            if user and user.tenant_id:
                                tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
                                if tenant:
                                    tenant_context.current_tenant_id.set(user.tenant_id)
                                    tenant_context.current_tenant_slug.set(tenant.slug)
                                    logger.debug(f"Set tenant context: {tenant.id} - {tenant.slug}")
                        finally:
                            db.close()
            except Exception as e:
                logger.warning(f"Failed to set tenant context: {str(e)}")

        try:
            response = await call_next(request)
        finally:
            tenant_context.current_tenant_id.reset(token_id)
            tenant_context.current_tenant_slug.reset(token_slug)
        return response
