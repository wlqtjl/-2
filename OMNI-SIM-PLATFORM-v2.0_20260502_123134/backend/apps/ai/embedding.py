from typing import List, Optional
import httpx
import os


class EmbeddingService:
    def __init__(self, api_base: str = "http://localhost:11434"):
        self.api_base = api_base
        self.model = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")

    async def generate_embedding(self, text: str) -> List[float]:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.api_base}/api/embeddings",
                    json={
                        "model": self.model,
                        "prompt": text
                    },
                    timeout=30.0
                )
                if response.status_code == 200:
                    data = response.json()
                    return data.get("embedding", [])
                return []
            except Exception as e:
                print(f"Embedding generation failed: {e}")
                return [0.0] * 768

    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        embeddings = []
        for text in texts:
            embedding = await self.generate_embedding(text)
            embeddings.append(embedding)
        return embeddings


class OllamaService:
    def __init__(self, api_base: str = "http://localhost:11434"):
        self.api_base = api_base
        self.default_model = os.getenv("LLM_MODEL", "llama3.2")

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        system: Optional[str] = None,
        temperature: float = 0.7
    ) -> str:
        async with httpx.AsyncClient() as client:
            try:
                payload = {
                    "model": model or self.default_model,
                    "prompt": prompt,
                    "temperature": temperature,
                    "stream": False
                }
                if system:
                    payload["system"] = system

                response = await client.post(
                    f"{self.api_base}/api/generate",
                    json=payload,
                    timeout=120.0
                )
                if response.status_code == 200:
                    data = response.json()
                    return data.get("response", "")
                return ""
            except Exception as e:
                print(f"LLM generation failed: {e}")
                return ""

    async def chat(
        self,
        messages: List[dict],
        model: Optional[str] = None,
        temperature: float = 0.7
    ) -> str:
        async with httpx.AsyncClient() as client:
            try:
                payload = {
                    "model": model or self.default_model,
                    "messages": messages,
                    "temperature": temperature,
                    "stream": False
                }
                response = await client.post(
                    f"{self.api_base}/api/chat",
                    json=payload,
                    timeout=120.0
                )
                if response.status_code == 200:
                    data = response.json()
                    return data.get("message", {}).get("content", "")
                return ""
            except Exception as e:
                print(f"LLM chat failed: {e}")
                return ""


embedding_service = EmbeddingService()
ollama_service = OllamaService()
