import os
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel
from apps.core.config import settings

logger = logging.getLogger(__name__)

BLUEGREEN_CONFIG_FILE = "/tmp/bluegreen_config.json"


class DeploymentStatus(str, Enum):
    """部署状态"""
    BLUE = "blue"
    GREEN = "green"
    SWITCHING = "switching"
    UNKNOWN = "unknown"


class BlueGreenConfig(BaseModel):
    """蓝绿配置模型"""
    active_env: DeploymentStatus = DeploymentStatus.BLUE
    blue_version: str = "0.0.0"
    green_version: str = "0.0.0"
    last_switch_time: Optional[datetime] = None
    switch_in_progress: bool = False
    health_check_enabled: bool = True
    health_check_url: str = "/health"
    health_check_timeout: int = 30
    rollback_on_failure: bool = True


class BlueGreenManager:
    """蓝绿部署管理器"""
    
    def __init__(self):
        self.config = self._load_config()
    
    def _load_config(self) -> BlueGreenConfig:
        """加载配置"""
        if os.path.exists(BLUEGREEN_CONFIG_FILE):
            try:
                with open(BLUEGREEN_CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    return BlueGreenConfig(**data)
            except Exception as e:
                logger.error(f"Failed to load bluegreen config: {str(e)}")
        return BlueGreenConfig()
    
    def _save_config(self):
        """保存配置"""
        try:
            with open(BLUEGREEN_CONFIG_FILE, 'w') as f:
                json.dump(self.config.dict(), f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save bluegreen config: {str(e)}")
    
    def get_active_env(self) -> DeploymentStatus:
        """获取当前活跃环境"""
        return self.config.active_env
    
    def get_inactive_env(self) -> DeploymentStatus:
        """获取非活跃环境"""
        if self.config.active_env == DeploymentStatus.BLUE:
            return DeploymentStatus.GREEN
        return DeploymentStatus.BLUE
    
    def set_version(self, env: DeploymentStatus, version: str):
        """设置环境版本"""
        if env == DeploymentStatus.BLUE:
            self.config.blue_version = version
        else:
            self.config.green_version = version
        self._save_config()
    
    def get_version(self, env: DeploymentStatus) -> str:
        """获取环境版本"""
        if env == DeploymentStatus.BLUE:
            return self.config.blue_version
        return self.config.green_version
    
    async def switch(self) -> bool:
        """切换环境"""
        if self.config.switch_in_progress:
            logger.warning("Switch already in progress")
            return False
        
        self.config.switch_in_progress = True
        self.config.active_env = self.get_inactive_env()
        self.config.last_switch_time = datetime.now(timezone.utc)
        self._save_config()
        
        logger.info(f"Switched to {self.config.active_env.value} environment")
        return True
    
    def cancel_switch(self):
        """取消切换"""
        self.config.switch_in_progress = False
        self._save_config()
        logger.info("Switch cancelled")
    
    def get_status(self) -> Dict[str, Any]:
        """获取当前状态"""
        return {
            "active_env": self.config.active_env.value,
            "blue_version": self.config.blue_version,
            "green_version": self.config.green_version,
            "last_switch_time": self.config.last_switch_time,
            "switch_in_progress": self.config.switch_in_progress
        }


# 全局蓝绿管理器实例
bluegreen_manager = BlueGreenManager()


# 蓝绿发布API路由
from fastapi import APIRouter, HTTPException, Depends
from apps.api.deps import require_admin_role

router = APIRouter(prefix="/bluegreen", tags=["蓝绿发布"])


@router.get("/status")
async def get_bluegreen_status():
    """获取蓝绿发布状态"""
    return bluegreen_manager.get_status()


@router.post("/switch")
async def switch_environment(
    current_user = Depends(require_admin_role)
):
    """切换蓝绿环境"""
    success = await bluegreen_manager.switch()
    if not success:
        raise HTTPException(status_code=400, detail="切换失败，可能正在进行中")
    return {"success": True, "message": "环境切换成功"}


@router.post("/cancel")
async def cancel_switch(
    current_user = Depends(require_admin_role)
):
    """取消切换"""
    bluegreen_manager.cancel_switch()
    return {"success": True, "message": "已取消切换"}


@router.post("/version")
async def set_version(
    env: str,
    version: str,
    current_user = Depends(require_admin_role)
):
    """设置环境版本"""
    if env.lower() not in ["blue", "green"]:
        raise HTTPException(status_code=400, detail="无效的环境名称")
    
    env_status = DeploymentStatus.BLUE if env.lower() == "blue" else DeploymentStatus.GREEN
    bluegreen_manager.set_version(env_status, version)
    
    return {"success": True, "message": f"{env}环境版本已更新为{version}"}


@router.get("/health-check")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy", "service": "bluegreen-manager"}