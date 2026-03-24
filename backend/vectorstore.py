"""ChromaDB 向量存储封装"""
from typing import List, Optional, Dict, Any
from pathlib import Path
import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.utils import embedding_functions
import uuid
from datetime import datetime

from .config import settings
from .embedder import get_embedder


class VectorStore:
    """ChromaDB 向量存储封装"""
    
    def __init__(
        self,
        persist_dir: str = None,
        collection_name: str = None
    ):
        self.persist_dir = persist_dir or str(settings.chroma_path)
        self.collection_name = collection_name or settings.chroma_collection_name
        
        # 初始化 ChromaDB
        self.client = chromadb.PersistentClient(
            path=self.persist_dir,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # 获取或创建集合
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        
        self.embedder = get_embedder()
    
    def add_documents(
        self,
        documents: List[str],
        metadatas: List[Dict[str, Any]],
        ids: Optional[List[str]] = None
    ) -> int:
        """
        添加文档到向量库
        
        Args:
            documents: 文档内容列表
            metadatas: 元数据列表
            ids: 可选的 ID 列表
        
        Returns:
            添加的文档数量
        """
        if not documents:
            return 0
        
        # 生成 ID
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in documents]
        
        # 生成向量
        embeddings = self.embedder.embed(documents)
        
        # 添加到 ChromaDB
        self.collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas
        )
        
        return len(documents)
    
    def upsert_documents(
        self,
        documents: List[str],
        metadatas: List[Dict[str, Any]],
        ids: List[str]
    ) -> int:
        """
        更新或插入文档（去重）
        
        Args:
            documents: 文档内容列表
            metadatas: 元数据列表
            ids: ID 列表（用于去重）
        
        Returns:
            处理的文档数量
        """
        if not documents:
            return 0
        
        # 生成向量
        embeddings = self.embedder.embed(documents)
        
        # Upsert 到 ChromaDB
        self.collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas
        )
        
        return len(documents)
    
    def search(
        self,
        query: str,
        top_k: int = 10,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        语义搜索
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            filter: 元数据过滤条件
        
        Returns:
            搜索结果列表
        """
        # 生成查询向量
        query_embedding = self.embedder.embed_single(query)
        
        # 搜索
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=filter,
            include=["documents", "metadatas", "distances"]
        )
        
        # 整理结果
        hits = []
        if results["ids"] and results["ids"][0]:
            for i in range(len(results["ids"][0])):
                distance = results["distances"][0][i]
                # ChromaDB 使用 L2 距离，转换为相似度
                similarity = 1 - distance
                
                hits.append({
                    "score": round(similarity, 4),
                    "content": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "id": results["ids"][0][i]
                })
        
        return hits
    
    def delete_by_source(self, source: str) -> int:
        """
        删除指定源文件的所有 chunks
        
        Args:
            source: 源文件路径
        
        Returns:
            删除的数量
        """
        # 先查询所有该源的 chunks
        results = self.collection.get(
            where={"source": source},
            include=["metadatas"]
        )
        
        if results["ids"]:
            self.collection.delete(ids=results["ids"])
            return len(results["ids"])
        
        return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """获取向量库统计信息"""
        count = self.collection.count()
        
        # 获取所有元数据中的唯一源文件
        results = self.collection.get(
            include=["metadatas"]
        )
        
        sources = set()
        if results["metadatas"]:
            for meta in results["metadatas"]:
                if "source" in meta:
                    sources.add(meta["source"])
        
        return {
            "total_chunks": count,
            "total_files": len(sources),
            "collection_name": self.collection_name,
            "persist_dir": self.persist_dir,
            "embedding_dim": self.embedder.get_embedding_dim()
        }
    
    def reset(self):
        """重置向量库（清空所有数据）"""
        self.client.delete_collection(self.collection_name)
        self.collection = self.client.create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )


# 全局实例
_vectorstore: Optional[VectorStore] = None


def get_vectorstore() -> VectorStore:
    """获取全局 VectorStore 实例"""
    global _vectorstore
    if _vectorstore is None:
        _vectorstore = VectorStore()
    return _vectorstore