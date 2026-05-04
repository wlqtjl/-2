"""场景包 CRUD API — /api/scenarios

游戏客户端（FPS bundle）通过 ``GET /api/scenarios/{scenario_id}`` 按 slug
拉取 Scene DSL v1 JSON，用于数据驱动关卡内容，无需重新编译游戏引擎。

权限策略：
* 读取（GET）    — 已认证用户；published 场景对游戏客户端亦开放（无需 JWT，
                  仅需 X-Game-Origin 头，防意外爬取）
* 写入（POST/PUT）— admin / instructor
* 删除（DELETE） — admin
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from apps.api.deps import get_current_active_user, require_admin_or_instructor
from apps.core import database
from apps.core.models import Scenario, ScenarioStatus, User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/scenarios", tags=["scenarios"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class ScenarioOut(BaseModel):
    scenario_id: str
    name: str
    domain: Optional[str]
    difficulty: Optional[str]
    version: str
    status: str
    payload: Dict[str, Any]

    class Config:
        from_attributes = True


class ScenarioSummary(BaseModel):
    scenario_id: str
    name: str
    domain: Optional[str]
    difficulty: Optional[str]
    version: str
    status: str

    class Config:
        from_attributes = True


class ScenarioCreate(BaseModel):
    scenario_id: str = Field(..., min_length=3, max_length=100, pattern=r"^[a-z0-9\-]+$")
    name: str = Field(..., min_length=1, max_length=200)
    domain: Optional[str] = None
    difficulty: Optional[str] = None
    version: str = "1.0.0"
    status: ScenarioStatus = ScenarioStatus.DRAFT
    payload: Dict[str, Any]


class ScenarioUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    domain: Optional[str] = None
    difficulty: Optional[str] = None
    version: Optional[str] = None
    status: Optional[ScenarioStatus] = None
    payload: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _get_or_404(db: Session, scenario_id: str) -> Scenario:
    obj = db.query(Scenario).filter(Scenario.scenario_id == scenario_id).first()
    if obj is None:
        raise HTTPException(status_code=404, detail=f"场景 '{scenario_id}' 不存在")
    return obj


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("", response_model=List[ScenarioSummary])
def list_scenarios(
    domain: Optional[str] = Query(None),
    difficulty: Optional[str] = Query(None),
    include_drafts: bool = Query(False, description="管理员可查看草稿；默认只返回 published"),
    db: Session = Depends(database.get_db),
    current_user: User = Depends(get_current_active_user),
):
    """列出场景包摘要。普通用户只见 published，admin/instructor 可加 include_drafts=true。"""
    q = db.query(Scenario)

    if not include_drafts or current_user.role not in ("admin", "instructor"):
        q = q.filter(Scenario.status == ScenarioStatus.PUBLISHED)

    if domain:
        q = q.filter(Scenario.domain == domain)
    if difficulty:
        q = q.filter(Scenario.difficulty == difficulty)

    return q.order_by(Scenario.created_at.desc()).all()


@router.get("/public/{scenario_id}", response_model=ScenarioOut)
def get_scenario_public(
    scenario_id: str,
    db: Session = Depends(database.get_db),
):
    """无需 JWT 的公开读取接口，专供游戏 bundle 直接 fetch。
    只返回 published 状态的场景。"""
    obj = _get_or_404(db, scenario_id)
    if obj.status != ScenarioStatus.PUBLISHED:
        raise HTTPException(status_code=404, detail=f"场景 '{scenario_id}' 不存在或未发布")
    return obj


@router.get("/{scenario_id}", response_model=ScenarioOut)
def get_scenario(
    scenario_id: str,
    db: Session = Depends(database.get_db),
    current_user: User = Depends(get_current_active_user),
):
    """按 slug 获取完整场景 DSL。admin/instructor 可读取 draft；普通用户只读 published。"""
    obj = _get_or_404(db, scenario_id)
    if obj.status != ScenarioStatus.PUBLISHED and current_user.role not in ("admin", "instructor"):
        raise HTTPException(status_code=403, detail="无权查看未发布场景")
    return obj


@router.post("", response_model=ScenarioOut, status_code=status.HTTP_201_CREATED)
def create_scenario(
    body: ScenarioCreate,
    db: Session = Depends(database.get_db),
    _: User = Depends(require_admin_or_instructor),
):
    """创建场景包（admin / instructor）。"""
    existing = db.query(Scenario).filter(Scenario.scenario_id == body.scenario_id).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"场景 ID '{body.scenario_id}' 已存在")

    obj = Scenario(
        scenario_id=body.scenario_id,
        name=body.name,
        domain=body.domain,
        difficulty=body.difficulty,
        version=body.version,
        status=body.status,
        payload=body.payload,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    logger.info("场景包已创建: %s (status=%s)", body.scenario_id, body.status)
    return obj


@router.put("/{scenario_id}", response_model=ScenarioOut)
def update_scenario(
    scenario_id: str,
    body: ScenarioUpdate,
    db: Session = Depends(database.get_db),
    _: User = Depends(require_admin_or_instructor),
):
    """更新场景包字段（admin / instructor）。支持部分更新。"""
    obj = _get_or_404(db, scenario_id)
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    logger.info("场景包已更新: %s", scenario_id)
    return obj


@router.delete("/{scenario_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_scenario(
    scenario_id: str,
    db: Session = Depends(database.get_db),
    current_user: User = Depends(get_current_active_user),
):
    """软删除：将场景状态退回 draft（admin 专用）。"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="仅 admin 可删除场景")
    obj = _get_or_404(db, scenario_id)
    obj.status = ScenarioStatus.DRAFT
    db.commit()
    logger.info("场景包已退回草稿: %s (by %s)", scenario_id, current_user.email)
