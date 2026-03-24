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
    layout="wide",
    initial_sidebar_state="collapsed"
)

# GitHub 风格样式
st.markdown("""
<style>
    .stApp { background-color: #0d1117; color: #c9d1d9; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif; }
    #MainMenu, footer, header {visibility: hidden;}
    .stDeployButton {display: none;}
    
    .main-title { font-size: 2rem; font-weight: 600; color: #f0f6fc; text-align: center; padding: 1.5rem 0 0.5rem 0; }
    .main-title span { color: #58a6ff; }
    .subtitle { color: #8b949e; text-align: center; font-size: 0.95rem; padding-bottom: 1rem; border-bottom: 1px solid #21262d; }
    
    .stTextInput > div > div > input { background-color: #0d1117 !important; border: 1px solid #30363d !important; border-radius: 6px !important; font-size: 1rem !important; padding: 0.75rem 1rem !important; color: #c9d1d9 !important; }
    .stTextInput > div > div > input:focus { border-color: #58a6ff !important; box-shadow: 0 0 0 3px rgba(88, 166, 255, 0.3) !important; background-color: #161b22 !important; }
    .stTextInput > div > div > input::placeholder { color: #484f58 !important; }
    
    .example-category { color: #8b949e; font-size: 0.85rem; margin: 1rem 0 0.5rem 0; padding-left: 0.5rem; border-left: 2px solid #30363d; }
    
    .stats-bar { background-color: #161b22; border: 1px solid #21262d; border-radius: 6px; padding: 0.75rem 1rem; margin: 1rem 0; display: flex; gap: 1.5rem; color: #8b949e; font-size: 0.9rem; }
    .stats-bar strong { color: #f0f6fc; }
    
    .sync-section { background-color: #161b22; border: 1px solid #21262d; border-radius: 6px; padding: 1rem; margin: 1rem 0; }
    .sync-title { color: #f0f6fc; font-weight: 600; margin-bottom: 0.75rem; font-size: 1rem; }
    .sync-info { color: #8b949e; font-size: 0.85rem; margin-bottom: 0.75rem; }
    
    .result-card { background-color: #161b22; border: 1px solid #21262d; border-radius: 6px; padding: 1.25rem 1.5rem; margin-bottom: 1rem; }
    .result-card:hover { border-color: #30363d; }
    
    .score-badge { display: inline-block; padding: 0.25rem 0.75rem; border-radius: 2em; font-size: 0.85rem; font-weight: 500; }
    .score-high { background-color: #238636; color: #ffffff; }
    .score-mid { background-color: #9e6a03; color: #ffffff; }
    .score-low { background-color: #30363d; color: #8b949e; }
    
    .path-area { padding: 0.75rem 0; border-bottom: 1px solid #21262d; margin-bottom: 1rem; }
    .path-link { color: #58a6ff; text-decoration: none; font-size: 1.05rem; font-weight: 500; }
    .path-link:hover { text-decoration: underline; }
    .heading-tag { color: #7ee787; font-size: 1rem; margin-left: 0.5rem; }
    .full-path { color: #6e7681; font-size: 0.85rem; margin-top: 0.35rem; font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace; }
    
    .action-btn { display: inline-flex; align-items: center; gap: 0.4rem; background-color: #21262d; border: 1px solid #30363d; color: #c9d1d9; padding: 0.4rem 0.85rem; border-radius: 6px; font-size: 0.85rem; text-decoration: none; }
    .action-btn:hover { background-color: #30363d; color: #f0f6fc; }
    .action-btn-primary { background-color: #238636; border-color: #238636; color: #ffffff; }
    .action-btn-primary:hover { background-color: #2ea043; }
    
    .md-content { color: #c9d1d9; line-height: 1.7; font-size: 0.92rem; }
    .md-content h1 { color: #f0f6fc; font-size: 1.4rem; margin: 1rem 0 0.5rem 0; font-weight: 600; border-bottom: 1px solid #21262d; padding-bottom: 0.3rem; }
    .md-content h2 { color: #f0f6fc; font-size: 1.2rem; margin: 0.9rem 0 0.5rem 0; font-weight: 600; }
    .md-content h3 { color: #f0f6fc; font-size: 1.05rem; margin: 0.8rem 0 0.4rem 0; font-weight: 600; }
    .md-content table { width: 100%; border-collapse: collapse; margin: 0.75rem 0; }
    .md-content th { background-color: #21262d; color: #f0f6fc; padding: 0.6rem 0.8rem; border: 1px solid #30363d; text-align: left; font-weight: 600; }
    .md-content td { padding: 0.6rem 0.8rem; border: 1px solid #30363d; color: #c9d1d9; }
    .md-content code { background-color: #343942; color: #f0f6fc; padding: 0.2rem 0.45rem; border-radius: 6px; font-size: 0.88em; font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace; }
    .md-content pre { background-color: #161b22; border: 1px solid #21262d; border-radius: 6px; padding: 1rem; overflow-x: auto; margin: 0.75rem 0; }
    .md-content pre code { background: none; padding: 0; border-radius: 0; font-size: 0.85rem; color: #c9d1d9; }
    .md-content blockquote { border-left: 4px solid #3b82f6; padding: 0.5rem 1rem; margin: 0.75rem 0; color: #8b949e; background-color: #0d1117; border-radius: 0 6px 6px 0; }
    .md-content ul, .md-content ol { padding-left: 1.5rem; margin: 0.5rem 0; }
    .md-content a { color: #58a6ff; text-decoration: none; }
    .md-content strong { color: #f0f6fc; font-weight: 600; }
    .md-content hr { border: none; border-top: 1px solid #21262d; margin: 1rem 0; }
    .md-content p { margin: 0.5rem 0; }
    
    .stSelectbox > div > div { background-color: #21262d; border: 1px solid #30363d; border-radius: 6px; }
</style>
""", unsafe_allow_html=True)


def search(query: str, top_k: int = 10):
    if not query or not query.strip():
        return {"error": "请输入查询内容"}
    try:
        response = httpx.post(f"{BACKEND_URL}/api/search", json={"query": query.strip(), "top_k": top_k}, timeout=30.0)
        response.raise_for_status()
        return response.json()
    except httpx.ConnectError:
        return {"error": "无法连接后端服务"}
    except httpx.TimeoutException:
        return {"error": "搜索超时"}
    except:
        return {"error": "搜索失败"}


def get_obsidian_url(file_path: str):
    if file_path.startswith("/Users/"):
        parts = file_path.split("/StorageObsidian/")
        relative_path = parts[1] if len(parts) > 1 else file_path.split("/")[-1]
    else:
        relative_path = file_path
    return f"obsidian://open?vault={OBSIDIAN_VAULT}&file={urllib.parse.quote(relative_path)}"


def trigger_sync():
    """触发全量同步"""
    try:
        response = httpx.post(f"{BACKEND_URL}/api/index", timeout=600.0)
        return response.json()
    except Exception as e:
        return {"error": str(e)}


def get_progress():
    """获取索引进度"""
    try:
        response = httpx.get(f"{BACKEND_URL}/api/index/progress", timeout=5.0)
        return response.json()
    except:
        return {"is_running": False}


def get_stats():
    """获取统计信息"""
    try:
        response = httpx.get(f"{BACKEND_URL}/api/stats", timeout=5.0)
        return response.json()
    except:
        return None


# ============== 初始化 Session State ==============
if "search_query" not in st.session_state:
    st.session_state["search_query"] = ""
if "syncing" not in st.session_state:
    st.session_state["syncing"] = False

# ============== Main UI ==============

# 标题
st.markdown('<h1 class="main-title">🔍 <span>Obsidian</span> 语义检索</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">基于 BGE-M3 向量模型的知识库搜索引擎</p>', unsafe_allow_html=True)

# 同步区域
st.markdown('<div class="sync-section">', unsafe_allow_html=True)
st.markdown('<div class="sync-title">📂 向量库同步</div>', unsafe_allow_html=True)

stats = get_stats()
if stats:
    st.markdown(f"""
    <div style="display: flex; gap: 2rem; align-items: center; margin-bottom: 0.75rem;">
        <span>📄 <strong>{stats['total_files']}</strong> 个文件</span>
        <span>📝 <strong>{stats['total_chunks']}</strong> 个文本块</span>
        <span>🔄 实时监听: {'✅' if stats.get('watcher_running') else '⏹️'}</span>
    </div>
    """, unsafe_allow_html=True)

# 检查是否正在同步
progress = get_progress()

if progress.get("is_running"):
    st.session_state["syncing"] = True
    
    # 显示进度条
    progress_percent = progress.get("progress_percent", 0)
    processed = progress.get("processed_files", 0)
    total = progress.get("total_files", 1)
    current_file = progress.get("current_file", "")
    
    st.progress(int(progress_percent) / 100)
    st.markdown(f"""
    <div class="sync-info">
        ⏳ 正在索引... {progress_percent}% ({processed}/{total})<br>
        当前文件: {current_file}
    </div>
    """, unsafe_allow_html=True)
    
    # 自动刷新
    time.sleep(0.5)
    st.rerun()

elif st.session_state["syncing"]:
    # 同步刚完成
    st.session_state["syncing"] = False
    if progress.get("status") == "completed":
        st.success(f"✅ {progress.get('message', '同步完成')}")
    st.rerun()

else:
    # 显示同步按钮
    if st.button("🔄 全量同步", use_container_width=True, type="primary"):
        st.session_state["syncing"] = True
        result = trigger_sync()
        if result.get("status") == "error":
            st.error(f"❌ {result['message']}")
            st.session_state["syncing"] = False
        else:
            st.rerun()

st.markdown('</div>', unsafe_allow_html=True)

# 搜索框
col_search, col_k = st.columns([5, 1])
with col_search:
    query = st.text_input(
        "搜索",
        value=st.session_state["search_query"],
        placeholder="搜索你的知识库...",
        label_visibility="collapsed",
        key="search_input"
    )
with col_k:
    top_k = st.selectbox("结果", [5, 10, 15, 20], index=1, label_visibility="collapsed")

# 示例查询
if not query:
    st.markdown('<div class="example-category">🌐 Web 安全</div>', unsafe_allow_html=True)
    cols = st.columns(4)
    for i, ex in enumerate(["SQL注入绕过WAF", "XSS窃取Cookie", "CSRF攻击原理", "SSRF内网探测"]):
        if cols[i].button(ex, key=f"web_{i}", use_container_width=True):
            st.session_state["search_query"] = ex
            st.rerun()
    
    st.markdown('<div class="example-category">🎯 渗透测试</div>', unsafe_allow_html=True)
    cols = st.columns(4)
    for i, ex in enumerate(["内网横向移动", "权限提升方法", "凭据窃取技术", "免杀绕过技巧"]):
        if cols[i].button(ex, key=f"pentest_{i}", use_container_width=True):
            st.session_state["search_query"] = ex
            st.rerun()
    
    st.markdown('<div class="example-category">☁️ 云安全</div>', unsafe_allow_html=True)
    cols = st.columns(4)
    for i, ex in enumerate(["Docker逃逸方法", "Kubernetes攻击面", "AWS IAM提权", "容器安全配置"]):
        if cols[i].button(ex, key=f"cloud_{i}", use_container_width=True):
            st.session_state["search_query"] = ex
            st.rerun()
    
    st.markdown('<div class="example-category">🔐 密码学</div>', unsafe_allow_html=True)
    cols = st.columns(4)
    for i, ex in enumerate(["RSA攻击方法", "AES加密模式", "哈希碰撞攻击", "证书伪造技术"]):
        if cols[i].button(ex, key=f"crypto_{i}", use_container_width=True):
            st.session_state["search_query"] = ex
            st.rerun()

# 执行搜索
if query:
    st.session_state["search_query"] = ""
    
    with st.spinner(""):
        result = search(query, top_k)
    
    if "error" in result:
        st.error(f"❌ {result['error']}")
    elif "results" in result:
        if not result["results"]:
            st.markdown('<div style="text-align: center; padding: 3rem; color: #8b949e;"><div style="font-size: 3rem;">🔍</div><div>未找到相关结果</div></div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="stats-bar"><span><strong>{result["total"]}</strong> 个结果</span><span>耗时 <strong>{result["took_ms"]}</strong>ms</span></div>', unsafe_allow_html=True)
            
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
                
                st.markdown(f'''
                <div class="result-card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span class="score-badge {score_class}">{score:.0%} 匹配</span>
                        <a href="{obsidian_url}" class="action-btn action-btn-primary" target="_blank">打开笔记</a>
                    </div>
                    <div class="path-area">
                        <a href="{obsidian_url}" class="path-link">📄 {relative_path}</a>
                        {f'<span class="heading-tag">› {heading}</span>' if heading else ''}
                        <div class="full-path">{source}</div>
                    </div>
                ''', unsafe_allow_html=True)
                
                if len(content) > 1000:
                    content = content[:1000]
                    last_newline = content.rfind("\n")
                    if last_newline > 600:
                        content = content[:last_newline]
                    content += "\n\n---\n*点击「打开笔记」查看完整内容*"
                
                st.markdown('<div class="md-content">', unsafe_allow_html=True)
                st.markdown(content)
                st.markdown('</div></div>', unsafe_allow_html=True)