"""Streamlit Web UI - Obsidian 语义检索"""
import streamlit as st
import httpx
import urllib.parse

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
    /* ===== 全局样式 ===== */
    .stApp {
        background-color: #0d1117;
        color: #c9d1d9;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif;
    }
    
    /* 隐藏默认元素 */
    #MainMenu, footer, header {visibility: hidden;}
    .stDeployButton {display: none;}
    
    /* ===== 标题样式 ===== */
    .main-title {
        font-size: 2rem;
        font-weight: 600;
        color: #f0f6fc;
        text-align: center;
        padding: 1.5rem 0 0.5rem 0;
    }
    .main-title span {
        color: #58a6ff;
    }
    .subtitle {
        color: #8b949e;
        text-align: center;
        font-size: 0.95rem;
        padding-bottom: 1.5rem;
        border-bottom: 1px solid #21262d;
    }
    
    /* ===== 搜索框 ===== */
    .stTextInput > div > div > input {
        background-color: #0d1117 !important;
        border: 1px solid #30363d !important;
        border-radius: 6px !important;
        font-size: 1rem !important;
        padding: 0.75rem 1rem !important;
        color: #c9d1d9 !important;
        transition: all 0.15s ease;
    }
    .stTextInput > div > div > input:focus {
        border-color: #58a6ff !important;
        box-shadow: 0 0 0 3px rgba(88, 166, 255, 0.3) !important;
        background-color: #161b22 !important;
    }
    .stTextInput > div > div > input::placeholder {
        color: #484f58 !important;
    }
    
    /* ===== 示例按钮 ===== */
    .example-container {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        justify-content: center;
        padding: 1rem 0;
    }
    .example-btn {
        background-color: #21262d;
        border: 1px solid #30363d;
        color: #8b949e;
        padding: 0.4rem 0.9rem;
        border-radius: 6px;
        font-size: 0.85rem;
        cursor: pointer;
        transition: all 0.15s ease;
    }
    .example-btn:hover {
        background-color: #30363d;
        border-color: #8b949e;
        color: #f0f6fc;
    }
    
    /* ===== 统计栏 ===== */
    .stats-bar {
        background-color: #161b22;
        border: 1px solid #21262d;
        border-radius: 6px;
        padding: 0.75rem 1rem;
        margin: 1rem 0;
        display: flex;
        gap: 1.5rem;
        color: #8b949e;
        font-size: 0.9rem;
    }
    .stats-bar strong {
        color: #f0f6fc;
    }
    
    /* ===== 结果卡片 ===== */
    .result-card {
        background-color: #161b22;
        border: 1px solid #21262d;
        border-radius: 6px;
        padding: 1rem 1.25rem;
        margin-bottom: 0.75rem;
    }
    .result-card:hover {
        border-color: #30363d;
    }
    
    /* ===== 分数徽章 ===== */
    .score-badge {
        display: inline-block;
        padding: 0.2rem 0.6rem;
        border-radius: 2em;
        font-size: 0.8rem;
        font-weight: 500;
    }
    .score-high {
        background-color: #238636;
        color: #ffffff;
    }
    .score-mid {
        background-color: #9e6a03;
        color: #ffffff;
    }
    .score-low {
        background-color: #30363d;
        color: #8b949e;
    }
    
    /* ===== 路径区域 ===== */
    .path-area {
        padding: 0.5rem 0;
        border-bottom: 1px solid #21262d;
        margin-bottom: 0.75rem;
    }
    .path-link {
        color: #58a6ff;
        text-decoration: none;
        font-size: 0.9rem;
        font-weight: 500;
    }
    .path-link:hover {
        text-decoration: underline;
    }
    .heading-tag {
        color: #7ee787;
        font-size: 0.85rem;
        margin-left: 0.5rem;
    }
    .full-path {
        color: #484f58;
        font-size: 0.75rem;
        margin-top: 0.25rem;
        font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace;
    }
    
    /* ===== 操作按钮 ===== */
    .action-btn {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        background-color: #21262d;
        border: 1px solid #30363d;
        color: #c9d1d9;
        padding: 0.35rem 0.75rem;
        border-radius: 6px;
        font-size: 0.8rem;
        text-decoration: none;
        transition: all 0.15s ease;
    }
    .action-btn:hover {
        background-color: #30363d;
        border-color: #8b949e;
        color: #f0f6fc;
    }
    .action-btn-primary {
        background-color: #238636;
        border-color: #238636;
        color: #ffffff;
    }
    .action-btn-primary:hover {
        background-color: #2ea043;
        border-color: #2ea043;
    }
    
    /* ===== Markdown 内容 ===== */
    .content-area {
        color: #c9d1d9;
        line-height: 1.6;
        font-size: 0.9rem;
    }
    .content-area h1, .content-area h2, .content-area h3 {
        color: #f0f6fc;
        margin: 0.75rem 0 0.5rem 0;
        font-weight: 600;
    }
    .content-area h1 { font-size: 1.25rem; }
    .content-area h2 { font-size: 1.1rem; }
    .content-area h3 { font-size: 1rem; }
    .content-area table {
        width: 100%;
        border-collapse: collapse;
        margin: 0.5rem 0;
    }
    .content-area th {
        background-color: #21262d;
        color: #f0f6fc;
        padding: 0.5rem 0.75rem;
        border: 1px solid #30363d;
        text-align: left;
        font-weight: 600;
    }
    .content-area td {
        padding: 0.5rem 0.75rem;
        border: 1px solid #30363d;
        color: #c9d1d9;
    }
    .content-area tr:nth-child(even) td {
        background-color: #0d1117;
    }
    .content-area code {
        background-color: #343942;
        color: #f0f6fc;
        padding: 0.15rem 0.4rem;
        border-radius: 6px;
        font-size: 0.85em;
        font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace;
    }
    .content-area pre {
        background-color: #161b22;
        border: 1px solid #21262d;
        border-radius: 6px;
        padding: 1rem;
        overflow-x: auto;
        margin: 0.75rem 0;
    }
    .content-area pre code {
        background: none;
        padding: 0;
        border-radius: 0;
        font-size: 0.85rem;
    }
    .content-area blockquote {
        border-left: 3px solid #3b82f6;
        padding-left: 1rem;
        color: #8b949e;
        margin: 0.75rem 0;
    }
    .content-area ul, .content-area ol {
        padding-left: 1.5rem;
    }
    .content-area li {
        margin: 0.25rem 0;
    }
    .content-area a {
        color: #58a6ff;
    }
    .content-area strong {
        color: #f0f6fc;
        font-weight: 600;
    }
    .content-area em {
        color: #8b949e;
    }
    .content-area hr {
        border: none;
        border-top: 1px solid #21262d;
        margin: 1rem 0;
    }
    
    /* ===== 加载更多 ===== */
    .load-more {
        text-align: center;
        padding: 1rem;
        color: #8b949e;
        font-size: 0.85rem;
    }
    
    /* ===== Select 样式 ===== */
    .stSelectbox > div > div {
        background-color: #21262d;
        border: 1px solid #30363d;
        border-radius: 6px;
    }
    .stSelectbox > div > div:hover {
        border-color: #8b949e;
    }
    
    /* ===== 分隔线 ===== */
    .divider {
        border: none;
        border-top: 1px solid #21262d;
        margin: 1.5rem 0;
    }
</style>
""", unsafe_allow_html=True)


def search(query: str, top_k: int = 10):
    """调用搜索 API"""
    if not query or not query.strip():
        return {"error": "请输入查询内容"}
    
    try:
        response = httpx.post(
            f"{BACKEND_URL}/api/search",
            json={"query": query.strip(), "top_k": top_k},
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()
    except httpx.ConnectError:
        return {"error": "无法连接后端服务"}
    except httpx.TimeoutException:
        return {"error": "搜索超时"}
    except Exception as e:
        return {"error": f"搜索失败"}


def get_obsidian_url(file_path: str):
    """生成 Obsidian 打开链接"""
    if file_path.startswith("/Users/"):
        parts = file_path.split("/StorageObsidian/")
        if len(parts) > 1:
            relative_path = parts[1]
        else:
            relative_path = file_path.split("/")[-1]
    else:
        relative_path = file_path
    encoded_path = urllib.parse.quote(relative_path)
    return f"obsidian://open?vault={OBSIDIAN_VAULT}&file={encoded_path}"


# ============== Main UI ==============

# 标题
st.markdown('<h1 class="main-title">🔍 <span>Obsidian</span> 语义检索</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">基于 BGE-M3 向量模型的知识库搜索引擎</p>', unsafe_allow_html=True)

# 搜索框
col_search, col_k = st.columns([5, 1])
with col_search:
    query = st.text_input(
        "搜索",
        placeholder="搜索你的知识库...",
        label_visibility="collapsed"
    )
with col_k:
    top_k = st.selectbox("结果", [5, 10, 15, 20], index=1, label_visibility="collapsed")

# 示例查询
if not query:
    st.markdown('<div class="example-container">', unsafe_allow_html=True)
    cols = st.columns(6)
    examples = ["SQL注入", "XSS攻击", "内网渗透", "Docker", "Kubernetes", "密码学"]
    for i, ex in enumerate(examples):
        if cols[i].button(ex, key=f"ex_{i}", use_container_width=True):
            st.session_state["query"] = ex
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<hr class="divider">', unsafe_allow_html=True)

# 执行搜索
if query:
    with st.spinner(""):
        result = search(query, top_k)
    
    if "error" in result:
        st.error(f"❌ {result['error']}")
    elif "results" in result:
        if not result["results"]:
            st.markdown("""
            <div style="text-align: center; padding: 3rem; color: #8b949e;">
                <div style="font-size: 3rem; margin-bottom: 1rem;">🔍</div>
                <div>未找到相关结果</div>
                <div style="font-size: 0.85rem; margin-top: 0.5rem;">尝试使用不同的关键词</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            # 结果统计
            st.markdown(f"""
            <div class="stats-bar">
                <span><strong>{result['total']}</strong> 个结果</span>
                <span>耗时 <strong>{result['took_ms']}</strong>ms</span>
            </div>
            """, unsafe_allow_html=True)
            
            # 结果列表
            for hit in result["results"]:
                score = hit.get("score", 0)
                source = hit.get("source", "")
                heading = hit.get("heading", "")
                content = hit.get("content", "")
                
                # 相对路径
                if source.startswith("/Users/"):
                    parts = source.split("/StorageObsidian/")
                    relative_path = parts[1] if len(parts) > 1 else source.split("/")[-1]
                else:
                    relative_path = source
                
                # Obsidian 链接
                obsidian_url = get_obsidian_url(source)
                
                # 分数样式
                if score >= 0.7:
                    score_class = "score-high"
                elif score >= 0.5:
                    score_class = "score-mid"
                else:
                    score_class = "score-low"
                
                # 卡片
                st.markdown(f"""
                <div class="result-card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span class="score-badge {score_class}">{score:.0%} 匹配</span>
                        <a href="{obsidian_url}" class="action-btn action-btn-primary" target="_blank">
                            打开笔记
                        </a>
                    </div>
                    <div class="path-area">
                        <a href="{obsidian_url}" class="path-link">📄 {relative_path}</a>
                        {f'<span class="heading-tag">› {heading}</span>' if heading else ''}
                        <div class="full-path">{source}</div>
                    </div>
                """, unsafe_allow_html=True)
                
                # 内容
                if len(content) > 700:
                    content = content[:700]
                    last_newline = content.rfind("\n")
                    if last_newline > 400:
                        content = content[:last_newline]
                    content += "\n\n---\n*点击「打开笔记」查看完整内容*"
                
                st.markdown(f'<div class="content-area">{content}</div>', unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)