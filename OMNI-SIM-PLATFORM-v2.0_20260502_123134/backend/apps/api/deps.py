from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from apps.core import security, database, config, models, tenant_context

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token", auto_error=False)

async def get_current_user(
    db: Session = Depends(database.get_db),
    token: Optional[str] = Depends(oauth2_scheme)
) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception
    try:
        payload = jwt.decode(token, config.settings.SECRET_KEY, algorithms=[config.settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = security.get_user(db, email=email)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: models.User = Depends(get_current_user)) -> models.User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

def get_db_session() -> Session:
    return next(database.get_db())


def require_tenant_access(current_user: models.User = Depends(get_current_active_user)):
    """验证用户是否属于当前租户上下文"""
    current_tenant_id = tenant_context.get_current_tenant_id()
    if current_tenant_id and current_user.tenant_id != current_tenant_id:
        raise HTTPException(
            status_code=403,
            detail="您无权访问此租户的数据"
        )
    return current_user


def require_admin_or_instructor(current_user: models.User = Depends(get_current_active_user)):
    """验证用户是否为管理员或讲师（用于教学/内容管理类接口）"""
    if current_user.role not in ["admin", "instructor"]:
        raise HTTPException(
            status_code=403,
            detail="需要管理员或讲师权限"
        )
    return current_user


# 兼容旧接口名（已废弃，调用方应迁移至 require_admin_or_instructor 或 require_super_admin）
require_admin_role = require_admin_or_instructor


def require_admin(current_user: models.User = Depends(get_current_active_user)):
    """严格的管理员校验：仅 admin 角色可通过"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="需要管理员权限"
        )
    return current_user


def require_super_admin(current_user: models.User = Depends(get_current_active_user)):
    """验证用户是否为超级管理员"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="需要超级管理员权限"
        )
    return current_user
