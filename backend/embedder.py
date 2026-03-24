"""BGE-M3 Embedding 封装"""
from typing import List, Optional
import torch
from sentence_transformers import SentenceTransformer
from functools import lru_cache
import hashlib
import json

from .config import settings


class Embedder:
    """Embedding 服务封装"""
    
    def __init__(
        self,
        model_name: str = None,
        device: str = None,
        batch_size: int = None
    ):
        self.model_name = model_name or settings.embedding_model
        self.device = self._get_device(device)
        self.batch_size = batch_size or settings.embedding_batch_size
        
        # 延迟加载模型
        self._model = None
        self._cache = {}  # 简单内存缓存
    
    def _get_device(self, device: Optional[str] = None) -> str:
        """确定计算设备"""
        device = device or settings.embedding_device
        
        if device == "auto":
            if torch.backends.mps.is_available():
                return "mps"  # Apple Silicon
            elif torch.cuda.is_available():
                return "cuda"
            else:
                return "cpu"
        return device
    
    @property
    def model(self) -> SentenceTransformer:
        """延迟加载模型"""
        if self._model is None:
            print(f"正在加载 Embedding 模型: {self.model_name}")
            print(f"使用设备: {self.device}")
            
            self._model = SentenceTransformer(
                self.model_name,
                device=self.device,
                trust_remote_code=True
            )
            print("模型加载完成")
        
        return self._model
    
    def embed(self, texts: List[str]) -> List[List[float]]:
        """
        将文本列表转换为向量
        
        Args:
            texts: 文本列表
        
        Returns:
            向量列表 (List of embeddings)
        """
        if not texts:
            return []
        
        # 检查缓存
        embeddings = []
        uncached_texts = []
        uncached_indices = []
        
        for i, text in enumerate(texts):
            cache_key = self._get_cache_key(text)
            if cache_key in self._cache:
                embeddings.append(self._cache[cache_key])
            else:
                embeddings.append(None)
                uncached_texts.append(text)
                uncached_indices.append(i)
        
        # 处理未缓存的文本
        if uncached_texts:
            print(f"Embedding {len(uncached_texts)} 个文本块...")
            new_embeddings = self.model.encode(
                uncached_texts,
                batch_size=self.batch_size,
                show_progress_bar=len(uncached_texts) > 10,
                convert_to_numpy=True,
                normalize_embeddings=True  # 归一化，便于余弦相似度
            )
            
            # 更新缓存和结果
            for idx, text, emb in zip(uncached_indices, uncached_texts, new_embeddings):
                cache_key = self._get_cache_key(text)
                self._cache[cache_key] = emb.tolist()
                embeddings[idx] = emb.tolist()
        
        return embeddings
    
    def embed_single(self, text: str) -> List[float]:
        """单个文本向量化"""
        return self.embed([text])[0]
    
    def _get_cache_key(self, text: str) -> str:
        """生成缓存键"""
        # 使用模型名 + 文本内容的哈希
        content = f"{self.model_name}:{text}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()
    
    def get_embedding_dim(self) -> int:
        """获取向量维度"""
        return self.model.get_sentence_embedding_dimension()


# 全局实例
_embedder: Optional[Embedder] = None


def get_embedder() -> Embedder:
    """获取全局 Embedder 实例"""
    global _embedder
    if _embedder is None:
        _embedder = Embedder()
    return _embedder