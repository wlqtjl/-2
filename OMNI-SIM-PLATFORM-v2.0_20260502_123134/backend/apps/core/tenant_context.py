from contextvars import ContextVar
from typing import Optional

current_tenant_id: ContextVar[Optional[int]] = ContextVar("current_tenant_id", default=None)
current_tenant_slug: ContextVar[Optional[str]] = ContextVar("current_tenant_slug", default=None)


def get_current_tenant_id() -> Optional[int]:
    """获取当前请求的租户ID"""
    return current_tenant_id.get()


def get_current_tenant_slug() -> Optional[str]:
    """获取当前请求的租户slug"""
    return current_tenant_slug.get()


def set_current_tenant(tenant_id: int, tenant_slug: str):
    """设置当前请求的租户上下文"""
    current_tenant_id.set(tenant_id)
    current_tenant_slug.set(tenant_slug)


def clear_current_tenant():
    """清除当前租户上下文"""
    current_tenant_id.set(None)
    current_tenant_slug.set(None)


class TenantContext:
    """租户上下文管理器"""
    
    def __init__(self, tenant_id: int, tenant_slug: str):
        self.tenant_id = tenant_id
        self.tenant_slug = tenant_slug
        self.token_id = None
        self.token_slug = None
    
    def __enter__(self):
        self.token_id = current_tenant_id.set(self.tenant_id)
        self.token_slug = current_tenant_slug.set(self.tenant_slug)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        current_tenant_id.reset(self.token_id)
        current_tenant_slug.reset(self.token_slug)