from typing import Optional, Dict, Any, List
import httpx
import json
from apps.core.config import settings


class AIClient:
    """统一AI客户端，支持多种模型"""
    
    def __init__(self, model_type: Optional[str] = None):
        self.model_type = model_type or settings.DEFAULT_AI_MODEL
        self.clients = {
            "claude": self._create_claude_client(),
            "qianwen": self._create_qianwen_client(),
            "deepseek": self._create_deepseek_client()
        }
    
    def _create_claude_client(self):
        return httpx.AsyncClient(
            headers={
                "Content-Type": "application/json",
                "X-API-Key": settings.CLAUDE_API_KEY or "",
                "anthropic-version": "2023-06-01"
            },
            timeout=60.0
        )
    
    def _create_qianwen_client(self):
        return httpx.AsyncClient(
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {settings.QIANWEN_API_KEY or ''}"
            },
            timeout=60.0
        )
    
    def _create_deepseek_client(self):
        return httpx.AsyncClient(
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY or ''}"
            },
            timeout=60.0
        )
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model_type: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7
    ) -> str:
        """生成AI响应"""
        model = model_type or self.model_type
        
        if model not in self.clients:
            raise ValueError(f"Unsupported model type: {model}")
        
        try:
            if model == "claude":
                return await self._generate_claude(prompt, system_prompt, max_tokens, temperature)
            elif model == "qianwen":
                return await self._generate_qianwen(prompt, system_prompt, max_tokens, temperature)
            elif model == "deepseek":
                return await self._generate_deepseek(prompt, system_prompt, max_tokens, temperature)
        except Exception as e:
            # 尝试回退到其他可用模型
            return await self._fallback_generate(prompt, system_prompt, max_tokens, temperature, model)
    
    async def _generate_claude(self, prompt: str, system_prompt: Optional[str], max_tokens: int, temperature: float) -> str:
        if not settings.CLAUDE_API_KEY:
            raise ValueError("Claude API key not configured")
        
        payload = {
            "model": settings.CLAUDE_MODEL,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        response = await self.clients["claude"].post(settings.CLAUDE_API_URL, json=payload)
        response.raise_for_status()
        
        result = response.json()
        return result["content"][0]["text"]
    
    async def _generate_qianwen(self, prompt: str, system_prompt: Optional[str], max_tokens: int, temperature: float) -> str:
        if not settings.QIANWEN_API_KEY:
            raise ValueError("Qianwen API key not configured")
        
        payload = {
            "model": settings.QIANWEN_MODEL,
            "input": prompt,
            "parameters": {
                "max_tokens": max_tokens,
                "temperature": temperature
            }
        }
        
        if system_prompt:
            payload["input"] = f"{system_prompt}\n\n{prompt}"
        
        response = await self.clients["qianwen"].post(settings.QIANWEN_API_URL, json=payload)
        response.raise_for_status()
        
        result = response.json()
        return result.get("output", {}).get("text", "")
    
    async def _generate_deepseek(self, prompt: str, system_prompt: Optional[str], max_tokens: int, temperature: float) -> str:
        if not settings.DEEPSEEK_API_KEY:
            raise ValueError("DeepSeek API key not configured")
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": settings.DEEPSEEK_MODEL,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        response = await self.clients["deepseek"].post(settings.DEEPSEEK_API_URL, json=payload)
        response.raise_for_status()
        
        result = response.json()
        return result["choices"][0]["message"]["content"]
    
    async def _fallback_generate(self, prompt: str, system_prompt: Optional[str], max_tokens: int, temperature: float, failed_model: str) -> str:
        """当首选模型失败时，尝试其他可用模型"""
        available_models = [m for m in ["claude", "qianwen", "deepseek"] if m != failed_model]
        
        for model in available_models:
            try:
                return await self.generate(prompt, system_prompt, model, max_tokens, temperature)
            except Exception:
                continue
        
        # 如果所有模型都失败，返回简单的默认响应
        return f"AI服务暂时不可用，请稍后重试。\n\n原始请求：{prompt[:100]}..."
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        model_type: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7
    ) -> str:
        """多轮对话"""
        model = model_type or self.model_type
        
        if model == "claude":
            return await self._chat_claude(messages, max_tokens, temperature)
        elif model == "deepseek":
            return await self._chat_deepseek(messages, max_tokens, temperature)
        else:
            # 对于千问，转换消息格式
            prompt = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
            return await self._generate_qianwen(prompt, None, max_tokens, temperature)
    
    async def _chat_claude(self, messages: List[Dict[str, str]], max_tokens: int, temperature: float) -> str:
        if not settings.CLAUDE_API_KEY:
            raise ValueError("Claude API key not configured")
        
        payload = {
            "model": settings.CLAUDE_MODEL,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages
        }
        
        response = await self.clients["claude"].post(settings.CLAUDE_API_URL, json=payload)
        response.raise_for_status()
        
        result = response.json()
        return result["content"][0]["text"]
    
    async def _chat_deepseek(self, messages: List[Dict[str, str]], max_tokens: int, temperature: float) -> str:
        if not settings.DEEPSEEK_API_KEY:
            raise ValueError("DeepSeek API key not configured")
        
        payload = {
            "model": settings.DEEPSEEK_MODEL,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        response = await self.clients["deepseek"].post(settings.DEEPSEEK_API_URL, json=payload)
        response.raise_for_status()
        
        result = response.json()
        return result["choices"][0]["message"]["content"]
    
    async def summarize(self, text: str, max_length: int = 200, model_type: Optional[str] = None) -> str:
        """文本摘要"""
        prompt = f"""请对以下文本进行简明扼要的总结，不超过{max_length}字：

{text}

总结："""
        
        return await self.generate(prompt, "你是一个专业的文本摘要助手", model_type)
    
    async def extract_keywords(self, text: str, count: int = 10, model_type: Optional[str] = None) -> List[str]:
        """提取关键词"""
        prompt = f"""请从以下文本中提取最多{count}个关键词，用逗号分隔：

{text}

关键词："""
        
        result = await self.generate(prompt, "你是一个专业的关键词提取助手", model_type)
        return [k.strip() for k in result.split(",") if k.strip()]
    
    async def analyze_sentiment(self, text: str, model_type: Optional[str] = None) -> Dict[str, Any]:
        """情感分析"""
        prompt = f"""请分析以下文本的情感倾向，返回JSON格式：

{text}

返回格式：{{"sentiment": "positive|neutral|negative", "confidence": 0.0-1.0, "reason": "分析理由"}}"""
        
        result = await self.generate(prompt, "你是一个专业的情感分析助手", model_type)
        
        try:
            return json.loads(result)
        except (json.JSONDecodeError, ValueError, KeyError):
            return {"sentiment": "neutral", "confidence": 0.5, "reason": "解析失败"}
    
    def get_available_models(self) -> List[str]:
        """获取可用的模型列表"""
        available = []
        if settings.CLAUDE_API_KEY:
            available.append("claude")
        if settings.QIANWEN_API_KEY:
            available.append("qianwen")
        if settings.DEEPSEEK_API_KEY:
            available.append("deepseek")
        return available if available else ["claude", "qianwen", "deepseek"]
    
    async def close(self):
        """关闭所有客户端连接"""
        for client in self.clients.values():
            await client.aclose()


ai_client = AIClient()
