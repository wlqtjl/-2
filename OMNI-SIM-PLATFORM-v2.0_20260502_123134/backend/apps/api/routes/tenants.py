from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from datetime import datetime
from apps.core.models import Tenant, User, Course
from apps.core.database import SessionLocal
from apps.api.deps import get_current_user
from pydantic import BaseModel, field_validator
import re

router = APIRouter(prefix="/tenants", tags=["租户管理"])


class TenantResponse(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str]
    user_count: int
    course_count: int
    created_at: datetime
    updated_at: Optional[datetime]


class TenantCreate(BaseModel):
    name: str
    slug: Optional[str] = None
    description: Optional[str] = None

    @field_validator('name')
    def name_required(cls, v):
        if not v or not v.strip():
            raise ValueError('租户名称不能为空')
        return v

    @field_validator('slug')
    def slug_valid(cls, v):
        if v and not re.match(r'^[a-z0-9-]+$', v):
            raise ValueError('slug只能包含小写字母、数字和连字符')
        return v


class TenantUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class TenantListResponse(BaseModel):
    tenants: List[TenantResponse]
    total: int
    page: int
    page_size: int


def require_super_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="需要超级管理员权限")
    return current_user


@router.get("", response_model=TenantListResponse)
async def get_tenants(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    current_user: User = Depends(require_super_admin)
):
    """获取租户列表"""
    db = SessionLocal()
    try:
        query = db.query(Tenant)

        if search:
            query = query.filter(
                (Tenant.name.contains(search)) |
                (Tenant.slug.contains(search))
            )

        total = query.count()
        tenants = query.order_by(Tenant.created_at.desc())\
            .offset((page - 1) * page_size)\
            .limit(page_size)\
            .all()

        result = []
        for tenant in tenants:
            user_count = db.query(User).filter(User.tenant_id == tenant.id).count()
            course_count = db.query(Course).filter(Course.tenant_id == tenant.id).count()
            result.append(TenantResponse(
                id=tenant.id,
                name=tenant.name,
                slug=tenant.slug,
                description=tenant.description,
                user_count=user_count,
                course_count=course_count,
                created_at=tenant.created_at,
                updated_at=tenant.updated_at
            ))

        return TenantListResponse(
            tenants=result,
            total=total,
            page=page,
            page_size=page_size
        )
    finally:
        db.close()


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: int,
    current_user: User = Depends(require_super_admin)
):
    """获取租户详情"""
    db = SessionLocal()
    try:
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="租户不存在")

        user_count = db.query(User).filter(User.tenant_id == tenant.id).count()
        course_count = db.query(Course).filter(Course.tenant_id == tenant.id).count()

        return TenantResponse(
            id=tenant.id,
            name=tenant.name,
            slug=tenant.slug,
            description=tenant.description,
            user_count=user_count,
            course_count=course_count,
            created_at=tenant.created_at,
            updated_at=tenant.updated_at
        )
    finally:
        db.close()


@router.post("", response_model=TenantResponse)
async def create_tenant(
    tenant_create: TenantCreate,
    current_user: User = Depends(require_super_admin)
):
    """创建租户"""
    db = SessionLocal()
    try:
        slug = tenant_create.slug or tenant_create.name.lower().replace(' ', '-').replace('_', '-')
        slug = re.sub(r'[^a-z0-9-]', '', slug)
        
        existing = db.query(Tenant).filter((Tenant.name == tenant_create.name) | (Tenant.slug == slug)).first()
        if existing:
            raise HTTPException(status_code=400, detail="租户名称或slug已存在")

        tenant = Tenant(
            name=tenant_create.name,
            slug=slug,
            description=tenant_create.description
        )
        db.add(tenant)
        db.commit()
        db.refresh(tenant)

        return TenantResponse(
            id=tenant.id,
            name=tenant.name,
            slug=tenant.slug,
            description=tenant.description,
            user_count=0,
            course_count=0,
            created_at=tenant.created_at,
            updated_at=tenant.updated_at
        )
    finally:
        db.close()


@router.put("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: int,
    tenant_update: TenantUpdate,
    current_user: User = Depends(require_super_admin)
):
    """更新租户信息"""
    db = SessionLocal()
    try:
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="租户不存在")

        if tenant_update.name:
            existing = db.query(Tenant).filter(
                Tenant.name == tenant_update.name,
                Tenant.id != tenant_id
            ).first()
            if existing:
                raise HTTPException(status_code=400, detail="租户名称已存在")
            tenant.name = tenant_update.name

        if tenant_update.description is not None:
            tenant.description = tenant_update.description

        db.commit()
        db.refresh(tenant)

        user_count = db.query(User).filter(User.tenant_id == tenant.id).count()
        course_count = db.query(Course).filter(Course.tenant_id == tenant.id).count()

        return TenantResponse(
            id=tenant.id,
            name=tenant.name,
            slug=tenant.slug,
            description=tenant.description,
            user_count=user_count,
            course_count=course_count,
            created_at=tenant.created_at,
            updated_at=tenant.updated_at
        )
    finally:
        db.close()


@router.delete("/{tenant_id}")
async def delete_tenant(
    tenant_id: int,
    current_user: User = Depends(require_super_admin)
):
    """删除租户"""
    db = SessionLocal()
    try:
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="租户不存在")

        if tenant.slug == "default":
            raise HTTPException(status_code=400, detail="不能删除默认租户")

        db.query(Course).filter(Course.tenant_id == tenant_id).delete()
        db.query(User).filter(User.tenant_id == tenant_id).delete()
        db.delete(tenant)
        db.commit()

        return {"success": True, "message": "租户删除成功"}
    finally:
        db.close()


@router.get("/{tenant_id}/users")
async def get_tenant_users(
    tenant_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_super_admin)
):
    """获取租户下的用户列表"""
    db = SessionLocal()
    try:
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="租户不存在")

        query = db.query(User).filter(User.tenant_id == tenant_id)
        total = query.count()
        users = query.order_by(User.created_at.desc())\
            .offset((page - 1) * page_size)\
            .limit(page_size)\
            .all()

        return {
            "users": [
                {
                    "id": u.id,
                    "email": u.email,
                    "full_name": u.full_name,
                    "role": u.role,
                    "is_active": u.is_active,
                    "created_at": u.created_at
                }
                for u in users
            ],
            "total": total,
            "page": page,
            "page_size": page_size
        }
    finally:
        db.close()


@router.post("/{tenant_id}/users")
async def add_user_to_tenant(
    tenant_id: int,
    user_id: int,
    current_user: User = Depends(require_super_admin)
):
    """将用户添加到租户"""
    db = SessionLocal()
    try:
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="租户不存在")

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")

        user.tenant_id = tenant_id
        db.commit()

        return {"success": True, "message": "用户已添加到租户"}
    finally:
        db.close()


@router.delete("/{tenant_id}/users/{user_id}")
async def remove_user_from_tenant(
    tenant_id: int,
    user_id: int,
    current_user: User = Depends(require_super_admin)
):
    """将用户从租户移除"""
    db = SessionLocal()
    try:
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="租户不存在")

        user = db.query(User).filter(User.id == user_id, User.tenant_id == tenant_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="用户不在该租户中")

        default_tenant = db.query(Tenant).filter(Tenant.slug == "default").first()
        if not default_tenant:
            default_tenant = Tenant(name="默认租户", slug="default")
            db.add(default_tenant)
            db.commit()
            db.refresh(default_tenant)

        user.tenant_id = default_tenant.id
        db.commit()

        return {"success": True, "message": "用户已从租户移除"}
    finally:
        db.close()