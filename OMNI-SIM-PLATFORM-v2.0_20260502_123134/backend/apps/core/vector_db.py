from typing import List, Dict, Any, Optional, Tuple
from apps.core.config import settings
import json
import logging

logger = logging.getLogger(__name__)

# qdrant-client / sentence-transformers / numpy 是可选重型依赖，
# 缺失时降级为内存桩，保证主流程不阻塞启动。
try:
    from qdrant_client import QdrantClient, models  # type: ignore
    from qdrant_client.http.exceptions import UnexpectedResponse  # type: ignore
    QDRANT_AVAILABLE = True
except ImportError:  # pragma: no cover
    QdrantClient = None  # type: ignore
    models = None  # type: ignore
    UnexpectedResponse = Exception  # type: ignore
    QDRANT_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer  # type: ignore
    ST_AVAILABLE = True
except ImportError:  # pragma: no cover
    SentenceTransformer = None  # type: ignore
    ST_AVAILABLE = False

try:
    import numpy as np  # type: ignore
except ImportError:  # pragma: no cover
    np = None  # type: ignore


class VectorDatabase:
    def __init__(self):
        self.collection_name = settings.VECTOR_DB_COLLECTION
        self.client = None
        self.encoder = None
        self.available = QDRANT_AVAILABLE and ST_AVAILABLE
        if not self.available:
            logger.warning(
                "向量库依赖未安装 (qdrant-client / sentence-transformers)，已退化为内存桩。"
            )
            return
        try:
            self.client = QdrantClient(
                host=settings.VECTOR_DB_HOST,
                port=settings.VECTOR_DB_PORT,
                api_key=settings.VECTOR_DB_API_KEY,
            )
            self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
        except Exception as e:  # pragma: no cover
            logger.warning(f"向量库初始化失败，已退化为内存桩: {e}")
            self.available = False
    
    def initialize_collection(self):
        """初始化向量数据库集合"""
        if not self.available:
            return
        try:
            self.client.get_collection(self.collection_name)
        except UnexpectedResponse:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=384,
                    distance=models.Distance.COSINE
                )
            )
            logger.info(f"Created collection: {self.collection_name}")

    def _generate_embedding(self, text: str) -> List[float]:
        """生成文本的向量嵌入"""
        if not self.available:
            return []
        embedding = self.encoder.encode(text)
        return embedding.tolist()
    
    def add_document(self, document_id: str, content: str, metadata: Dict[str, Any] = None):
        """添加文档到向量数据库"""
        embedding = self._generate_embedding(content)
        point = models.PointStruct(
            id=int(document_id) if document_id.isdigit() else hash(document_id),
            vector=embedding,
            payload={
                "document_id": document_id,
                "content": content,
                **(metadata or {})
            }
        )
        self.client.upsert(
            collection_name=self.collection_name,
            points=[point]
        )
    
    def add_documents(self, documents: List[Dict[str, Any]]):
        """批量添加文档"""
        points = []
        for doc in documents:
            embedding = self._generate_embedding(doc['content'])
            point = models.PointStruct(
                id=int(doc['id']) if str(doc['id']).isdigit() else hash(doc['id']),
                vector=embedding,
                payload={
                    "document_id": str(doc['id']),
                    "content": doc['content'],
                    **(doc.get('metadata', {}))
                }
            )
            points.append(point)
        
        if points:
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
    
    def search(self, query: str, top_k: int = 5, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """搜索相似文档"""
        if not self.available:
            return []
        query_vector = self._generate_embedding(query)
        
        qdrant_filters = None
        if filters:
            must_conditions = []
            for key, value in filters.items():
                if isinstance(value, list):
                    must_conditions.append(models.FieldCondition(
                        key=key,
                        match=models.MatchAny(any=value)
                    ))
                else:
                    must_conditions.append(models.FieldCondition(
                        key=key,
                        match=models.MatchValue(value=value)
                    ))
            qdrant_filters = models.Filter(must=must_conditions)
        
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=top_k,
            query_filter=qdrant_filters,
            with_payload=True,
            with_vectors=False
        )
        
        return [
            {
                "document_id": hit.payload.get("document_id"),
                "content": hit.payload.get("content"),
                "score": hit.score,
                "metadata": {k: v for k, v in hit.payload.items() if k not in ["document_id", "content"]}
            }
            for hit in results
        ]
    
    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """获取单个文档"""
        try:
            point_id = int(document_id) if document_id.isdigit() else hash(document_id)
            result = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[point_id],
                with_payload=True,
                with_vectors=False
            )
            if result:
                payload = result[0].payload
                return {
                    "document_id": payload.get("document_id"),
                    "content": payload.get("content"),
                    "metadata": {k: v for k, v in payload.items() if k not in ["document_id", "content"]}
                }
            return None
        except Exception:
            return None
    
    def delete_document(self, document_id: str):
        """删除文档"""
        point_id = int(document_id) if document_id.isdigit() else hash(document_id)
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=models.PointIdsList(ids=[point_id])
        )
    
    def clear_collection(self):
        """清空集合"""
        self.client.delete_collection(collection_name=self.collection_name)
        self.initialize_collection()
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """获取集合统计信息"""
        try:
            info = self.client.get_collection(self.collection_name)
            return {
                "vectors_count": info.vectors_count,
                "points_count": info.points_count,
                "indexed_points_count": info.indexed_points_count
            }
        except Exception as e:
            return {"error": str(e)}


class MemoryVectorStore:
    """用户记忆向量存储"""

    def __init__(self):
        self.collection_name = "user_memories"
        self.client = None
        self.encoder = None
        self.available = QDRANT_AVAILABLE and ST_AVAILABLE
        if not self.available:
            return
        try:
            self.client = QdrantClient(
                host=settings.VECTOR_DB_HOST,
                port=settings.VECTOR_DB_PORT,
                api_key=settings.VECTOR_DB_API_KEY,
            )
            self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
        except Exception as e:  # pragma: no cover
            logger.warning(f"MemoryVectorStore 初始化失败: {e}")
            self.available = False

    def initialize_collection(self):
        """初始化记忆集合"""
        if not self.available:
            return
        try:
            self.client.get_collection(self.collection_name)
        except UnexpectedResponse:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=384,
                    distance=models.Distance.COSINE
                )
            )
            logger.info(f"Created memory collection: {self.collection_name}")
    
    def add_memory(self, user_id: int, memory_type: str, content: str, context: Dict[str, Any] = None):
        """添加用户记忆"""
        embedding = self.encoder.encode(content)
        point = models.PointStruct(
            id=hash(f"{user_id}_{memory_type}_{content[:50]}"),
            vector=embedding,
            payload={
                "user_id": user_id,
                "memory_type": memory_type,
                "content": content,
                "timestamp": context.get("timestamp") if context else None,
                "related_level": context.get("related_level") if context else None,
                "score": context.get("score") if context else None,
                **(context or {})
            }
        )
        self.client.upsert(
            collection_name=self.collection_name,
            points=[point]
        )
    
    def search_memories(self, user_id: int, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """搜索用户记忆"""
        query_vector = self.encoder.encode(query)
        
        qdrant_filter = models.Filter(
            must=[models.FieldCondition(
                key="user_id",
                match=models.MatchValue(value=user_id)
            )]
        )
        
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=top_k,
            query_filter=qdrant_filter,
            with_payload=True,
            with_vectors=False
        )
        
        return [
            {
                "memory_type": hit.payload.get("memory_type"),
                "content": hit.payload.get("content"),
                "score": hit.score,
                "metadata": {k: v for k, v in hit.payload.items() if k not in ["user_id", "memory_type", "content"]}
            }
            for hit in results
        ]
    
    def get_user_memories(self, user_id: int, memory_type: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """获取用户所有记忆"""
        must_conditions = [models.FieldCondition(
            key="user_id",
            match=models.MatchValue(value=user_id)
        )]
        
        if memory_type:
            must_conditions.append(models.FieldCondition(
                key="memory_type",
                match=models.MatchValue(value=memory_type)
            ))
        
        qdrant_filter = models.Filter(must=must_conditions)
        
        results = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=qdrant_filter,
            limit=limit,
            with_payload=True,
            with_vectors=False
        )
        
        memories = []
        for point in results[0]:
            payload = point.payload
            memories.append({
                "memory_type": payload.get("memory_type"),
                "content": payload.get("content"),
                "metadata": {k: v for k, v in payload.items() if k not in ["user_id", "memory_type", "content"]}
            })
        
        return memories


vector_db = VectorDatabase()
memory_store = MemoryVectorStore()
