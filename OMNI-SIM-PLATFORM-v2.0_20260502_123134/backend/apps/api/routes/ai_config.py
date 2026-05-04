from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from pathlib import Path
from apps.core.config import settings
from apps.core.models import User
from apps.api.deps import require_admin_or_instructor

router = APIRouter(prefix="/ai-config", tags=["AI配置"])

# .env 路径锚定到 backend/.env，与 config.py 一致，不依赖 cwd 或绝对硬编码
_BACKEND_DIR = Path(__file__).resolve().parents[3]
_ENV_FILE = _BACKEND_DIR / ".env"

# 仅允许写入这些已知键，避免 .env 被注入任意键
_ALLOWED_KEYS = {
    "CLAUDE_API_KEY",
    "QIANWEN_API_KEY",
    "DEEPSEEK_API_KEY",
    "DEFAULT_AI_MODEL",
}

class AIConfigResponse(BaseModel):
    claude_api_key_configured: bool
    qianwen_api_key_configured: bool
    deepseek_api_key_configured: bool
    default_model: str
    claude_model: str
    qianwen_model: str
    deepseek_model: str

class AIConfigUpdate(BaseModel):
    claude_api_key: str | None = None
    qianwen_api_key: str | None = None
    deepseek_api_key: str | None = None
    default_model: str | None = None


def _upsert_env(updates: dict[str, str]) -> None:
    """将 updates 写入 .env：已存在的键就替换，不存在就追加。仅允许白名单键。"""
    safe_updates = {k: v for k, v in updates.items() if k in _ALLOWED_KEYS}
    if not safe_updates:
        return
    # 校验值：禁止换行/控制字符注入
    for k, v in safe_updates.items():
        if any(ord(c) < 0x20 for c in v):
            raise HTTPException(status_code=400, detail=f"非法字符: {k}")

    lines: list[str] = []
    if _ENV_FILE.exists():
        lines = _ENV_FILE.read_text(encoding="utf-8").splitlines()

    seen: set[str] = set()
    new_lines: list[str] = []
    for line in lines:
        stripped = line.lstrip()
        if "=" in stripped and not stripped.startswith("#"):
            key = stripped.split("=", 1)[0].strip()
            if key in safe_updates:
                new_lines.append(f"{key}={safe_updates[key]}")
                seen.add(key)
                continue
        new_lines.append(line)
    for key, val in safe_updates.items():
        if key not in seen:
            new_lines.append(f"{key}={val}")

    _ENV_FILE.parent.mkdir(parents=True, exist_ok=True)
    _ENV_FILE.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


@router.get("/status", response_model=AIConfigResponse)
async def get_ai_config_status(_: User = Depends(require_admin_or_instructor)):
    return {
        "claude_api_key_configured": bool(settings.CLAUDE_API_KEY and settings.CLAUDE_API_KEY != "your-claude-api-key-here"),
        "qianwen_api_key_configured": bool(settings.QIANWEN_API_KEY and settings.QIANWEN_API_KEY != "your-qianwen-api-key-here"),
        "deepseek_api_key_configured": bool(settings.DEEPSEEK_API_KEY and settings.DEEPSEEK_API_KEY != "your-deepseek-api-key-here"),
        "default_model": settings.DEFAULT_AI_MODEL,
        "claude_model": settings.CLAUDE_MODEL,
        "qianwen_model": settings.QIANWEN_MODEL,
        "deepseek_model": settings.DEEPSEEK_MODEL,
    }

@router.post("/update")
async def update_ai_config(
    config: AIConfigUpdate,
    _: User = Depends(require_admin_or_instructor),
):
    updates: dict[str, str] = {}
    if config.claude_api_key is not None:
        updates["CLAUDE_API_KEY"] = config.claude_api_key
    if config.qianwen_api_key is not None:
        updates["QIANWEN_API_KEY"] = config.qianwen_api_key
    if config.deepseek_api_key is not None:
        updates["DEEPSEEK_API_KEY"] = config.deepseek_api_key
    if config.default_model is not None:
        if config.default_model not in {"claude", "qianwen", "deepseek"}:
            raise HTTPException(status_code=400, detail="default_model 必须是 claude/qianwen/deepseek 之一")
        updates["DEFAULT_AI_MODEL"] = config.default_model

    _upsert_env(updates)
    return {"success": True, "message": "AI配置已更新，需要重启服务生效"}
