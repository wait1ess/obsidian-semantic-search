"""Streamlit Web UI - Obsidian 语义检索"""
import streamlit as st
import httpx
import urllib.parse
import time

# 配置
BACKEND_URL = "http://127.0.0.1:8000"
OBSIDIAN_VAULT = "StorageObsidian"

st.set_page_config(
    page_title="Obsidian 语义检索",
    page_icon="🔍",
    layout="wide"
)

# 样式 - GitHub Dark 简洁风格
st.markdown("""
<style>
    /* 全局 */
    .stApp { background-color: #0d1117; color: #c9d1d9; }
    #MainMenu, footer, header {visibility: hidden;}

    /* 标题区 - 紧凑 */
    .main-title { font-size: 1.75rem; font-weight: 600; color: #f0f6fc; margin-bottom: 0.25rem; }
    .main-title span { color: #58a6ff; }
    .subtitle { color: #8b949e; font-size: 0.95rem; margin-bottom: 1rem; }

    /* 搜索框 - 更大更清晰 */
    .stTextInput > div > div > input {
        background-color: #0d1117 !important;
        border: 1px solid #30363d !important;
        border-radius: 6px !important;
        font-size: 1.05rem !important;
        padding: 0.6rem 0.85rem !important;
        color: #c9d1d9 !important;
    }
    .stTextInput > div > div > input:focus { border-color: #58a6ff !important; }
    .stTextInput > div > div > input::placeholder { color: #484f58 !important; }

    /* 示例分类 - 简化 */
    .example-category { color: #8b949e; font-size: 0.9rem; margin: 0.75rem 0 0.4rem 0; }

    /* 同步区 - 去掉色块背景 */
    .sync-section { margin: 0.75rem 0; }
    .sync-title { color: #f0f6fc; font-weight: 600; font-size: 1rem; margin-bottom: 0.5rem; }
    .sync-info { color: #8b949e; font-size: 0.9rem; margin: 0.3rem 0; }

    /* 统计栏 - 去掉背景色块 */
    .stats-bar {
        color: #8b949e;
        font-size: 0.9rem;
        padding: 0.5rem 0;
        border-bottom: 1px solid #21262d;
        margin-bottom: 0.75rem;
    }
    .stats-bar strong { color: #c9d1d9; }

    /* 结果卡片 - 简化，去掉背景色块 */
    .result-card {
        border-bottom: 1px solid #21262d;
        padding: 0.75rem 0;
        margin-bottom: 0.5rem;
    }

    /* 分数徽章 - 更低调 */
    .score-badge {
        display: inline-block;
        padding: 0.15rem 0.5rem;
        border-radius: 4px;
        font-size: 0.85rem;
        font-weight: 500;
    }
    .score-high { color: #3fb950; }
    .score-mid { color: #d29922; }
    .score-low { color: #8b949e; }

    /* 路径区 - 更紧凑 */
    .path-area { padding: 0.4rem 0; margin-bottom: 0.5rem; }
    .path-link { color: #58a6ff; text-decoration: none; font-size: 1rem; font-weight: 500; }
    .heading-tag { color: #7ee787; font-size: 0.95rem; margin-left: 0.3rem; }
    .full-path { color: #6e7681; font-size: 0.8rem; margin-top: 0.2rem; font-family: monospace; }

    /* 按钮样式 */
    .open-btn {
        background-color: #21262d;
        color: #c9d1d9;
        border: 1px solid #30363d;
        padding: 0.3rem 0.7rem;
        border-radius: 6px;
        font-size: 0.85rem;
        cursor: pointer;
    }
    .open-btn:hover { background-color: #30363d; }

    /* Markdown内容 - 放大字体 */
    .md-content { color: #c9d1d9; line-height: 1.65; font-size: 1rem; }
    .md-content h1, .md-content h2, .md-content h3 { color: #f0f6fc; font-weight: 600; margin-top: 0.5rem; }
    .md-content code { background-color: #343942; padding: 0.15rem 0.35rem; border-radius: 4px; font-size: 0.9em; }
    .md-content pre { background-color: #161b22; border: 1px solid #21262d; border-radius: 6px; padding: 0.75rem; overflow-x: auto; }
    .md-content pre code { background: none; padding: 0; }
    .md-content blockquote { border-left: 3px solid #3b82f6; padding: 0.3rem 0.75rem; color: #8b949e; margin: 0.5rem 0; }
    .md-content table { border-collapse: collapse; margin: 0.5rem 0; }
    .md-content th, .md-content td { padding: 0.4rem 0.6rem; border: 1px solid #30363d; }
    .md-content th { background-color: #161b22; }

    /* Streamlit按钮 */
    .stButton > button {
        background-color: #21262d !important;
        color: #c9d1d9 !important;
        border: 1px solid #30363d !important;
        border-radius: 6px !important;
    }
    .stButton > button:hover { background-color: #30363d !important; }
    .stButton > button[kind="primary"] {
        background-color: #238636 !important;
        border-color: #238636 !important;
        color: #ffffff !important;
    }
</style>
""", unsafe_allow_html=True)


def search(query: str, top_k: int = 10):
    try:
        r = httpx.post(f"{BACKEND_URL}/api/search", json={"query": query.strip(), "top_k": top_k}, timeout=30.0)
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def get_stats():
    try:
        r = httpx.get(f"{BACKEND_URL}/api/stats", timeout=5.0)
        return r.json()
    except:
        return None


def get_progress():
    try:
        r = httpx.get(f"{BACKEND_URL}/api/index/progress", timeout=5.0)
        return r.json()
    except:
        return {"is_running": False}


def trigger_sync():
    """触发全量同步（异步，立即返回）"""
    try:
        r = httpx.post(f"{BACKEND_URL}/api/index", timeout=10.0)
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def get_obsidian_url(file_path: str):
    if file_path.startswith("/Users/"):
        parts = file_path.split("/StorageObsidian/")
        relative_path = parts[1] if len(parts) > 1 else file_path.split("/")[-1]
    else:
        relative_path = file_path
    return f"obsidian://open?vault={OBSIDIAN_VAULT}&file={urllib.parse.quote(relative_path)}"


# ============== Session State ==============
if "query" not in st.session_state:
    st.session_state.query = ""

# ============== UI ==============

# 标题 - 简洁
st.markdown('<h1 class="main-title">🔍 <span>Obsidian</span> 语义检索</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">基于 BGE-M3 的知识库搜索引擎</p>', unsafe_allow_html=True)

# ===== 同步区域 - 简化 =====
st.markdown('<div class="sync-section"><div class="sync-title">📂 向量库同步</div>', unsafe_allow_html=True)

stats = get_stats()
if stats:
    st.markdown(f"""
    <div class="stats-bar">
        📄 <strong>{stats['total_files']}</strong> 个文件
        &nbsp;|&nbsp; 📝 <strong>{stats['total_chunks']}</strong> 个文本块
        &nbsp;|&nbsp; 🔄 实时监听: {'✅' if stats.get('watcher_running') else '⏹️'}
    </div>
    """, unsafe_allow_html=True)

# 检查进度
progress = get_progress()

if progress.get("is_running"):
    # 显示进度
    pct = progress.get("progress_percent", 0)
    processed = progress.get("processed_files", 0)
    total = progress.get("total_files", 1)
    current = progress.get("current_file", "")
    chunks = progress.get("total_chunks", 0)
    elapsed = progress.get("elapsed_seconds", 0)

    st.progress(int(pct) / 100)
    st.markdown(f'''
    <div class="sync-info">
        {pct}% ({processed}/{total}) · {chunks} 文本块 · {elapsed:.0f}秒<br>
        当前: {current}
    </div>
    ''', unsafe_allow_html=True)
    time.sleep(1)
    st.rerun()

elif progress.get("status") == "completed":
    # 显示完成状态
    msg = progress.get("message", "")
    st.success(f"✅ {msg}")
    st.markdown('</div>', unsafe_allow_html=True)

else:
    # 同步按钮
    if st.button("🔄 全量同步", type="primary", use_container_width=True):
        with st.spinner("触发同步..."):
            result = trigger_sync()
        if result.get("status") == "error":
            st.error(f"❌ {result.get('message', '未知错误')}")
        else:
            st.success("🚀 已启动")
            time.sleep(0.5)
            st.rerun()

st.markdown('</div>', unsafe_allow_html=True)

# ===== 搜索框 =====
col_search, col_k = st.columns([5, 1])
with col_search:
    query = st.text_input(
        "搜索",
        value=st.session_state.query,
        placeholder="搜索你的知识库...",
        label_visibility="collapsed"
    )
with col_k:
    top_k = st.selectbox("结果", [5, 10, 15, 20], index=1, label_visibility="collapsed")

# ===== 示例 =====
if not query:
    st.markdown('<div class="example-category">Web 安全</div>', unsafe_allow_html=True)
    cols = st.columns(4)
    for i, ex in enumerate(["SQL注入绕过WAF", "XSS窃取Cookie", "CSRF攻击原理", "SSRF内网探测"]):
        if cols[i].button(ex, key=f"web_{i}", use_container_width=True):
            st.session_state.query = ex
            st.rerun()

    st.markdown('<div class="example-category">渗透测试</div>', unsafe_allow_html=True)
    cols = st.columns(4)
    for i, ex in enumerate(["内网横向移动", "权限提升方法", "凭据窃取技术", "免杀绕过技巧"]):
        if cols[i].button(ex, key=f"pentest_{i}", use_container_width=True):
            st.session_state.query = ex
            st.rerun()

    st.markdown('<div class="example-category">云安全</div>', unsafe_allow_html=True)
    cols = st.columns(4)
    for i, ex in enumerate(["Docker逃逸方法", "Kubernetes攻击", "AWS IAM提权", "容器安全配置"]):
        if cols[i].button(ex, key=f"cloud_{i}", use_container_width=True):
            st.session_state.query = ex
            st.rerun()

    st.markdown('<div class="example-category">密码学</div>', unsafe_allow_html=True)
    cols = st.columns(4)
    for i, ex in enumerate(["RSA攻击方法", "AES加密模式", "哈希碰撞攻击", "证书伪造技术"]):
        if cols[i].button(ex, key=f"crypto_{i}", use_container_width=True):
            st.session_state.query = ex
            st.rerun()

# ===== 搜索结果 =====
if query:
    st.session_state.query = ""

    with st.spinner("搜索中..."):
        result = search(query, top_k)

    if "error" in result:
        st.error(f"❌ {result['error']}")
    elif result.get("results"):
        st.markdown(f'<div class="stats-bar">📊 {result["total"]} 个结果 · {result["took_ms"]}ms</div>', unsafe_allow_html=True)

        for hit in result["results"]:
            score = hit.get("score", 0)
            source = hit.get("source", "")
            heading = hit.get("heading", "")
            content = hit.get("content", "")

            if source.startswith("/Users/"):
                parts = source.split("/StorageObsidian/")
                relative_path = parts[1] if len(parts) > 1 else source.split("/")[-1]
            else:
                relative_path = source

            obsidian_url = get_obsidian_url(source)
            score_class = "score-high" if score >= 0.7 else ("score-mid" if score >= 0.5 else "score-low")

            # 简化的结果卡片
            st.markdown(f'''
            <div class="result-card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.3rem;">
                    <span class="score-badge {score_class}">{score:.0%}</span>
                    <a href="{obsidian_url}" target="_blank" style="text-decoration: none;">
                        <button class="open-btn">打开笔记</button>
                    </a>
                </div>
                <div class="path-area">
                    <a href="{obsidian_url}" class="path-link">{relative_path}</a>
                    {f'<span class="heading-tag">› {heading}</span>' if heading else ''}
                </div>
            ''', unsafe_allow_html=True)

            if len(content) > 600:
                content = content[:600] + "\n\n*...查看完整内容请打开笔记*"

            st.markdown(f'<div class="md-content">{content}</div></div>', unsafe_allow_html=True)
    else:
        st.info("🔍 未找到相关结果")