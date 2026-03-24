"""Streamlit Web UI - Obsidian 语义检索"""
import streamlit as st
import httpx
from typing import List, Dict, Any
import time
from pathlib import Path

# 配置
BACKEND_URL = "http://backend:8000"
# 本地开发时使用
# BACKEND_URL = "http://localhost:8000"

st.set_page_config(
    page_title="Obsidian 语义检索",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义样式
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        margin-bottom: 0.5rem;
    }
    .result-card {
        background-color: #1a1a2e;
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 1rem;
        border: 1px solid #333;
    }
    .result-score {
        color: #4CAF50;
        font-weight: bold;
        font-size: 1.1rem;
    }
    .result-source {
        color: #888;
        font-size: 0.9rem;
        margin-bottom: 0.5rem;
    }
    .result-content {
        color: #ddd;
        line-height: 1.6;
    }
    .stApp {
        background-color: #0e0e1a;
    }
</style>
""", unsafe_allow_html=True)


def search_query(query: str, top_k: int = 10, folder: str = None) -> Dict[str, Any]:
    """调用搜索 API"""
    try:
        response = httpx.post(
            f"{BACKEND_URL}/api/search",
            json={
                "query": query,
                "top_k": top_k,
                "folder": folder if folder else None
            },
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}


def get_stats() -> Dict[str, Any]:
    """获取统计信息"""
    try:
        response = httpx.get(f"{BACKEND_URL}/api/stats", timeout=10.0)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}


def trigger_index() -> Dict[str, Any]:
    """触发全量索引"""
    try:
        response = httpx.post(f"{BACKEND_URL}/api/index", timeout=300.0)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}


def check_health() -> bool:
    """检查后端健康状态"""
    try:
        response = httpx.get(f"{BACKEND_URL}/health", timeout=5.0)
        return response.status_code == 200
    except:
        return False


# ============== Main UI ==============

def main():
    # 标题
    st.markdown('<p class="main-header">🔍 Obsidian 语义检索</p>', unsafe_allow_html=True)
    st.markdown("基于 BGE-M3 向量模型的智能知识检索")
    
    # 侧边栏
    with st.sidebar:
        st.header("📊 系统状态")
        
        # 健康检查
        if check_health():
            st.success("✅ 后端服务正常")
        else:
            st.error("❌ 后端服务异常")
        
        # 统计信息
        stats = get_stats()
        if "error" not in stats:
            st.metric("📄 文档数", stats.get("total_files", 0))
            st.metric("📝 文本块", stats.get("total_chunks", 0))
            
            watcher_status = "运行中 🟢" if stats.get("watcher_running") else "已停止 🔴"
            st.metric("🔄 实时同步", watcher_status)
            
            # 最近事件
            if stats.get("last_events"):
                with st.expander("📋 最近同步事件"):
                    for event in stats["last_events"][-5:]:
                        st.text(f"{event['type']}: {event['path']}")
        else:
            st.warning(f"无法获取统计: {stats['error']}")
        
        st.divider()
        
        # 索引操作
        st.header("⚙️ 索引管理")
        
        if st.button("🔄 全量索引", use_container_width=True):
            with st.spinner("正在索引..."):
                result = trigger_index()
                if "error" in result:
                    st.error(f"索引失败: {result['error']}")
                else:
                    st.success(f"✅ {result['message']}")
                    st.info(f"文件: {result['files_indexed']} | 块: {result['chunks_created']} | 耗时: {result['took_seconds']}s")
                    time.sleep(1)
                    st.rerun()
        
        st.divider()
        
        # 设置
        st.header("⚙️ 搜索设置")
        top_k = st.slider("返回结果数", 1, 20, 10)
        folder_filter = st.text_input("文件夹过滤", placeholder="如: 网络安全知识库")
    
    # 主搜索区
    st.markdown("### 🔎 搜索你的知识库")
    
    # 搜索框
    col1, col2 = st.columns([6, 1])
    with col1:
        query = st.text_input(
            "输入查询内容",
            placeholder="例如: SQL注入的防御方法有哪些？",
            label_visibility="collapsed"
        )
    with col2:
        search_button = st.button("搜索", type="primary", use_container_width=True)
    
    # 执行搜索
    if query and search_button:
        with st.spinner("搜索中..."):
            start_time = time.time()
            result = search_query(query, top_k, folder_filter if folder_filter else None)
            took_ms = int((time.time() - start_time) * 1000)
        
        if "error" in result:
            st.error(f"搜索失败: {result['error']}")
        elif "results" in result:
            st.markdown(f"找到 **{result['total']}** 个结果 · 耗时 **{result['took_ms']}ms**")
            
            if result["results"]:
                for i, hit in enumerate(result["results"], 1):
                    with st.container():
                        # 结果卡片
                        col_score, col_source = st.columns([1, 5])
                        
                        with col_score:
                            score_color = "green" if hit["score"] > 0.7 else ("orange" if hit["score"] > 0.5 else "gray")
                            st.markdown(f"**{hit['score']:.2%}**")
                        
                        with col_source:
                            source = hit.get("source", "")
                            if hit.get("heading"):
                                st.markdown(f"📄 `{source}` · **{hit['heading']}**")
                            else:
                                st.markdown(f"📄 `{source}`")
                        
                        # 内容预览
                        content = hit.get("content", "")
                        # 高亮关键词（简单实现）
                        preview = content[:500] + "..." if len(content) > 500 else content
                        st.markdown(f"> {preview}")
                        
                        # 操作按钮
                        col1, col2 = st.columns([1, 1])
                        with col1:
                            if hit.get("file_path"):
                                st.code(hit["file_path"], language=None)
                        
                        st.divider()
            else:
                st.info("未找到相关结果，试试其他关键词？")
    
    # 示例查询
    st.markdown("### 💡 试试这些查询")
    example_queries = [
        "SQL注入的防御方法",
        "XSS攻击类型和防护",
        "密码学基础知识",
        "渗透测试流程",
        "常见Web漏洞"
    ]
    
    cols = st.columns(len(example_queries))
    for col, eq in zip(cols, example_queries):
        if col.button(eq, key=f"example_{eq}"):
            st.session_state["query"] = eq
            st.rerun()


if __name__ == "__main__":
    main()