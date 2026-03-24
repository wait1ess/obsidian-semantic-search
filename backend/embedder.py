"""BGE-M3 Embedding 封装"""
from typing import List, Optional
import torch
from sentence_transformers import SentenceTransformer
from functools import lru_cache
import hashlib
import json
import threading

from .config import settings


class ReadWriteLock:
    """
    读写锁实现
    - 多个读操作可以同时进行
    - 写操作独占访问
    - 适合读多写少的场景
    """
    def __init__(self):
        self._lock = threading.Lock()
        self._read_ready = threading.Condition(self._lock)
        self._readers = 0
        self._writers = 0
        self._writing = False

    def acquire_read(self):
        """获取读锁"""
        with self._lock:
            while self._writers > 0 or self._writing:
                self._read_ready.wait()
            self._readers += 1

    def release_read(self):
        """释放读锁"""
        with self._lock:
            self._readers -= 1
            if self._readers == 0:
                self._read_ready.notify_all()

    def acquire_write(self):
        """获取写锁"""
        with self._lock:
            self._writers += 1
            while self._readers > 0 or self._writing:
                self._read_ready.wait()
            self._writers -= 1
            self._writing = True

    def release_write(self):
        """释放写锁"""
        with self._lock:
            self._writing = False
            self._read_ready.notify_all()


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
        self._cache_lock = ReadWriteLock()  # 读写锁保护缓存
    
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

        # 第一阶段：读锁检查缓存
        embeddings = []
        uncached_texts = []
        uncached_indices = []

        self._cache_lock.acquire_read()
        try:
            for i, text in enumerate(texts):
                cache_key = self._get_cache_key(text)
                if cache_key in self._cache:
                    embeddings.append(self._cache[cache_key])
                else:
                    embeddings.append(None)
                    uncached_texts.append(text)
                    uncached_indices.append(i)
        finally:
            self._cache_lock.release_read()

        # 第二阶段：处理未缓存的文本（无需锁，模型推断线程安全）
        if uncached_texts:
            print(f"Embedding {len(uncached_texts)} 个文本块...")

            # 分批处理
            all_new_embeddings = []
            batch_size = min(self.batch_size, 8)  # 限制批次大小

            for i in range(0, len(uncached_texts), batch_size):
                batch = uncached_texts[i:i+batch_size]
                print(f"  处理批次 {i//batch_size + 1}/{(len(uncached_texts)-1)//batch_size + 1}")

                batch_embeddings = self.model.encode(
                    batch,
                    batch_size=len(batch),
                    show_progress_bar=False,
                    convert_to_numpy=True,
                    normalize_embeddings=True
                )
                all_new_embeddings.extend(batch_embeddings)

            # 第三阶段：写锁更新缓存
            self._cache_lock.acquire_write()
            try:
                for idx, text, emb in zip(uncached_indices, uncached_texts, all_new_embeddings):
                    cache_key = self._get_cache_key(text)
                    self._cache[cache_key] = emb.tolist()
                    embeddings[idx] = emb.tolist()
            finally:
                self._cache_lock.release_write()

            # 清理
            del all_new_embeddings
            import gc
            gc.collect()

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
        self._cache_lock.acquire_write()
        try:
            self._cache.clear()
        finally:
            self._cache_lock.release_write()
    
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