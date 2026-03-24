"""BGE-M3 Embedding 封装"""
from typing import List, Optional
import torch
from sentence_transformers import SentenceTransformer
from functools import lru_cache
import hashlib
import json
import threading
import logging
from collections import OrderedDict

from .config import settings

# 配置日志
logger = logging.getLogger(__name__)


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


class LRUCache:
    """
    线程安全的 LRU 缓存
    - 自动淘汰最久未使用的条目
    - 限制内存使用
    """
    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self._cache = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str):
        """获取缓存值，存在则移动到末尾（最近使用）"""
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key]
            return None

    def set(self, key: str, value):
        """设置缓存值"""
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            else:
                if len(self._cache) >= self.max_size:
                    self._cache.popitem(last=False)  # 淘汰最久未使用
            self._cache[key] = value

    def __contains__(self, key: str) -> bool:
        with self._lock:
            return key in self._cache

    def clear(self):
        with self._lock:
            self._cache.clear()

    def __len__(self):
        with self._lock:
            return len(self._cache)


class Embedder:
    """Embedding 服务封装"""

    def __init__(
        self,
        model_name: str = None,
        device: str = None,
        batch_size: int = None,
        cache_size: int = 10000
    ):
        self.model_name = model_name or settings.embedding_model
        self.device = self._get_device(device)
        self.batch_size = batch_size or settings.embedding_batch_size
        self._debug = settings.log_level == "DEBUG"

        # 延迟加载模型
        self._model = None
        self._cache = LRUCache(max_size=cache_size)  # LRU 缓存

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
            logger.info(f"正在加载 Embedding 模型: {self.model_name}")
            logger.info(f"使用设备: {self.device}")

            self._model = SentenceTransformer(
                self.model_name,
                device=self.device,
                trust_remote_code=True
            )
            logger.info("模型加载完成")

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

        # 第一阶段：检查缓存（LRUCache 已线程安全）
        embeddings = []
        uncached_texts = []
        uncached_indices = []

        for i, text in enumerate(texts):
            cache_key = self._get_cache_key(text)
            cached = self._cache.get(cache_key)
            if cached is not None:
                embeddings.append(cached)
            else:
                embeddings.append(None)
                uncached_texts.append(text)
                uncached_indices.append(i)

        # 第二阶段：处理未缓存的文本（模型推断线程安全）
        if uncached_texts:
            if self._debug:
                logger.debug(f"Embedding {len(uncached_texts)} 个文本块...")

            # 分批处理
            all_new_embeddings = []
            batch_size = min(self.batch_size, 8)  # 限制批次大小

            for i in range(0, len(uncached_texts), batch_size):
                batch = uncached_texts[i:i+batch_size]
                if self._debug:
                    logger.debug(f"  处理批次 {i//batch_size + 1}/{(len(uncached_texts)-1)//batch_size + 1}")

                batch_embeddings = self.model.encode(
                    batch,
                    batch_size=len(batch),
                    show_progress_bar=False,
                    convert_to_numpy=True,
                    normalize_embeddings=True
                )
                all_new_embeddings.extend(batch_embeddings)

            # 第三阶段：更新缓存（LRUCache 已线程安全）
            for idx, text, emb in zip(uncached_indices, uncached_texts, all_new_embeddings):
                cache_key = self._get_cache_key(text)
                self._cache.set(cache_key, emb.tolist())
                embeddings[idx] = emb.tolist()

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
        self._cache.clear()

    def get_cache_size(self) -> int:
        """获取缓存大小"""
        return len(self._cache)

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