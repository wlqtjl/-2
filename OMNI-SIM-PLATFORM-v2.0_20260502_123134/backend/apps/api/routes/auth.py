from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from apps.core import security, database, config
from apps.core.models import User, Tenant
from apps.api.deps import get_current_active_user
from schemas.user import UserCreate, UserResponse, Token

router = APIRouter(prefix="/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")


@router.get("/me", response_model=UserResponse)
def read_me(current_user: User = Depends(get_current_active_user)):
    """返回当前登录用户的完整信息（取代前端解析 JWT）"""
    return current_user


@router.post("/token", response_model=Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(database.get_db)
):
    user = security.get_user(db, email=form_data.username)

    # 统一证据错误响应以避免账号枚举
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_CREDENTIALS", "message": "邮箱或密码错误"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "USER_INACTIVE", "message": "账户已被禁用，请联系管理员"},
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=config.settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.email, "role": user.role, "user_id": user.id}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/register", response_model=UserResponse)
def register_user(
    user_create: UserCreate,
    db: Session = Depends(database.get_db)
):
    errors = []
    
    if not user_create.email:
        errors.append({"field": "email", "message": "邮箱地址不能为空"})
    elif "@" not in user_create.email:
        errors.append({"field": "email", "message": "请输入有效的邮箱地址"})
    
    if not user_create.password:
        errors.append({"field": "password", "message": "密码不能为空"})
    elif len(user_create.password) < 6:
        errors.append({"field": "password", "message": "密码长度至少为6位"})
    
    if not user_create.full_name:
        errors.append({"field": "full_name", "message": "姓名不能为空"})
    
    if user_create.role and user_create.role != "learner":
        errors.append({"field": "role", "message": "注册仅允许 learner 角色"})
    
    if errors:
        raise HTTPException(
            status_code=400,
            detail={"code": "VALIDATION_ERROR", "message": "输入验证失败", "errors": errors}
        )
    
    db_user = security.get_user(db, email=user_create.email)
    if db_user:
        raise HTTPException(
            status_code=400,
            detail={"code": "EMAIL_EXISTS", "message": "该邮箱已被注册，请使用其他邮箱"}
        )
    
    default_tenant = db.query(Tenant).filter(Tenant.slug == "default").first()
    if not default_tenant:
        default_tenant = Tenant(name="默认租户", slug="default")
        db.add(default_tenant)
        db.commit()
        db.refresh(default_tenant)
    
    try:
        hashed_password = security.get_password_hash(user_create.password)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"code": "PASSWORD_HASH_ERROR", "message": "密码加密失败，请稍后重试"}
        )
    
    new_user = User(
        email=user_create.email,
        hashed_password=hashed_password,
        full_name=user_create.full_name,
        role="learner",
        tenant_id=default_tenant.id
    )
    
    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail={"code": "DATABASE_ERROR", "message": "数据库操作失败，请稍后重试"}
        )
    
    return new_user
