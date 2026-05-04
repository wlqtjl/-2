from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2AuthorizationCodeBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from apps.core.config import settings
from apps.core.models import User, Tenant
from apps.core.database import SessionLocal
from apps.core.security import create_access_token, get_password_hash
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from urllib.parse import urlencode
import httpx
import logging
import secrets

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/oauth", tags=["OAuth/SSO"])

# 不同环境下可信的 redirect_uri 白名单，避免开放重定向
ALLOWED_REDIRECT_URIS = {
    settings.OAUTH_REDIRECT_URI,
}

# 在进程内低依赖保存 state（生产应走 Redis/Cookie）
_OAUTH_STATE_STORE: Dict[str, float] = {}
_STATE_TTL_SECONDS = 600


def _issue_state() -> str:
    state = secrets.token_urlsafe(32)
    _OAUTH_STATE_STORE[state] = datetime.now(timezone.utc).timestamp()
    # 偷懒清理过期 state
    cutoff = datetime.now(timezone.utc).timestamp() - _STATE_TTL_SECONDS
    for k in list(_OAUTH_STATE_STORE.keys()):
        if _OAUTH_STATE_STORE[k] < cutoff:
            _OAUTH_STATE_STORE.pop(k, None)
    return state


def _consume_state(state: Optional[str]) -> bool:
    if not state:
        return False
    issued = _OAUTH_STATE_STORE.pop(state, None)
    if issued is None:
        return False
    return (datetime.now(timezone.utc).timestamp() - issued) <= _STATE_TTL_SECONDS


# OAuth配置
OAUTH_PROVIDERS = {
    "google": {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": "https://www.googleapis.com/oauth2/v3/userinfo",
        "scope": "openid email profile"
    },
    "github": {
        "client_id": settings.GITHUB_CLIENT_ID,
        "client_secret": settings.GITHUB_CLIENT_SECRET,
        "authorize_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "userinfo_url": "https://api.github.com/user",
        "scope": "user:email"
    },
    "azure": {
        "client_id": settings.AZURE_CLIENT_ID,
        "client_secret": settings.AZURE_CLIENT_SECRET,
        "authorize_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        "token_url": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
        "userinfo_url": "https://graph.microsoft.com/v1.0/me",
        "scope": "openid email profile"
    }
}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    refresh_token: Optional[str] = None
    expires_in: int


class OAuthUser(BaseModel):
    email: str
    name: str
    provider: str
    provider_id: str


async def get_oauth_user(provider: str, code: str, redirect_uri: str) -> OAuthUser:
    """获取OAuth用户信息"""
    provider_config = OAUTH_PROVIDERS.get(provider)
    if not provider_config:
        raise HTTPException(status_code=400, detail="不支持的OAuth提供商")
    
    if not provider_config["client_id"] or not provider_config["client_secret"]:
        raise HTTPException(status_code=500, detail="OAuth提供商未配置")
    
    # 获取token
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            provider_config["token_url"],
            data={
                "client_id": provider_config["client_id"],
                "client_secret": provider_config["client_secret"],
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if token_response.status_code != 200:
            raise HTTPException(status_code=400, detail="获取token失败")
        
        token_data = token_response.json()
        access_token = token_data.get("access_token")
        
        # 获取用户信息
        userinfo_response = await client.get(
            provider_config["userinfo_url"],
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        if userinfo_response.status_code != 200:
            raise HTTPException(status_code=400, detail="获取用户信息失败")
        
        userinfo = userinfo_response.json()
        
        # 根据provider解析用户信息
        if provider == "google":
            return OAuthUser(
                email=userinfo.get("email"),
                name=userinfo.get("name"),
                provider="google",
                provider_id=str(userinfo.get("sub"))
            )
        elif provider == "github":
            email = userinfo.get("email")
            if not email:
                emails_response = await client.get(
                    "https://api.github.com/user/emails",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                emails = emails_response.json()
                primary_email = next((e for e in emails if e.get("primary")), None)
                email = primary_email.get("email") if primary_email else None
            
            return OAuthUser(
                email=email,
                name=userinfo.get("name") or userinfo.get("login"),
                provider="github",
                provider_id=str(userinfo.get("id"))
            )
        elif provider == "azure":
            return OAuthUser(
                email=userinfo.get("mail") or userinfo.get("userPrincipalName"),
                name=userinfo.get("displayName"),
                provider="azure",
                provider_id=str(userinfo.get("id"))
            )
    
    raise HTTPException(status_code=400, detail="无法解析用户信息")


@router.get("/{provider}/authorize")
async def get_oauth_authorize_url(provider: str):
    """获取OAuth授权URL"""
    provider_config = OAUTH_PROVIDERS.get(provider)
    if not provider_config:
        raise HTTPException(status_code=400, detail="不支持的OAuth提供商")

    if not provider_config["client_id"]:
        raise HTTPException(status_code=500, detail="OAuth提供商未配置")

    state = _issue_state()
    params = {
        "client_id": provider_config["client_id"],
        "redirect_uri": settings.OAUTH_REDIRECT_URI,
        "response_type": "code",
        "scope": provider_config["scope"],
        "state": state,
    }
    authorize_url = f"{provider_config['authorize_url']}?{urlencode(params)}"

    return {"authorize_url": authorize_url, "state": state}


@router.post("/{provider}/callback")
async def oauth_callback(
    provider: str,
    code: str,
    state: Optional[str] = None,
    redirect_uri: str = settings.OAUTH_REDIRECT_URI,
):
    """OAuth回调处理"""
    if redirect_uri not in ALLOWED_REDIRECT_URIS:
        raise HTTPException(status_code=400, detail="redirect_uri 不在允许名单内")
    if not _consume_state(state):
        raise HTTPException(status_code=400, detail="无效或过期的 state参数")

    db = SessionLocal()

    try:
        # 获取OAuth用户信息
        oauth_user = await get_oauth_user(provider, code, redirect_uri)

        if not oauth_user.email:
            raise HTTPException(status_code=400, detail="无法获取用户邮箱")

        # 查找或创建用户
        user = db.query(User).filter(User.email == oauth_user.email).first()

        if user:
            # 仅在账号原本没有姓名时补充，避免覆盖用户资料
            if not user.full_name and oauth_user.name:
                user.full_name = oauth_user.name
                db.commit()
                db.refresh(user)
        else:
            # 创建新用户（默认角色为学员）
            default_tenant = db.query(Tenant).filter(Tenant.slug == "default").first()
            if not default_tenant:
                default_tenant = Tenant(name="默认租户", slug="default")
                db.add(default_tenant)
                db.commit()
                db.refresh(default_tenant)

            random_password = secrets.token_urlsafe(32)
            user = User(
                email=oauth_user.email,
                full_name=oauth_user.name,
                hashed_password=get_password_hash(random_password),
                role="learner",
                is_active=True,
                tenant_id=default_tenant.id,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        
        # 创建访问令牌
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.email, "user_id": user.id},
            expires_delta=access_token_expires
        )
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
    
    finally:
        db.close()


@router.get("/providers")
async def get_oauth_providers():
    """获取可用的OAuth提供商列表"""
    providers = []
    for name, config in OAUTH_PROVIDERS.items():
        if config["client_id"]:
            providers.append({
                "name": name,
                "display_name": {
                    "google": "Google",
                    "github": "GitHub",
                    "azure": "Azure AD"
                }.get(name, name.capitalize())
            })
    
    return {"providers": providers}