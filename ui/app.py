"""Streamlit Web UI - Obsidian 语义检索（简化版）"""
import streamlit as st
import httpx

# 配置
BACKEND_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="Obsidian 语义检索",
    page_icon="🔍",
    layout="wide"
)

# 简洁样式
st.markdown("""
<style>
    .stApp { background-color: #0e0e1a; }
    .result-card { 
        background-color: #1a1a2e; 
        border-radius: 8px; 
        padding: 1rem; 
        margin-bottom: 1rem; 
        border: 1px solid #333; 
    }
</style>
""", unsafe_allow_html=True)


def search(query: str, top_k: int = 10):
    """调用搜索 API"""
    try:
        response = httpx.post(
            f"{BACKEND_URL}/api/search",
            json={"query": query, "top_k": top_k},
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}


def get_stats():
    """获取统计信息"""
    try:
        response = httpx.get(f"{BACKEND_URL}/api/stats", timeout=5.0)
        response.raise_for_status()
        return response.json()
    except:
        return None


# ============== Main UI ==============

st.title("🔍 Obsidian 语义检索")
st.markdown("基于 BGE-M3 向量模型的知识库搜索")

# 侧边栏 - 统计信息
stats = get_stats()
if stats:
    with st.sidebar:
        st.metric("📄 文档数", stats.get("total_files", 0))
        st.metric("📝 文本块", stats.get("total_chunks", 0))

# 搜索框
query = st.text_input(
    "输入查询内容",
    placeholder="例如: SQL注入的防御方法",
    label_visibility="collapsed"
)

top_k = st.slider("返回结果数", 1, 20, 5)

# 执行搜索
if query:
    with st.spinner("搜索中..."):
        result = search(query, top_k)
    
    if "error" in result:
        st.error(f"搜索失败: {result['error']}")
    elif "results" in result:
        st.markdown(f"找到 **{result['total']}** 个结果 · 耗时 **{result['took_ms']}ms**")
        
        for hit in result["results"]:
            with st.container():
                # 分数和来源
                col1, col2 = st.columns([1, 6])
                with col1:
                    st.metric("相似度", f"{hit['score']:.0%}")
                with col2:
                    source = hit.get("source", "").split("/")[-1]
                    if hit.get("heading"):
                        st.markdown(f"**{source}** · {hit['heading']}")
                    else:
                        st.markdown(f"**{source}**")
                
                # 内容预览
                content = hit.get("content", "")
                st.markdown(f"> {content[:400]}{'...' if len(content) > 400 else ''}")
                st.divider()