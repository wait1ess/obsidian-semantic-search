# SPEC.md - Obsidian 语义检索系统

## 项目目标
为 Obsidian Vault 构建本地语义检索系统，支持实时同步、Web UI 搜索、Docker 部署。

## 项目信息
- **项目名称**: obsidian-rag
- **项目路径**: /Users/liuwj77/temp_obsidian_rag
- **Vault 路径**: /Users/liuwj77/StorageObsidian
- **部署方式**: Docker Compose（本地）
- **Embedding 模型**: BAAI/bge-m3

## 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Compose                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │  Web UI     │───▶│  Backend    │───▶│  ChromaDB   │     │
│  │  (Streamlit)│    │  (FastAPI)  │    │  (Vector)   │     │
│  └─────────────┘    └─────────────┘    └─────────────┘     │
│         │                   │                               │
│         │            ┌──────┴──────┐                       │
│         │            │             │                       │
│         │       ┌────┴────┐  ┌─────┴─────┐                │
│         │       │ Watcher │  │ Embedder  │                │
│         │       │(实时监听)│  │ (BGE-M3)  │                │
│         │       └────┬────┘  └─────┬─────┘                │
│         │            │             │                       │
└─────────┼────────────┼─────────────┼───────────────────────┘
          │            │             │
          │            ▼             │
          │   /Users/liuwj77/        │
          │   StorageObsidian        │
          │   (Obsidian Vault)       │
          │                          │
          └──────────────────────────┘
```

## 目录结构

```
temp_obsidian_rag/
├── SPEC.md                 # 本文档
├── docker-compose.yml      # Docker 编排
├── Dockerfile.backend      # 后端镜像
├── Dockerfile.ui           # Web UI 镜像
├── requirements.txt        # Python 依赖
├── backend/
│   ├── main.py            # FastAPI 主入口
│   ├── embedder.py        # BGE-M3 Embedding 封装
│   ├── vectorstore.py     # ChromaDB 封装
│   ├── watcher.py         # 文件监听服务
│   ├── chunker.py         # Markdown 分块
│   └── config.py          # 配置管理
├── ui/
│   ├── app.py             # Streamlit 应用
│   └── components/        # UI 组件
├── data/
│   └── chroma/             # ChromaDB 持久化（.gitignore）
├── tests/
│   └── test_*.py          # 单元测试
├── scripts/
│   ├── init_index.py      # 全量索引脚本
│   └── reset_db.py        # 重置向量库
└── .gitignore
```

## 接口定义

### Backend API (FastAPI)

| 接口 | 方法 | 功能 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/api/search` | POST | 语义检索 |
| `/api/index` | POST | 全量索引 |
| `/api/index/file` | POST | 单文件索引 |
| `/api/stats` | GET | 向量库统计 |
| `/api/sync/status` | GET | 同步状态 |

### 请求/响应格式

```python
# POST /api/search
{
    "query": "SQL注入的防御方法",
    "top_k": 10,
    "filter": {  # 可选
        "folder": "网络安全知识库（理论知识）"
    }
}

# Response
{
    "results": [
        {
            "score": 0.89,
            "content": "...",
            "source": "网络安全知识库（理论知识）/SQL注入.md",
            "chunk_index": 2
        }
    ],
    "total": 15,
    "took_ms": 23
}
```

## 功能模块

### 1. Embedding 服务 (embedder.py)
- 模型：BAAI/bge-m3
- 支持批量处理
- 缓存机制（避免重复计算）
- 自动 GPU/MPS 加速（Mac M系列）

### 2. 向量存储 (vectorstore.py)
- ChromaDB 持久化存储
- 余弦相似度检索
- 增量更新支持
- 文件级别去重

### 3. 文件监听 (watcher.py)
- watchdog 实时监听
- 自动检测 .md 文件变更
- 防抖处理（避免频繁更新）
- 删除检测

### 4. 文本分块 (chunker.py)
- Markdown 结构感知
- 支持标题层级分割
- 可配置块大小（默认 512 tokens）
- 重叠窗口（默认 50 tokens）

### 5. Web UI (ui/app.py)
- 搜索界面
- 结果高亮
- 文件预览跳转
- 索引状态显示
- 深色主题（适配 Obsidian）

## 部署配置

### Docker Compose 服务

| 服务 | 端口 | 说明 |
|------|------|------|
| backend | 8000 | FastAPI 后端 |
| ui | 8501 | Streamlit Web UI |
| chroma | 8001 | ChromaDB（可选独立服务） |

### 环境变量

```bash
OBSIDIAN_VAULT_PATH=/Users/liuwj77/StorageObsidian
CHROMA_PERSIST_DIR=/app/data/chroma
EMBEDDING_MODEL=BAAI/bge-m3
CHUNK_SIZE=512
CHUNK_OVERLAP=50
```

## 验收标准

1. **功能验收**
   - [ ] 全量索引成功
   - [ ] 语义检索返回相关结果
   - [ ] 实时更新正常工作
   - [ ] Web UI 可正常访问和搜索

2. **性能验收**
   - [ ] 检索延迟 < 500ms（1000 chunks）
   - [ ] 索引速度 > 50 files/min

3. **质量验收**
   - [ ] 代码有类型注解
   - [ ] 核心逻辑有单元测试
   - [ ] 错误处理完善

## 清理规则

- `data/chroma/` 不纳入版本控制
- `__pycache__/` `.pyc` 忽略
- `.env` 文件忽略
- 模型缓存目录忽略

## 版本规划

- v0.1.0: 基础检索功能
- v0.2.0: 实时同步
- v0.3.0: Web UI 优化
- v1.0.0: 正式发布