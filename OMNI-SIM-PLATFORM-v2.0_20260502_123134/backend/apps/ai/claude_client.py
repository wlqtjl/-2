import httpx
from apps.core.config import settings


class ClaudeClient:
    def __init__(self):
        self.api_key = settings.CLAUDE_API_KEY
        self.api_url = settings.CLAUDE_API_URL

    async def generate(self, prompt: str, system: str = "") -> str:
        if not self.api_key:
            return "Claude API key not configured. Please set CLAUDE_API_KEY in .env"

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

        payload = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 4096,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }

        if system:
            payload["system"] = system

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.api_url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                return data.get("content", [{"text": ""}])[0].get("text", "")
        except Exception as e:
            return f"Error calling Claude API: {str(e)}"


claude_client = ClaudeClient()
