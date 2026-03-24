"""配置管理"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
from pathlib import Path


class Settings(BaseSettings):
    """应用配置"""

    # Obsidian Vault
    obsidian_vault_path: str = Field(
        default="/Users/liuwj77/StorageObsidian",
        description="Obsidian Vault 绝对路径"
    )

    # ChromaDB
    chroma_persist_dir: str = Field(
        default="./data/chroma",
        description="ChromaDB 持久化目录"
    )
    chroma_collection_name: str = Field(
        default="obsidian_notes",
        description="ChromaDB 集合名称"
    )

    # Embedding
    embedding_model: str = Field(
        default="BAAI/bge-m3",
        description="Embedding 模型名称"
    )
    embedding_device: str = Field(
        default="auto",
        description="计算设备: auto/cpu/cuda/mps"
    )
    embedding_batch_size: int = Field(
        default=8,
        description="Embedding 批处理大小"
    )

    # Chunking
    chunk_size: int = Field(
        default=512,
        description="文本块最大 token 数"
    )
    chunk_overlap: int = Field(
        default=50,
        description="块重叠 token 数"
    )

    # Server
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    debug: bool = Field(default=False)

    # Logging
    log_level: str = Field(
        default="INFO",
        description="日志级别: DEBUG/INFO/WARNING/ERROR"
    )

    # Watcher
    watcher_debounce_seconds: float = Field(
        default=2.0,
        description="文件变更防抖时间（秒）"
    )
    
    @property
    def vault_path(self) -> Path:
        """获取 Vault Path 对象"""
        return Path(self.obsidian_vault_path).expanduser().absolute()
    
    @property
    def chroma_path(self) -> Path:
        """获取 ChromaDB Path 对象"""
        return Path(self.chroma_persist_dir).expanduser().absolute()
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# 全局配置实例
settings = Settings()