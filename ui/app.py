"""Streamlit Web UI - Obsidian 语义检索"""
import streamlit as st
import httpx

# 配置
BACKEND_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="Obsidian 语义检索",
    page_icon="🔍",
    layout="wide"
)

# 自定义样式
st.markdown("""
<style>
    .stApp { background-color: #0f0f1a; }
    .search-box input {
        font-size: 1.2rem !important;
        padding: 1rem !important;
    }
    .result-card {
        background-color: #1a1a2e;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        border: 1px solid #2a2a4a;
    }
    .source-path {
        color: #888;
        font-size: 0.9rem;
        margin-bottom: 0.5rem;
    }
    .score-badge {
        background: linear-gradient(135deg, #4CAF50, #2E7D32);
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-weight: bold;
        font-size: 0.9rem;
    }
    .example-chip {
        background-color: #2a2a4a;
        color: #aaa;
        padding: 0.4rem 0.8rem;
        border-radius: 16px;
        cursor: pointer;
        margin: 0.2rem;
        display: inline-block;
        transition: all 0.2s;
    }
    .example-chip:hover {
        background-color: #3a3a5a;
        color: #fff;
    }
    .result-card table { width: 100%; border-collapse: collapse; }
    .result-card th, .result-card td { border: 1px solid #444; padding: 0.5rem; }
    .result-card code { background-color: #2a2a4a; padding: 0.2rem 0.4rem; border-radius: 4px; font-size: 0.85rem; }
    .result-card pre { background-color: #1e1e2e; padding: 1rem; border-radius: 8px; overflow-x: auto; }
    .result-card blockquote { border-left: 3px solid #4CAF50; padding-left: 1rem; color: #aaa; }
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
        return {"error": "无法连接后端服务，请检查后端是否启动"}
    except httpx.TimeoutException:
        return {"error": "搜索超时，请稍后重试"}
    except Exception as e:
        return {"error": f"搜索失败: {str(e)}"}


# ============== Main UI ==============

# 标题
st.markdown("# 🔍 Obsidian 语义检索")
st.markdown("---")

# 搜索区域
col_search, col_k = st.columns([5, 1])
with col_search:
    query = st.text_input(
        "搜索",
        placeholder="输入查询内容，如：SQL注入的防御方法",
        label_visibility="collapsed"
    )
with col_k:
    top_k = st.selectbox("结果数", [5, 10, 15, 20], index=1, label_visibility="collapsed")

# 示例查询（仅在没有查询时显示）
if not query:
    st.markdown("**试试这些查询：**")
    examples = [
        "SQL注入防御", "XSS攻击类型", "内网渗透",
        "Docker安全", "Kubernetes部署", "密码学基础"
    ]
    cols = st.columns(len(examples))
    for i, ex in enumerate(examples):
        if cols[i].button(ex, key=f"ex_{i}"):
            st.session_state["query_input"] = ex
            st.rerun()
    st.markdown("---")

# 执行搜索
if query:
    with st.spinner("搜索中..."):
        result = search(query, top_k)
    
    if "error" in result:
        st.error(f"❌ {result['error']}")
    elif "results" in result:
        if not result["results"]:
            st.info("未找到相关结果，请尝试其他关键词")
        else:
            # 结果统计
            st.markdown(f"**{result['total']}** 条结果 · 耗时 {result['took_ms']}ms")
            st.markdown("---")
            
            # 结果列表
            for hit in result["results"]:
                with st.container():
                    # 头部：分数 + 来源路径
                    col1, col2 = st.columns([1, 9])
                    
                    with col1:
                        score = hit.get("score", 0)
                        if score >= 0.7:
                            st.markdown(f'<span class="score-badge">{score:.0%}</span>', unsafe_allow_html=True)
                        elif score >= 0.5:
                            st.markdown(f'<span style="color:#FFC107; font-weight:bold;">{score:.0%}</span>', unsafe_allow_html=True)
                        else:
                            st.markdown(f'<span style="color:#888;">{score:.0%}</span>', unsafe_allow_html=True)
                    
                    with col2:
                        source = hit.get("source", "")
                        if source.startswith("/Users/"):
                            parts = source.split("/StorageObsidian/")
                            if len(parts) > 1:
                                source = parts[1]
                        heading = hit.get("heading", "")
                        if heading:
                            st.markdown(f'<div class="source-path">📄 {source} <span style="color:#4CAF50;">› {heading}</span></div>', unsafe_allow_html=True)
                        else:
                            st.markdown(f'<div class="source-path">📄 {source}</div>', unsafe_allow_html=True)
                    
                    # Markdown 内容预览
                    content = hit.get("content", "")
                    if len(content) > 600:
                        content = content[:600]
                        last_newline = content.rfind("\n")
                        if last_newline > 400:
                            content = content[:last_newline]
                        content += "\n\n*...*"
                    
                    st.markdown(content)
                    st.markdown("---")