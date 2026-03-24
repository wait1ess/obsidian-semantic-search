# Obsidian 语义检索系统

基于 BGE-M3 向量模型的 Obsidian Vault 本地语义检索系统。

## 功能特性

- **BGE-M3 向量化** — MTEB 高排名多语言模型
- **ChromaDB 存储** — 轻量本地向量库
- **实时同步** — watchdog 监听自动更新
- **Web UI** — Streamlit 搜索界面
- **MPS 加速** — Apple Silicon 原生加速

## 快速开始

### 1. 创建 Conda 环境

```bash
conda create -n obsidian_rag python=3.10 -y
conda activate obsidian_rag
pip install -r requirements.txt
```

### 2. 启动后端

```bash
cd /Users/liuwj77/temp_obsidian_rag
python -m backend.main
```

后端地址：http://localhost:8000

### 3. 启动 Web UI（另一个终端）

```bash
conda activate obsidian_rag
cd /Users/liuwj77/temp_obsidian_rag
streamlit run ui/app.py
```

Web UI：http://localhost:8501

### 4. 全量索引

首次使用需要触发全量索引：

```bash
curl -X POST http://localhost:8000/api/index
```

或在 Web UI 侧边栏点击「全量索引」按钮。

## 配置

编辑 `backend/config.py` 或设置环境变量：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `OBSIDIAN_VAULT_PATH` | `/Users/liuwj77/StorageObsidian` | Vault 路径 |
| `CHROMA_PERSIST_DIR` | `./data/chroma` | 向量库路径 |
| `CHUNK_SIZE` | `512` | 文本块大小 |
| `CHUNK_OVERLAP` | `50` | 重叠 token 数 |

## API 接口

| 接口 | 方法 | 功能 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/api/search` | POST | 语义检索 |
| `/api/index` | POST | 全量索引 |
| `/api/stats` | GET | 统计信息 |

## 项目结构

```
temp_obsidian_rag/
├── backend/              # 后端服务
│   ├── main.py          # FastAPI 入口
│   ├── embedder.py      # Embedding 服务
│   ├── vectorstore.py   # 向量存储
│   ├── chunker.py       # 文本分块
│   ├── watcher.py       # 文件监听
│   └── config.py        # 配置管理
├── ui/                   # Web UI
│   └── app.py           # Streamlit 应用
├── data/chroma/          # 向量库数据
├── scripts/              # 辅助脚本
└── requirements.txt      # Python 依赖
```

## 使用示例

```python
import httpx

# 搜索
response = httpx.post(
    "http://localhost:8000/api/search",
    json={"query": "SQL注入的防御方法", "top_k": 5}
)
results = response.json()

for hit in results["results"]:
    print(f"[{hit['score']:.2%}] {hit['source']}")
    print(f"  {hit['content'][:100]}...")
```