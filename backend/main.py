"""FastAPI 主服务"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from pathlib import Path
import asyncio
import time
from datetime import datetime
import os
import threading

from .config import settings
from .embedder import get_embedder
from .vectorstore import get_vectorstore
from .chunker import MarkdownChunker
from .watcher import init_watcher, get_watcher


# ============== 索引进度追踪 ==============
class IndexProgress:
    """索引进度状态"""
    def __init__(self):
        self.lock = threading.Lock()
        self.is_running = False
        self.total_files = 0
        self.processed_files = 0
        self.total_chunks = 0
        self.current_file = ""
        self.start_time = None
        self.status = "idle"  # idle, running, completed, error
        self.message = ""
    
    def start(self, total_files: int):
        with self.lock:
            self.is_running = True
            self.total_files = total_files
            self.processed_files = 0
            self.total_chunks = 0
            self.current_file = ""
            self.start_time = time.time()
            self.status = "running"
            self.message = "开始索引..."
    
    def update(self, processed: int, chunks: int, current_file: str):
        with self.lock:
            self.processed_files = processed
            self.total_chunks = chunks
            self.current_file = current_file
            self.message = f"正在处理: {current_file}"
    
    def complete(self, total_chunks: int):
        with self.lock:
            self.is_running = False
            self.status = "completed"
            self.total_chunks = total_chunks
            self.message = f"完成！索引 {self.processed_files} 个文件，{total_chunks} 个文本块"
    
    def error(self, message: str):
        with self.lock:
            self.is_running = False
            self.status = "error"
            self.message = message
    
    def to_dict(self) -> dict:
        with self.lock:
            elapsed = time.time() - self.start_time if self.start_time else 0
            progress = (self.processed_files / self.total_files * 100) if self.total_files > 0 else 0
            return {
                "is_running": self.is_running,
                "status": self.status,
                "total_files": self.total_files,
                "processed_files": self.processed_files,
                "total_chunks": self.total_chunks,
                "current_file": self.current_file,
                "progress_percent": round(progress, 1),
                "elapsed_seconds": round(elapsed, 1),
                "message": self.message
            }

# 全局进度实例
index_progress = IndexProgress()


# ============== Models ==============

class SearchRequest(BaseModel):
    """搜索请求"""
    query: str
    top_k: int = 10
    folder: Optional[str] = None


class SearchResult(BaseModel):
    """搜索结果项"""
    score: float
    content: str
    source: str
    heading: Optional[str] = None
    file_path: Optional[str] = None
    chunk_index: Optional[int] = None


class SearchResponse(BaseModel):
    """搜索响应"""
    results: List[SearchResult]
    total: int
    took_ms: int


class IndexResponse(BaseModel):
    """索引响应"""
    status: str
    message: str
    files_indexed: int = 0
    chunks_created: int = 0
    took_seconds: float = 0


class StatsResponse(BaseModel):
    """统计响应"""
    total_chunks: int
    total_files: int
    collection_name: str
    embedding_dim: int
    watcher_running: bool
    last_events: List[Dict[str, Any]] = []


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    timestamp: str
    vault_path: str
    vault_exists: bool


# ============== App ==============

app = FastAPI(
    title="Obsidian RAG API",
    description="Obsidian Vault 语义检索系统",
    version="0.1.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============== Global State ==============

_indexing = False
_chunker: Optional[MarkdownChunker] = None


def get_chunker() -> MarkdownChunker:
    """获取 Chunker 实例"""
    global _chunker
    if _chunker is None:
        _chunker = MarkdownChunker(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap
        )
    return _chunker


# ============== Startup & Shutdown ==============

@app.on_event("startup")
async def startup():
    """启动时初始化"""
    # 确保 ChromaDB 目录存在
    settings.chroma_path.mkdir(parents=True, exist_ok=True)
    
    # 初始化 Embedder（预加载模型）
    print("正在初始化 Embedding 模型...")
    get_embedder()
    
    # 初始化文件监听
    watcher = init_watcher(
        settings.vault_path,
        on_file_change=handle_file_change
    )
    watcher.start()
    
    print("🚀 服务启动完成")


@app.on_event("shutdown")
async def shutdown():
    """关闭时清理"""
    watcher = get_watcher()
    if watcher:
        watcher.stop()
    print("👋 服务已关闭")


# ============== File Change Handler ==============

def handle_file_change(path: Path, event_type: str):
    """处理文件变更"""
    if event_type == "deleted":
        # 删除向量库中的内容
        try:
            rel_path = str(path.relative_to(settings.vault_path))
            store = get_vectorstore()
            deleted = store.delete_by_source(rel_path)
            print(f"已删除 {deleted} 个 chunks: {rel_path}")
            
            # 更新 watcher 记录
            watcher = get_watcher()
            if watcher:
                watcher.remove_indexed(path)
        except Exception as e:
            print(f"删除失败: {path} - {e}")
    
    elif event_type in ("created", "modified"):
        # 索引文件
        try:
            index_single_file(path)
            
            watcher = get_watcher()
            if watcher:
                watcher.mark_indexed(path)
        except Exception as e:
            print(f"索引失败: {path} - {e}")


def index_single_file(file_path: Path) -> int:
    """索引单个文件"""
    chunker = get_chunker()
    store = get_vectorstore()
    
    # 获取相对路径
    rel_path = str(file_path.relative_to(settings.vault_path))
    
    # 先删除旧的 chunks
    store.delete_by_source(rel_path)
    
    # 分块
    chunks = chunker.chunk_file(file_path)
    if not chunks:
        return 0
    
    # 准备数据
    documents = [c["content"] for c in chunks]
    metadatas = [c["metadata"] for c in chunks]
    ids = [f"{rel_path}#{c['metadata']['chunk_index']}" for c in chunks]
    
    # 更新向量库
    store.upsert_documents(documents, metadatas, ids)
    
    return len(chunks)


# ============== API Endpoints ==============

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查"""
    vault_exists = settings.vault_path.exists()
    
    return HealthResponse(
        status="healthy" if vault_exists else "warning",
        timestamp=datetime.now().isoformat(),
        vault_path=str(settings.vault_path),
        vault_exists=vault_exists
    )


@app.post("/api/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """语义搜索"""
    start_time = time.time()
    
    store = get_vectorstore()
    
    # 构建过滤条件
    filter_dict = None
    if request.folder:
        filter_dict = {"source": {"$contains": request.folder}}
    
    # 搜索
    results = store.search(
        query=request.query,
        top_k=request.top_k,
        filter=filter_dict
    )
    
    took_ms = int((time.time() - start_time) * 1000)
    
    # 转换结果
    search_results = []
    for r in results:
        metadata = r.get("metadata", {})
        search_results.append(SearchResult(
            score=r["score"],
            content=r["content"],
            source=metadata.get("source", ""),
            heading=metadata.get("heading"),
            file_path=metadata.get("file_path"),
            chunk_index=metadata.get("chunk_index")
        ))
    
    return SearchResponse(
        results=search_results,
        total=len(search_results),
        took_ms=took_ms
    )


@app.post("/api/index", response_model=IndexResponse)
async def full_index(background_tasks: BackgroundTasks):
    """全量索引 - 异步后台执行"""
    global _indexing

    if _indexing or index_progress.is_running:
        return IndexResponse(
            status="error",
            message="索引任务正在进行中"
        )

    _indexing = True

    def run_index():
        """在后台线程中执行索引"""
        try:
            # 扫描所有 .md 文件
            md_files = list(settings.vault_path.rglob("*.md"))

            # 排除 .obsidian 目录
            md_files = [f for f in md_files if ".obsidian" not in str(f)]

            # 初始化进度
            index_progress.start(len(md_files))

            # 索引
            total_chunks = 0
            indexed_files = 0

            for i, md_file in enumerate(md_files):
                try:
                    chunks = index_single_file(md_file)
                    total_chunks += chunks
                    indexed_files += 1

                    # 更新进度
                    rel_path = str(md_file.relative_to(settings.vault_path))
                    index_progress.update(i + 1, total_chunks, rel_path)

                    # 更新 watcher 记录
                    watcher = get_watcher()
                    if watcher:
                        watcher.mark_indexed(md_file)

                except Exception as e:
                    print(f"索引失败: {md_file} - {e}")

            # 完成
            index_progress.complete(total_chunks)
            print(f"✅ 索引完成: {indexed_files} 文件, {total_chunks} 文本块")

        except Exception as e:
            print(f"❌ 索引错误: {e}")
            index_progress.error(str(e))

        finally:
            global _indexing
            _indexing = False

    # 启动后台线程
    thread = threading.Thread(target=run_index, daemon=True)
    thread.start()

    return IndexResponse(
        status="success",
        message="索引任务已启动，请轮询 /api/index/progress 获取进度"
    )


@app.post("/api/index/file")
async def index_file(file_path: str):
    """索引单个文件"""
    path = Path(file_path)
    
    if not path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    
    if not path.is_relative_to(settings.vault_path):
        raise HTTPException(status_code=400, detail="文件不在 Vault 中")
    
    chunks = index_single_file(path)
    
    return {
        "status": "success",
        "file": str(path.relative_to(settings.vault_path)),
        "chunks": chunks
    }


@app.get("/api/stats", response_model=StatsResponse)
async def get_stats():
    """获取统计信息"""
    store = get_vectorstore()
    stats = store.get_stats()
    
    watcher = get_watcher()
    last_events = watcher.get_event_log(10) if watcher else []
    
    return StatsResponse(
        total_chunks=stats["total_chunks"],
        total_files=stats["total_files"],
        collection_name=stats["collection_name"],
        embedding_dim=stats["embedding_dim"],
        watcher_running=watcher.is_running() if watcher else False,
        last_events=last_events
    )


@app.get("/api/index/progress")
async def get_index_progress():
    """获取索引进度"""
    return index_progress.to_dict()


@app.post("/api/sync/pause")
async def pause_sync():
    """暂停同步"""
    watcher = get_watcher()
    if watcher:
        watcher.stop()
        return {"status": "paused"}
    return {"status": "error", "message": "Watcher 未初始化"}


@app.post("/api/sync/resume")
async def resume_sync():
    """恢复同步"""
    watcher = get_watcher()
    if watcher:
        watcher.start()
        return {"status": "resumed"}
    return {"status": "error", "message": "Watcher 未初始化"}


@app.delete("/api/reset")
async def reset_database():
    """重置向量库"""
    store = get_vectorstore()
    store.reset()
    
    # 清空 watcher 记录
    watcher = get_watcher()
    if watcher:
        watcher._indexed_files.clear()
    
    return {"status": "success", "message": "向量库已重置"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )