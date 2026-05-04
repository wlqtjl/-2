from typing import Optional, Dict, Any, List, Callable
from enum import Enum
import httpx
from apps.core.config import settings


class AIProvider(str, Enum):
    CLAUDE = "claude"
    QWEN = "qwen"
    DEEPSEEK = "deepseek"
    OPENAI = "openai"


class AIConfigManager:
    """
    统一的AI客户端管理器
    - 支持多种AI Provider (Claude, DeepSeek, Qianwen, OpenAI)
    - 自动检测可用provider
    - 自动fallback到其他provider
    - 所有配置从settings读取
    """

    def __init__(self):
        self._providers: Dict[AIProvider, Dict[str, Any]] = {}
        self._initialize_providers()
        self._active_provider: Optional[AIProvider] = None
        self._setup_active_provider()

    def _initialize_providers(self):
        """从settings初始化所有provider配置"""
        self._providers = {
            AIProvider.CLAUDE: {
                "api_key": settings.CLAUDE_API_KEY,
                "api_url": settings.CLAUDE_API_URL,
                "model": settings.CLAUDE_MODEL,
                "enabled": bool(settings.CLAUDE_API_KEY),
            },
            AIProvider.QWEN: {
                "api_key": settings.QIANWEN_API_KEY,
                "api_url": settings.QIANWEN_API_URL,
                "model": settings.QIANWEN_MODEL,
                "enabled": bool(settings.QIANWEN_API_KEY),
            },
            AIProvider.DEEPSEEK: {
                "api_key": settings.DEEPSEEK_API_KEY,
                "api_url": settings.DEEPSEEK_API_URL,
                "model": settings.DEEPSEEK_MODEL,
                "enabled": bool(settings.DEEPSEEK_API_KEY),
            },
            AIProvider.OPENAI: {
                "api_key": None,
                "api_url": "https://api.openai.com/v1",
                "model": "gpt-4o-mini",
                "enabled": False,
            },
        }

    def _setup_active_provider(self):
        """设置默认provider，按优先级选择第一个可用的"""
        priority = [AIProvider.CLAUDE, AIProvider.DEEPSEEK, AIProvider.QWEN]
        for provider in priority:
            if self._providers.get(provider, {}).get("enabled"):
                self._active_provider = provider
                return
        self._active_provider = None

    def get_provider_config(self, provider: AIProvider) -> Optional[Dict[str, Any]]:
        """获取指定provider的配置"""
        return self._providers.get(provider)

    def is_provider_enabled(self, provider: AIProvider) -> bool:
        """检查provider是否启用"""
        config = self._providers.get(provider)
        return config is not None and config.get("enabled", False)

    def get_active_provider(self) -> Optional[AIProvider]:
        """获取当前激活的provider"""
        return self._active_provider

    def list_enabled_providers(self) -> List[AIProvider]:
        """列出所有已启用的provider"""
        return [p for p in AIProvider if self.is_provider_enabled(p)]

    def get_available_providers_for_fallback(self, exclude: Optional[AIProvider] = None) -> List[AIProvider]:
        """获取可用于fallback的provider列表（按优先级排序）"""
        priority = [AIProvider.CLAUDE, AIProvider.DEEPSEEK, AIProvider.QWEN, AIProvider.OPENAI]
        available = [p for p in priority if p != exclude and self.is_provider_enabled(p)]
        return available

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        provider: Optional[AIProvider] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7
    ) -> str:
        """
        统一的生成接口
        1. 尝试使用指定的provider
        2. 如果失败，自动fallback到其他provider
        3. 所有provider都失败时返回默认响应
        """
        target_provider = provider or self._active_provider

        if target_provider and self.is_provider_enabled(target_provider):
            result = await self._call_provider(target_provider, prompt, system_prompt, max_tokens, temperature)
            if result["success"]:
                return result["content"]

        fallback_providers = self.get_available_providers_for_fallback(exclude=target_provider)
        for fallback_provider in fallback_providers:
            result = await self._call_provider(fallback_provider, prompt, system_prompt, max_tokens, temperature)
            if result["success"]:
                self._active_provider = fallback_provider
                return result["content"]

        return self._get_default_response(prompt)

    async def _call_provider(
        self,
        provider: AIProvider,
        prompt: str,
        system_prompt: Optional[str],
        max_tokens: int,
        temperature: float
    ) -> Dict[str, Any]:
        """调用指定的provider"""
        try:
            if provider == AIProvider.CLAUDE:
                return await self._call_claude(prompt, system_prompt, max_tokens, temperature)
            elif provider == AIProvider.DEEPSEEK:
                return await self._call_deepseek(prompt, system_prompt, max_tokens, temperature)
            elif provider == AIProvider.QWEN:
                return await self._call_qwen(prompt, system_prompt, max_tokens, temperature)
            elif provider == AIProvider.OPENAI:
                return await self._call_openai(prompt, system_prompt, max_tokens, temperature)
            else:
                return {"success": False, "content": f"Unsupported provider: {provider}"}
        except Exception as e:
            return {"success": False, "content": f"{provider.value} error: {str(e)}"}

    async def _call_claude(self, prompt: str, system_prompt: Optional[str], max_tokens: int, temperature: float) -> Dict[str, Any]:
        """调用Claude API"""
        config = self._providers[AIProvider.CLAUDE]

        headers = {
            "x-api-key": config["api_key"],
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

        payload = {
            "model": config["model"],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}]
        }

        if system_prompt:
            payload["system"] = system_prompt

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(config["api_url"], headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            content = data.get("content", [{"text": ""}])[0].get("text", "")
            return {"success": True, "content": content}

    async def _call_deepseek(self, prompt: str, system_prompt: Optional[str], max_tokens: int, temperature: float) -> Dict[str, Any]:
        """调用DeepSeek API"""
        config = self._providers[AIProvider.DEEPSEEK]

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": config["model"],
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }

        headers = {
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(config["api_url"], headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return {"success": True, "content": content}

    async def _call_qwen(self, prompt: str, system_prompt: Optional[str], max_tokens: int, temperature: float) -> Dict[str, Any]:
        """调用Qianwen API"""
        config = self._providers[AIProvider.QWEN]

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": config["model"],
            "input": {"messages": messages},
            "parameters": {
                "max_tokens": max_tokens,
                "temperature": temperature
            }
        }

        headers = {
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{config['api_url']}/services/aigc/text-generation/generation",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            content = data.get("output", {}).get("text", "")
            return {"success": True, "content": content}

    async def _call_openai(self, prompt: str, system_prompt: Optional[str], max_tokens: int, temperature: float) -> Dict[str, Any]:
        """调用OpenAI API"""
        config = self._providers[AIProvider.OPENAI]

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": config["model"],
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }

        headers = {
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{config['api_url']}/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return {"success": True, "content": content}

    def _get_default_response(self, prompt: str) -> str:
        """当所有provider都失败时，返回默认响应"""
        return f"AI服务暂时不可用，请稍后重试。\n\n原始请求：{prompt[:100]}..."

    async def chat(
        self,
        messages: List[Dict[str, str]],
        provider: Optional[AIProvider] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7
    ) -> str:
        """多轮对话接口"""
        if not messages:
            return "No messages provided"

        prompt = "\n".join([f"{m.get('role', 'user')}: {m.get('content', '')}" for m in messages])
        system_prompt = None

        for msg in messages:
            if msg.get("role") == "system":
                system_prompt = msg.get("content")
                break

        return await self.generate(prompt, system_prompt, provider, max_tokens, temperature)

    def get_status(self) -> Dict[str, Any]:
        """获取AI服务状态"""
        enabled_providers = self.list_enabled_providers()
        return {
            "api_configured": len(enabled_providers) > 0,
            "coordinator_ready": self._active_provider is not None,
            "default_model": self._active_provider.value if self._active_provider else None,
            "available_providers": [p.value for p in enabled_providers],
            "provider_details": {
                p.value: {
                    "enabled": self.is_provider_enabled(p),
                    "model": self._providers[p]["model"]
                }
                for p in AIProvider
            }
        }


ai_config_manager = AIConfigManager()
ai_client = ai_config_manager
