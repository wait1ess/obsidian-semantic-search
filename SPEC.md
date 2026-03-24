# SPEC.md - Obsidian 语义检索系统

## 1. 项目概述

### 1.1 项目信息

| 项目 | 内容 |
|------|------|
| **项目名称** | obsidian-semantic-search |
| **版本** | v0.3.7 |
| **位置** | `/Users/liuwj77/temp_obsidian_rag` |
| **GitHub** | https://github.com/wait1ess/obsidian-semantic-search |
| **许可证** | MIT |

### 1.2 项目目标

为 Obsidian Vault 构建本地语义检索系统，实现：
- 基于向量相似度的语义搜索
- 实时文件监听与自动同步
- Markdown 格式渲染
- Obsidian URI 跳转

### 1.3 技术栈

| 层级 | 技术 | 版本 |
|------|------|------|
| **后端框架** | FastAPI | 0.109.0 |
| **ASGI 服务器** | Uvicorn | 0.27.0 |
| **向量模型** | BAAI/bge-m3 | latest |
| **深度学习框架** | PyTorch | 2.1.2 |
| **向量数据库** | ChromaDB | 0.4.22 |
| **文件监听** | watchdog | 3.0.0 |
| **Web UI** | Streamlit | 1.30.0 |
| **HTTP 客户端** | httpx | 0.26.0 |
| **Python** | - | 3.10 |

---

## 2. 系统架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              用户交互层                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────────┐                      ┌─────────────────┐            │
│   │   Streamlit     │      HTTP/REST       │   FastAPI       │            │
│   │   Web UI        │ ◄──────────────────► │   Backend       │            │
│   │   (Port 8501)   │                      │   (Port 8000)   │            │
│   └─────────────────┘                      └─────────────────┘            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              核心服务层                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐  │
│   │  Embedder   │   │ VectorStore │   │  Chunker    │   │  Watcher    │  │
│   │  向量化服务  │   │  向量存储    │   │  文本分块   │   │  文件监听   │  │
│   └─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘  │
│         │                  │                                     │        │
│         ▼                  ▼                                     ▼        │
│   ┌─────────────┐   ┌─────────────┐                      ┌─────────────┐  │
│   │   BGE-M3    │   │  ChromaDB   │                      │  watchdog   │  │
│   │   Model     │   │  (SQLite)   │                      │  Observer   │  │
│   └─────────────┘   └─────────────┘                      └─────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              数据存储层                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                      Obsidian Vault                                 │  │
│   │                   /Users/liuwj77/StorageObsidian                    │  │
│   │                                                                     │  │
│   │   ├── 网络安全知识库（理论知识）/                                    │  │
│   │   │   ├── 01_infrastructure/                                        │  │
│   │   │   ├── 02_database/                                              │  │
│   │   │   ├── 03_web_security/                                          │  │
│   │   │   └── ...                                                       │  │
│   │   └── 网络安全知识库（实战payload）/                                 │  │
│   │                                                                     │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│   ┌─────────────────────────┐      ┌─────────────────────────┐            │
│   │   ChromaDB 持久化        │      │   HuggingFace 缓存      │            │
│   │   data/chroma/          │      │   ~/.cache/huggingface/ │            │
│   │   - chroma.sqlite3      │      │   - models--BAAI--bge-m3│            │
│   │   - *.bin               │      │                         │            │
│   └─────────────────────────┘      └─────────────────────────┘            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 数据流图

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         索引流程（写入）                                  │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Obsidian Vault                                                         │
│       │                                                                  │
│       │ 1. 文件变更事件 (created/modified/deleted)                       │
│       ▼                                                                  │
│  ┌─────────────┐                                                        │
│  │  Watcher    │ ──► 防抖处理 (2秒)                                      │
│  │  监听器     │                                                         │
│  └─────────────┘                                                        │
│       │                                                                  │
│       │ 2. 文件内容                                                      │
│       ▼                                                                  │
│  ┌─────────────┐                                                        │
│  │  Chunker    │ ──► 按标题分割 → 控制块大小(512 tokens)                 │
│  │  分块器     │                                                         │
│  └─────────────┘                                                        │
│       │                                                                  │
│       │ 3. 文本块列表                                                    │
│       ▼                                                                  │
│  ┌─────────────┐                                                        │
│  │  Embedder   │ ──► Tokenize → Transformer → 向量 [1024维]             │
│  │  向量化     │                                                         │
│  └─────────────┘                                                        │
│       │                                                                  │
│       │ 4. 向量 + 元数据                                                 │
│       ▼                                                                  │
│  ┌─────────────┐                                                        │
│  │ VectorStore │ ──► upsert 到 ChromaDB                                  │
│  │  向量存储   │                                                         │
│  └─────────────┘                                                        │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│                         搜索流程（读取）                                  │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  用户输入查询                                                            │
│       │                                                                  │
│       │ 1. HTTP POST /api/search                                        │
│       ▼                                                                  │
│  ┌─────────────┐                                                        │
│  │  FastAPI    │                                                        │
│  │  路由处理   │                                                         │
│  └─────────────┘                                                        │
│       │                                                                  │
│       │ 2. query 字符串                                                  │
│       ▼                                                                  │
│  ┌─────────────┐                                                        │
│  │  Embedder   │ ──► 查询向量化 [1024维]                                │
│  │  向量化     │                                                         │
│  └─────────────┘                                                        │
│       │                                                                  │
│       │ 3. 查询向量                                                      │
│       ▼                                                                  │
│  ┌─────────────┐                                                        │
│  │ VectorStore │ ──► 余弦相似度计算 → Top-K 结果                        │
│  │  检索       │                                                         │
│  └─────────────┘                                                        │
│       │                                                                  │
│       │ 4. 结果列表                                                      │
│       ▼                                                                  │
│  ┌─────────────┐                                                        │
│  │  Streamlit  │ ──► Markdown渲染 → Obsidian URI跳转                    │
│  │  Web UI     │                                                         │
│  └─────────────┘                                                        │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 3. 目录结构

```
temp_obsidian_rag/
│
├── backend/                    # 后端服务模块
│   ├── __init__.py            # 包初始化，导出公共接口
│   ├── config.py              # 配置管理，Pydantic Settings
│   ├── main.py                # FastAPI 应用入口，路由定义
│   ├── embedder.py            # BGE-M3 向量化封装
│   ├── vectorstore.py         # ChromaDB 向量存储封装
│   ├── chunker.py             # Markdown 文本分块器
│   └── watcher.py             # 文件系统监听器
│
├── ui/                         # Web UI 模块
│   ├── __init__.py            # 包初始化
│   └── app.py                 # Streamlit 应用
│
├── data/                       # 数据目录
│   └── chroma/                # ChromaDB 持久化存储
│       ├── chroma.sqlite3     # SQLite 元数据库
│       └── */                 # HNSW 索引文件
│
├── scripts/                    # 辅助脚本
│   ├── init_index.py          # 全量索引脚本
│   └── reset_db.py            # 重置向量库
│
├── tests/                      # 测试目录
│   └── (待添加)
│
├── requirements.txt            # Python 依赖清单
├── .gitignore                  # Git 忽略规则
├── SPEC.md                     # 本文档
├── README.md                   # 项目说明
└── LICENSE                     # MIT 许可证
```

---

## 4. 模块详细说明

### 4.1 backend/config.py - 配置管理

**职责：** 集中管理所有配置项，支持环境变量覆盖

**关键类：**
```python
class Settings(BaseSettings):
    # Obsidian Vault
    obsidian_vault_path: str          # Vault 路径
    chroma_persist_dir: str           # ChromaDB 存储路径
    chroma_collection_name: str       # 集合名称
    
    # Embedding
    embedding_model: str              # 模型名称
    embedding_device: str             # 计算设备
    embedding_batch_size: int         # 批处理大小
    
    # Chunking
    chunk_size: int                   # 块大小
    chunk_overlap: int                # 块重叠
    
    # Server
    host: str                         # 服务主机
    port: int                         # 服务端口
    
    # Watcher
    watcher_debounce_seconds: float   # 防抖时间
```

**配置优先级：**
1. 环境变量 (最高)
2. .env 文件
3. 代码默认值 (最低)

**依赖：**
- `pydantic-settings` - 配置管理基类
- `pathlib.Path` - 路径处理

---

### 4.2 backend/embedder.py - 向量化服务

**职责：** 封装 BGE-M3 模型，提供文本向量化能力

**关键类：**
```python
class Embedder:
    def __init__(model_name, device, batch_size)
    def embed(texts: List[str]) -> List[List[float]]
    def embed_single(text: str) -> List[float]
    def get_embedding_dim() -> int
    def clear_cache()
```

**内部实现：**

```
Embedder
    │
    ├── _model: SentenceTransformer    # 懒加载
    ├── _cache: dict                   # 内存缓存
    │
    └── embed() 流程:
        │
        ├─► 检查缓存
        │       │
        │       └─► 命中 → 直接返回
        │
        ├─► 未命中 → 批量处理
        │       │
        │       ├─► Tokenize
        │       ├─► Transformer Forward
        │       └─► Normalize
        │
        └─► 更新缓存 → 返回向量
```

**设备选择逻辑：**
```python
if device == "auto":
    if torch.backends.mps.is_available():
        return "mps"   # Apple Silicon
    elif torch.cuda.is_available():
        return "cuda"  # NVIDIA GPU
    else:
        return "cpu"
```

**依赖：**
- `sentence-transformers` - 模型加载
- `torch` - 深度学习框架

---

### 4.3 backend/vectorstore.py - 向量存储

**职责：** 封装 ChromaDB，提供向量存储和检索能力

**关键类：**
```python
class VectorStore:
    def __init__(persist_dir, collection_name)
    def add_documents(documents, metadatas, ids) -> int
    def upsert_documents(documents, metadatas, ids) -> int
    def search(query, top_k, filter) -> List[dict]
    def delete_by_source(source) -> int
    def get_stats() -> dict
    def reset()
```

**数据结构：**

```
ChromaDB Collection: obsidian_notes
    │
    ├── ids: List[str]                    # "相对路径#块索引"
    │       例: "网络安全/sql_injection.md#0"
    │
    ├── embeddings: List[List[float]]     # 1024维向量
    │
    ├── documents: List[str]              # 文本内容
    │
    └── metadatas: List[dict]             # 元数据
            {
                "source": "相对路径",
                "heading": "标题",
                "chunk_index": 0,
                "file_path": "绝对路径"
            }
```

**检索流程：**
```
search(query, top_k)
    │
    ├─► query_embedding = embedder.embed_single(query)
    │
    ├─► results = collection.query(
    │       query_embeddings=[query_embedding],
    │       n_results=top_k,
    │       where=filter
    │   )
    │
    └─► 转换为标准格式:
        {
            "score": 1 - distance,  # L2距离转相似度
            "content": document,
            "metadata": metadata
        }
```

**依赖：**
- `chromadb` - 向量数据库
- `backend.embedder` - 向量化服务

---

### 4.4 backend/chunker.py - 文本分块器

**职责：** 将 Markdown 文件分割为语义完整的文本块

**关键类：**
```python
class MarkdownChunker:
    def __init__(chunk_size, chunk_overlap, min_chunk_size)
    def chunk_file(file_path) -> List[dict]
    def chunk_text(content, source, file_path) -> List[dict]
```

**分块算法：**

```
Markdown 文件
    │
    ▼
┌───────────────────────────────────────────────────────────┐
│  Step 1: 按标题层级分割                                   │
│                                                           │
│  检测 # ## ### 标题，将文档分割为多个 section              │
│  每个 section 保留其标题                                  │
└───────────────────────────────────────────────────────────┘
    │
    ▼
┌───────────────────────────────────────────────────────────┐
│  Step 2: 检查 section 大小                                │
│                                                           │
│  if section.size <= min_chunk_size:                       │
│      合并到上一个 chunk (保留语义完整性)                   │
│  elif section.size > chunk_size:                          │
│      进入 Step 3 进一步分割                               │
│  else:                                                    │
│      直接作为一个 chunk                                   │
└───────────────────────────────────────────────────────────┘
    │
    ▼
┌───────────────────────────────────────────────────────────┐
│  Step 3: 大块分割                                         │
│                                                           │
│  1. 按段落分割 (\n\n)                                     │
│  2. 如果段落仍超限，按句子分割                             │
│  3. 添加重叠窗口 (保留上下文)                             │
└───────────────────────────────────────────────────────────┘
    │
    ▼
┌───────────────────────────────────────────────────────────┐
│  Step 4: 生成 chunk 元数据                                │
│                                                           │
│  {                                                        │
│    "content": "文本内容",                                 │
│    "metadata": {                                          │
│      "source": "相对路径",                                │
│      "chunk_index": 0,                                    │
│      "heading": "所属标题",                               │
│      "file_path": "绝对路径"                              │
│    }                                                      │
│  }                                                        │
└───────────────────────────────────────────────────────────┘
```

**依赖：**
- `pathlib.Path` - 文件路径处理
- `re` - 正则表达式

---

### 4.5 backend/watcher.py - 文件监听器

**职责：** 实时监听 Obsidian Vault 变更，触发自动同步

**关键类：**
```python
class VaultWatcher:
    def __init__(vault_path, on_file_change, debounce_seconds)
    def start()                    # 启动监听
    def stop()                     # 停止监听
    def is_running() -> bool       # 状态检查
    def get_event_log(limit)       # 获取事件日志
    def mark_indexed(path)         # 标记已索引
    def remove_indexed(path)       # 移除标记
```

**事件处理流程：**

```
文件系统事件
    │
    ├─► created  ──┐
    ├─► modified ──┼──► DebouncedHandler
    └─► deleted  ──┘         │
                              │
                              ▼
                    ┌─────────────────┐
                    │  防抖处理        │
                    │  等待 2 秒       │
                    │  合并连续事件    │
                    └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  事件分发        │
                    │                 │
                    │  created  → 索引│
                    │  modified → 更新│
                    │  deleted  → 删除│
                    └─────────────────┘
                              │
                              ▼
                    callback(path, event_type)
```

**防抖实现：**
```python
class DebouncedHandler(FileSystemEventHandler):
    def _schedule_event(path, event_type):
        # 记录事件
        self._pending_events[path] = event
        
        # 取消之前的定时器
        if self._timer:
            self._timer.cancel()
        
        # 设置新定时器
        self._timer = Timer(debounce_seconds, self._process_events)
        self._timer.start()
```

**依赖：**
- `watchdog` - 文件系统监听
- `threading.Timer` - 防抖定时器

---

### 4.6 backend/main.py - FastAPI 应用

**职责：** 提供 REST API 接口，协调各模块工作

**应用生命周期：**

```
┌──────────────────────────────────────────────────────────┐
│  Startup                                                 │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  1. 创建 ChromaDB 目录                                   │
│  2. 初始化 Embedder (预加载模型)                         │
│  3. 初始化 VaultWatcher                                  │
│  4. 启动文件监听                                         │
│                                                          │
└──────────────────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────┐
│  Runtime                                                 │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  处理 HTTP 请求                                          │
│  - /health                                               │
│  - /api/search                                           │
│  - /api/index                                            │
│  - /api/stats                                            │
│  - /api/index/progress                                   │
│                                                          │
│  Watcher 后台运行                                        │
│  - 监听文件变更                                          │
│  - 触发自动同步                                          │
│                                                          │
└──────────────────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────┐
│  Shutdown                                                │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  1. 停止 Watcher                                         │
│  2. 清理资源                                             │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

**全局状态：**

```python
# 索引进度追踪
class IndexProgress:
    is_running: bool
    total_files: int
    processed_files: int
    total_chunks: int
    current_file: str
    progress_percent: float
    status: str  # idle, running, completed, error
    message: str

index_progress = IndexProgress()  # 全局实例
```

**依赖：**
- `fastapi` - Web 框架
- `backend.config` - 配置
- `backend.embedder` - 向量化
- `backend.vectorstore` - 向量存储
- `backend.chunker` - 文本分块
- `backend.watcher` - 文件监听

---

### 4.7 ui/app.py - Streamlit Web UI

**职责：** 提供用户交互界面

**页面结构：**

```
┌─────────────────────────────────────────────────────────────┐
│  🔍 Obsidian 语义检索                                       │
│  基于 BGE-M3 向量模型的知识库搜索引擎                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  📂 向量库同步                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 📄 124 个文件 | 📝 10103 个文本块 | 🔄 实时监听: ✅  │   │
│  │                                                     │   │
│  │ [🔄 全量同步]                                       │   │
│  │                                                     │   │
│  │ ████████████████████░░░░░░░░░░  65% (81/124)      │   │
│  │ ⏳ 正在索引... 当前: xxx.md                         │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [  搜索你的知识库...                          ] [10 ▼]   │
│                                                             │
│  🌐 Web 安全                                                │
│  [SQL注入绕过WAF] [XSS窃取Cookie] [CSRF攻击] [SSRF内网]    │
│                                                             │
│  🎯 渗透测试                                                │
│  [内网横向移动] [权限提升方法] [凭据窃取] [免杀绕过]       │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  📊 5 个结果 | ⏱️ 2ms                                       │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 72% 匹配                        [打开笔记]          │   │
│  │ 📄 网络安全/sql_injection.md › 技术概述             │   │
│  │                                                     │   │
│  │ ## 技术概述                                         │   │
│  │ SQL 注入是 Web 安全领域最经典的漏洞...              │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Session State：**

```python
st.session_state = {
    "query": "",          # 搜索查询
}
```

**关键函数：**

| 函数 | 职责 |
|------|------|
| `search()` | 调用后端搜索 API |
| `get_stats()` | 获取向量库统计 |
| `get_progress()` | 获取索引进度 |
| `trigger_sync()` | 触发全量同步 |
| `get_obsidian_url()` | 生成 Obsidian URI |

**依赖：**
- `streamlit` - UI 框架
- `httpx` - HTTP 客户端
- `urllib.parse` - URL 编码

---

## 5. API 接口定义

### 5.1 接口列表

| 接口 | 方法 | 功能 | 请求体 | 响应体 |
|------|------|------|--------|--------|
| `/health` | GET | 健康检查 | - | HealthResponse |
| `/api/search` | POST | 语义检索 | SearchRequest | SearchResponse |
| `/api/index` | POST | 全量索引 | - | IndexResponse |
| `/api/index/progress` | GET | 索引进度 | - | ProgressResponse |
| `/api/stats` | GET | 统计信息 | - | StatsResponse |
| `/api/sync/pause` | POST | 暂停同步 | - | StatusResponse |
| `/api/sync/resume` | POST | 恢复同步 | - | StatusResponse |
| `/api/reset` | DELETE | 重置向量库 | - | StatusResponse |

### 5.2 数据模型

#### SearchRequest

```python
{
    "query": "SQL注入防御方法",      # 查询文本
    "top_k": 10,                    # 返回结果数
    "folder": "网络安全"            # 可选：文件夹过滤
}
```

#### SearchResponse

```python
{
    "results": [
        {
            "score": 0.72,                            # 相似度分数
            "content": "文本内容...",                  # 文本内容
            "source": "网络安全/sql_injection.md",     # 相对路径
            "heading": "技术概述",                     # 所属标题
            "file_path": "/Users/.../sql_injection.md", # 绝对路径
            "chunk_index": 0                           # 块索引
        }
    ],
    "total": 5,                      # 总结果数
    "took_ms": 23                    # 耗时(毫秒)
}
```

#### IndexResponse

```python
{
    "status": "success",             # success | error
    "message": "成功索引 124 个文件",
    "files_indexed": 124,            # 已索引文件数
    "chunks_created": 10103,         # 创建的文本块数
    "took_seconds": 45.2             # 耗时(秒)
}
```

#### ProgressResponse

```python
{
    "is_running": true,              # 是否正在运行
    "status": "running",             # idle | running | completed | error
    "total_files": 124,              # 总文件数
    "processed_files": 81,           # 已处理文件数
    "total_chunks": 6500,            # 已创建文本块数
    "current_file": "sql_injection.md", # 当前处理文件
    "progress_percent": 65.3,        # 进度百分比
    "elapsed_seconds": 30.5,         # 已耗时
    "message": "正在处理..."          # 状态消息
}
```

#### StatsResponse

```python
{
    "total_chunks": 10103,           # 总文本块数
    "total_files": 124,              # 总文件数
    "collection_name": "obsidian_notes",
    "embedding_dim": 1024,           # 向量维度
    "watcher_running": true,         # 监听器状态
    "last_events": [                 # 最近事件
        {
            "time": "2026-03-24T16:00:00",
            "path": "test.md",
            "type": "modified"
        }
    ]
}
```

### 5.3 调用示例

**搜索：**
```bash
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "SQL注入防御", "top_k": 5}'
```

**触发全量索引：**
```bash
curl -X POST http://localhost:8000/api/index
```

**获取进度：**
```bash
curl http://localhost:8000/api/index/progress
```

---

## 6. 模块调用关系

### 6.1 启动流程调用链

```
python -m backend.main
    │
    ├─► main.py: FastAPI 应用创建
    │       │
    │       └─► @app.on_event("startup")
    │               │
    │               ├─► config.py: Settings 加载
    │               │
    │               ├─► embedder.py: get_embedder()
    │               │       │
    │               │       └─► SentenceTransformer("BAAI/bge-m3")
    │               │
    │               ├─► watcher.py: init_watcher()
    │               │       │
    │               │       └─► VaultWatcher.start()
    │               │               │
    │               │               └─► Observer.start()
    │               │
    │               └─► uvicorn.run()
    │
    └─► 后台线程: watchdog Observer
            │
            └─► 文件事件 → handle_file_change()
                    │
                    ├─► chunker.py: MarkdownChunker.chunk_file()
                    │
                    ├─► embedder.py: Embedder.embed()
                    │
                    └─► vectorstore.py: VectorStore.upsert_documents()
```

### 6.2 搜索请求调用链

```
POST /api/search
    │
    ├─► main.py: search(request)
    │       │
    │       ├─► vectorstore.py: VectorStore.search()
    │       │       │
    │       │       ├─► embedder.py: Embedder.embed_single(query)
    │       │       │       │
    │       │       │       └─► model.encode(query)
    │       │       │
    │       │       └─► collection.query()
    │       │
    │       └─► 返回 SearchResponse
    │
    └─► ui/app.py: 显示结果
            │
            ├─► Markdown 渲染
            │
            └─► Obsidian URI 生成
```

### 6.3 全量索引调用链

```
POST /api/index
    │
    ├─► main.py: full_index()
    │       │
    │       ├─► 扫描 .md 文件
    │       │
    │       ├─► index_progress.start(total_files)
    │       │
    │       └─► for file in files:
    │               │
    │               ├─► chunker.py: MarkdownChunker.chunk_file()
    │               │
    │               ├─► embedder.py: Embedder.embed(chunks)
    │               │
    │               ├─► vectorstore.py: VectorStore.upsert_documents()
    │               │
    │               ├─► index_progress.update()
    │               │
    │               └─► watcher.mark_indexed()
    │
    └─► index_progress.complete()
```

### 6.4 实时同步调用链

```
Obsidian 文件变更
    │
    └─► watchdog.Observer
            │
            └─► DebouncedHandler.on_modified()
                    │
                    ├─► 防抖等待 (2秒)
                    │
                    └─► callback(path, "modified")
                            │
                            ├─► chunker.py: MarkdownChunker.chunk_file()
                            │
                            ├─► embedder.py: Embedder.embed()
                            │
                            └─► vectorstore.py: VectorStore.upsert_documents()
```

---

## 7. 配置说明

### 7.1 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `OBSIDIAN_VAULT_PATH` | `/Users/liuwj77/StorageObsidian` | Obsidian Vault 路径 |
| `CHROMA_PERSIST_DIR` | `./data/chroma` | ChromaDB 存储路径 |
| `EMBEDDING_MODEL` | `BAAI/bge-m3` | Embedding 模型 |
| `EMBEDDING_DEVICE` | `auto` | 计算设备 (auto/cpu/cuda/mps) |
| `CHUNK_SIZE` | `512` | 文本块大小 |
| `CHUNK_OVERLAP` | `50` | 块重叠大小 |
| `WATCHER_DEBOUNCE_SECONDS` | `2.0` | 文件监听防抖时间 |

### 7.2 配置文件

创建 `.env` 文件：
```bash
OBSIDIAN_VAULT_PATH=/path/to/your/vault
CHUNK_SIZE=512
CHUNK_OVERLAP=50
```

---

## 8. 部署说明

### 8.1 环境准备

```bash
# 创建 conda 环境
conda create -n obsidian_rag python=3.10 -y
conda activate obsidian_rag

# 安装依赖
cd /Users/liuwj77/temp_obsidian_rag
pip install -r requirements.txt
```

### 8.2 启动服务

```bash
# 终端 1: 后端服务
conda activate obsidian_rag
cd /Users/liuwj77/temp_obsidian_rag
python -m backend.main

# 终端 2: Web UI
conda activate obsidian_rag
cd /Users/liuwj77/temp_obsidian_rag
streamlit run ui/app.py --server.headless true
```

### 8.3 访问地址

| 服务 | 地址 |
|------|------|
| Web UI | http://localhost:8501 |
| API 文档 | http://localhost:8000/docs |
| 健康检查 | http://localhost:8000/health |

### 8.4 首次使用

1. 首次启动会自动下载 BGE-M3 模型（约 2GB）
2. 访问 Web UI，点击「全量同步」按钮
3. 等待索引完成后即可搜索

---

## 9. 性能指标

| 指标 | 数值 |
|------|------|
| **向量维度** | 1024 |
| **检索延迟** | ~100ms |
| **索引速度** | ~50 文件/分钟 |
| **内存占用** | ~3GB (模型 + 向量库) |
| **向量库大小** | ~138MB (10,103 chunks) |

---

## 10. 版本历史

| 版本 | 说明 |
|------|------|
| v0.3.7 | fix: 修复UI显示问题 |
| v0.3.6 | feat: 添加实时进度条 |
| v0.3.5 | feat: 添加全量同步按钮 |
| v0.3.4 | fix: 修复示例按钮跳转 |
| v0.3.3 | fix: 移除未使用导入 |
| v0.3.2 | fix: 正确渲染Markdown |
| v0.3.1 | style: GitHub风格UI |
| v0.3.0 | feat: Obsidian跳转功能 |
| v0.2.0 | refactor: 切换本地conda |
| v0.1.0 | feat: 项目初始化 |