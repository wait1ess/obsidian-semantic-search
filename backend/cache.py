"""持久化向量缓存 - SQLite 实现"""
import sqlite3
import hashlib
import json
import threading
import logging
from pathlib import Path
from typing import List, Optional, Any
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class PersistentCache:
    """
    基于 SQLite 的持久化向量缓存
    - 支持跨会话持久化
    - 线程安全
    - 自动清理过期条目
    """

    def __init__(self, db_path: str, max_size: int = 50000):
        self.db_path = Path(db_path)
        self.max_size = max_size
        self._local = threading.local()

        # 确保目录存在
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # 初始化数据库
        self._init_db()
        logger.info(f"持久化缓存初始化: {db_path}")

    def _get_conn(self) -> sqlite3.Connection:
        """获取线程本地的数据库连接"""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False
            )
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    @contextmanager
    def _get_connection(self):
        """上下文管理器获取连接"""
        conn = self._get_conn()
        try:
            yield conn
        except Exception as e:
            conn.rollback()
            raise e

    def _init_db(self):
        """初始化数据库表"""
        with self._get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS embeddings (
                    key TEXT PRIMARY KEY,
                    embedding BLOB NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    access_count INTEGER DEFAULT 1
                )
            ''')
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_accessed_at ON embeddings(accessed_at)
            ''')
            conn.commit()

    def get(self, key: str) -> Optional[List[float]]:
        """获取缓存的向量"""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    '''SELECT embedding FROM embeddings WHERE key = ?''',
                    (key,)
                )
                row = cursor.fetchone()

                if row:
                    # 更新访问时间和计数
                    conn.execute(
                        '''UPDATE embeddings
                           SET accessed_at = CURRENT_TIMESTAMP,
                               access_count = access_count + 1
                           WHERE key = ?''',
                        (key,)
                    )
                    conn.commit()

                    # 解析向量
                    embedding = json.loads(row['embedding'])
                    return embedding
        except Exception as e:
            logger.warning(f"缓存读取失败: {e}")

        return None

    def set(self, key: str, embedding: List[float]):
        """设置缓存"""
        try:
            with self._get_connection() as conn:
                # 检查是否需要清理
                self._maybe_cleanup(conn)

                # 插入或更新
                conn.execute('''
                    INSERT OR REPLACE INTO embeddings (key, embedding, accessed_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                ''', (key, json.dumps(embedding)))
                conn.commit()
        except Exception as e:
            logger.warning(f"缓存写入失败: {e}")

    def contains(self, key: str) -> bool:
        """检查键是否存在"""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    'SELECT 1 FROM embeddings WHERE key = ?',
                    (key,)
                )
                return cursor.fetchone() is not None
        except Exception as e:
            logger.warning(f"缓存查询失败: {e}")
            return False

    def delete(self, key: str) -> bool:
        """删除缓存项"""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    'DELETE FROM embeddings WHERE key = ?',
                    (key,)
                )
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.warning(f"缓存删除失败: {e}")
            return False

    def clear(self):
        """清空缓存"""
        try:
            with self._get_connection() as conn:
                conn.execute('DELETE FROM embeddings')
                conn.commit()
                logger.info("缓存已清空")
        except Exception as e:
            logger.warning(f"缓存清空失败: {e}")

    def _maybe_cleanup(self, conn):
        """检查并清理过期条目"""
        cursor = conn.execute('SELECT COUNT(*) FROM embeddings')
        count = cursor.fetchone()[0]

        if count >= self.max_size:
            # 删除最旧的 10% 条目
            delete_count = self.max_size // 10
            conn.execute('''
                DELETE FROM embeddings
                WHERE key IN (
                    SELECT key FROM embeddings
                    ORDER BY accessed_at ASC
                    LIMIT ?
                )
            ''', (delete_count,))
            logger.info(f"缓存清理: 删除 {delete_count} 个条目")

    def get_stats(self) -> dict:
        """获取缓存统计"""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute('SELECT COUNT(*) FROM embeddings')
                count = cursor.fetchone()[0]

                cursor = conn.execute('SELECT SUM(access_count) FROM embeddings')
                total_access = cursor.fetchone()[0] or 0

                return {
                    "total_entries": count,
                    "total_access": total_access,
                    "max_size": self.max_size
                }
        except Exception as e:
            return {"error": str(e)}

    def close(self):
        """关闭连接"""
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None


def get_cache_key(model_name: str, text: str) -> str:
    """生成缓存键"""
    content = f"{model_name}:{text}"
    return hashlib.md5(content.encode()).hexdigest()