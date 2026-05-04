from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import httpx
import asyncio


class VectorPoint(BaseModel):
    id: str
    vector: List[float]
    payload: Dict[str, Any]


class SearchResult(BaseModel):
    id: str
    score: float
    payload: Dict[str, Any]


class VectorCollection(BaseModel):
    name: str
    vectors_size: int
    points_count: int
    status: str


class QdrantClient:
    def __init__(self, host: str = "localhost", port: int = 6333, api_key: Optional[str] = None):
        self.host = host
        self.port = port
        self.api_key = api_key
        self.base_url = f"http://{host}:{port}"
        self.headers = {"api-key": api_key} if api_key else {}

    async def create_collection(
        self,
        name: str,
        vector_size: int,
        distance: str = "Cosine"
    ) -> bool:
        payload = {
            "name": name,
            "vectors": {
                "size": vector_size,
                "distance": distance
            }
        }
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{self.base_url}/collections/{name}",
                json=payload,
                headers=self.headers,
                timeout=10.0
            )
            return response.status_code == 200

    async def delete_collection(self, name: str) -> bool:
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{self.base_url}/collections/{name}",
                headers=self.headers,
                timeout=10.0
            )
            return response.status_code == 200

    async def list_collections(self) -> List[str]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/collections",
                headers=self.headers,
                timeout=10.0
            )
            if response.status_code == 200:
                data = response.json()
                return [c["name"] for c in data.get("result", {}).get("collections", [])]
            return []

    async def upsert_points(
        self,
        collection_name: str,
        points: List[VectorPoint]
    ) -> bool:
        payload = {
            "points": [
                {
                    "id": p.id,
                    "vector": p.vector,
                    "payload": p.payload
                }
                for p in points
            ]
        }
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{self.base_url}/collections/{collection_name}/points",
                json=payload,
                headers=self.headers,
                timeout=30.0
            )
            return response.status_code == 200

    async def search(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 5,
        score_threshold: Optional[float] = None,
        query_filter: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        payload = {
            "vector": query_vector,
            "limit": limit,
            "with_payload": True
        }
        if score_threshold:
            payload["score_threshold"] = score_threshold
        if query_filter:
            payload["filter"] = query_filter

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/collections/{collection_name}/points/search",
                json=payload,
                headers=self.headers,
                timeout=10.0
            )
            if response.status_code == 200:
                results = response.json().get("result", [])
                return [
                    SearchResult(
                        id=r["id"],
                        score=r["score"],
                        payload=r.get("payload", {})
                    )
                    for r in results
                ]
            return []

    async def scroll(
        self,
        collection_name: str,
        limit: int = 100,
        offset: Optional[str] = None,
        filter_cond: Optional[Dict[str, Any]] = None
    ) -> tuple[List[Dict[str, Any]], Optional[str]]:
        payload = {"limit": limit, "with_payload": True}
        if offset:
            payload["offset"] = offset
        if filter_cond:
            payload["filter"] = filter_cond

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/collections/{collection_name}/points/scroll",
                json=payload,
                headers=self.headers,
                timeout=10.0
            )
            if response.status_code == 200:
                data = response.json().get("result", {})
                points = data.get("points", [])
                next_page_offset = data.get("next_page_offset")
                return points, next_page_offset
            return [], None

    async def delete_points(
        self,
        collection_name: str,
        point_ids: List[str]
    ) -> bool:
        payload = {"points": point_ids}
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/collections/{collection_name}/points/delete",
                json=payload,
                headers=self.headers,
                timeout=10.0
            )
            return response.status_code == 200


class MemoryVectorStore:
    COLLECTION_USER = "user_memory"
    COLLECTION_FEEDBACK = "feedback_memory"
    COLLECTION_KNOWLEDGE = "knowledge_base"
    COLLECTION_REFERENCE = "reference_docs"

    def __init__(self, qdrant_client: QdrantClient):
        self.client = qdrant_client

    async def initialize(self):
        collections = await self.client.list_collections()
        for collection in [self.COLLECTION_USER, self.COLLECTION_FEEDBACK,
                          self.COLLECTION_KNOWLEDGE, self.COLLECTION_REFERENCE]:
            if collection not in collections:
                await self.client.create_collection(collection, vector_size=768)

    async def store_user_memory(
        self,
        user_id: int,
        memory_text: str,
        embedding: List[float],
        memory_type: str = "interaction"
    ) -> bool:
        point = VectorPoint(
            id=f"user_{user_id}_{memory_type}_{int(asyncio.get_event_loop().time() * 1000)}",
            vector=embedding,
            payload={
                "user_id": user_id,
                "memory_text": memory_text,
                "memory_type": memory_type
            }
        )
        return await self.client.upsert_points(self.COLLECTION_USER, [point])

    async def search_user_memory(
        self,
        user_id: int,
        query_embedding: List[float],
        limit: int = 5
    ) -> List[SearchResult]:
        return await self.client.search(
            self.COLLECTION_USER,
            query_vector=query_embedding,
            limit=limit,
            query_filter={
                "must": [
                    {"key": "user_id", "match": {"value": user_id}}
                ]
            }
        )

    async def store_feedback(
        self,
        user_id: int,
        level_id: int,
        feedback_text: str,
        embedding: List[float],
        rating: int
    ) -> bool:
        point = VectorPoint(
            id=f"feedback_{user_id}_{level_id}_{int(asyncio.get_event_loop().time() * 1000)}",
            vector=embedding,
            payload={
                "user_id": user_id,
                "level_id": level_id,
                "feedback_text": feedback_text,
                "rating": rating
            }
        )
        return await self.client.upsert_points(self.COLLECTION_FEEDBACK, [point])

    async def store_knowledge(
        self,
        content: str,
        embedding: List[float],
        metadata: Dict[str, Any]
    ) -> bool:
        point = VectorPoint(
            id=f"knowledge_{metadata.get('source', 'unknown')}_{int(asyncio.get_event_loop().time() * 1000)}",
            vector=embedding,
            payload={
                "content": content,
                **metadata
            }
        )
        return await self.client.upsert_points(self.COLLECTION_KNOWLEDGE, [point])

    async def search_knowledge(
        self,
        query_embedding: List[float],
        limit: int = 5,
        topic_filter: Optional[str] = None
    ) -> List[SearchResult]:
        query_filter = None
        if topic_filter:
            query_filter = {
                "must": [
                    {"key": "topic", "match": {"value": topic_filter}}
                ]
            }
        return await self.client.search(
            self.COLLECTION_KNOWLEDGE,
            query_vector=query_embedding,
            limit=limit,
            query_filter=query_filter
        )
