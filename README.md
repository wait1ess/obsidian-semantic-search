# 🔍 Obsidian 语义检索系统

基于 **BGE-M3** 向量模型的 Obsidian Vault 本地语义检索系统。

[![GitHub](https://img.shields.io/badge/GitHub-wait1ess%2Fobsidian--semantic--search-blue?logo=github)](https://github.com/wait1ess/obsidian-semantic-search)
[![Python](https://img.shields.io/badge/Python-3.10-green?logo=python)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## ✨ 特性

- **🎯 高精度语义检索** — 基于 BGE-M3 (MTEB Top 排名) 向量模型
- **🌐 中英混合支持** — 优秀的多语言检索能力
- **📝 Markdown 渲染** — 搜索结果保持原始格式
- **🔗 Obsidian 跳转** — 点击直接在 Obsidian 中打开笔记
- **👁️ 实时同步** — 自动监听文件变更并更新索引
- **🎨 GitHub 风格 UI** — 简洁美观的深色主题

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/wait1ess/obsidian-semantic-search.git
cd obsidian-semantic-search
```

### 2. 创建 Conda 环境

```bash
conda create -n obsidian_rag python=3.10 -y
conda activate obsidian_rag
pip install -r requirements.txt
```

### 3. 配置 Vault 路径

编辑 `backend/config.py`，设置你的 Obsidian Vault 路径：

```python
obsidian_vault_path: str = "/path/to/your/obsidian/vault"
```

### 4. 启动服务

```bash
# 终端 1: 启动后端
python -m backend.main

# 终端 2: 启动 Web UI
streamlit run ui/app.py --server.headless true
```

### 5. 访问

- **Web UI**: http://localhost:8501
- **API 文档**: http://localhost:8000/docs

## 📖 使用

1. 首次启动会自动下载 BGE-M3 模型（约 2GB）
2. 点击「🔄 全量同步」建立索引（后台异步执行，可实时查看进度）
3. 搜索框输入查询，获取语义相关的笔记片段
4. 点击路径或「打开笔记」按钮在 Obsidian 中查看原文

> **注意**：全量同步在后台线程执行，索引期间搜索功能仍可正常使用。

## 🛠️ 技术栈

| 组件 | 技术 |
|------|------|
| **后端** | FastAPI + Uvicorn |
| **向量模型** | BAAI/bge-m3 |
| **向量数据库** | ChromaDB |
| **文件监听** | watchdog |
| **Web UI** | Streamlit |

## 📊 性能

| 指标 | 数值 |
|------|------|
| 向量维度 | 1024 |
| 检索延迟 | ~100ms |
| 内存占用 | ~3GB |

## 📁 项目结构

```
obsidian-semantic-search/
├── backend/              # 后端服务
│   ├── main.py          # FastAPI 入口
│   ├── embedder.py      # Embedding 封装
│   ├── vectorstore.py   # ChromaDB 封装
│   ├── chunker.py       # Markdown 分块
│   ├── watcher.py       # 文件监听
│   └── config.py        # 配置管理
├── ui/                   # Web UI
│   └── app.py           # Streamlit 应用
├── data/chroma/          # 向量库数据
├── scripts/              # 辅助脚本
├── requirements.txt      # Python 依赖
└── README.md
```

## 🔧 API 接口

| 接口 | 方法 | 功能 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/api/search` | POST | 语义检索 |
| `/api/index` | POST | 全量索引（异步后台执行） |
| `/api/index/progress` | GET | 获取索引进度 |
| `/api/stats` | GET | 统计信息 |
| `/api/sync/pause` | POST | 暂停文件监听 |
| `/api/sync/resume` | POST | 恢复文件监听 |
| `/api/reset` | DELETE | 重置向量库 |

### 搜索示例

```bash
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "SQL注入防御方法", "top_k": 5}'
```

## 📝 配置选项

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `OBSIDIAN_VAULT_PATH` | - | Obsidian Vault 路径 |
| `CHUNK_SIZE` | 512 | 文本块大小 |
| `CHUNK_OVERLAP` | 50 | 块重叠大小 |
| `EMBEDDING_BATCH_SIZE` | 8 | 批处理大小 |

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

[MIT License](LICENSE)