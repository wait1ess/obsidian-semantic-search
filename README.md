# Obsidian RAG 使用指南

## 快速开始

### 1. 启动服务

```bash
cd /Users/liuwj77/temp_obsidian_rag

# 首次构建
docker-compose build

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

### 2. 访问服务

- **Web UI**: http://localhost:8501
- **API 文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health

### 3. 全量索引

首次使用需要触发全量索引：

```bash
# 通过 API
curl -X POST http://localhost:8000/api/index

# 或在 Web UI 侧边栏点击"全量索引"
```

### 4. 搜索测试

```bash
# API 调用
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "SQL注入的防御方法", "top_k": 5}'

# 或使用 Web UI 搜索
```

## 常用命令

```bash
# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 查看后端日志
docker-compose logs -f backend

# 查看UI日志
docker-compose logs -f ui

# 进入后端容器
docker-compose exec backend bash

# 重新构建
docker-compose build --no-cache
```

## 配置修改

编辑 `docker-compose.yml` 中的环境变量：

```yaml
environment:
  - CHUNK_SIZE=512        # 文本块大小
  - CHUNK_OVERLAP=50      # 重叠 token 数
  - WATCHER_DEBOUNCE_SECONDS=2.0  # 防抖时间
```

修改后需重启服务：

```bash
docker-compose down
docker-compose up -d
```

## 本地开发（非 Docker）

```bash
# 创建 conda 环境
conda create -n obsidian_rag python=3.10 -y
conda activate obsidian_rag

# 安装依赖
pip install -r requirements.txt

# 启动后端
cd /Users/liuwj77/temp_obsidian_rag
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# 另一个终端启动 UI
cd /Users/liuwj77/temp_obsidian_rag
streamlit run ui/app.py
```

## 项目结构

```
temp_obsidian_rag/
├── docker-compose.yml    # Docker 编排
├── Dockerfile.backend    # 后端镜像
├── Dockerfile.ui         # UI 镜像
├── requirements.txt      # Python 依赖
├── backend/              # 后端代码
│   ├── main.py          # FastAPI 入口
│   ├── embedder.py      # Embedding 服务
│   ├── vectorstore.py   # 向量存储
│   ├── chunker.py       # 文本分块
│   ├── watcher.py       # 文件监听
│   └── config.py        # 配置管理
├── ui/                   # Web UI
│   └── app.py           # Streamlit 应用
├── data/                 # 数据目录
│   └── chroma/          # ChromaDB 存储
└── scripts/              # 辅助脚本
    ├── init_index.py    # 全量索引
    └── reset_db.py      # 重置向量库
```

## API 接口

| 接口 | 方法 | 功能 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/api/search` | POST | 语义检索 |
| `/api/index` | POST | 全量索引 |
| `/api/stats` | GET | 统计信息 |
| `/api/sync/pause` | POST | 暂停同步 |
| `/api/sync/resume` | POST | 恢复同步 |
| `/api/reset` | DELETE | 重置向量库 |

## 注意事项

1. **首次启动较慢** - 需要下载 BGE-M3 模型（约 2GB）
2. **模型缓存** - 模型缓存在 `~/.cache/huggingface`
3. **实时同步** - 服务启动后自动监听 Vault 变更
4. **内存占用** - 建议至少 8GB 内存