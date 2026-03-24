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

# 美化样式
st.markdown("""
<style>
    /* 全局样式 */
    .stApp {
        background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 100%);
        min-height: 100vh;
    }
    
    /* 隐藏 Streamlit 默认元素 */
    #MainMenu, footer, header {visibility: hidden;}
    .stDeployButton {display: none;}
    
    /* 搜索框样式 */
    .stTextInput > div > div > input {
        background-color: #1e1e2e !important;
        border: 2px solid #3a3a5a !important;
        border-radius: 12px !important;
        font-size: 1.1rem !important;
        padding: 1rem 1.5rem !important;
        color: #e0e0e0 !important;
        transition: all 0.3s ease;
    }
    .stTextInput > div > div > input:focus {
        border-color: #7C3AED !important;
        box-shadow: 0 0 0 3px rgba(124, 58, 237, 0.2) !important;
    }
    .stTextInput > div > div > input::placeholder {
        color: #666 !important;
    }
    
    /* 标题样式 */
    .main-title {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(135deg, #7C3AED 0%, #4CAF50 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .subtitle {
        color: #888;
        text-align: center;
        font-size: 1rem;
        margin-bottom: 2rem;
    }
    
    /* 示例按钮 */
    .example-btn {
        background: linear-gradient(135deg, #2a2a4a 0%, #3a3a5a 100%);
        border: 1px solid #4a4a6a;
        color: #bbb;
        padding: 0.6rem 1.2rem;
        border-radius: 25px;
        cursor: pointer;
        transition: all 0.3s ease;
        font-size: 0.9rem;
    }
    .example-btn:hover {
        background: linear-gradient(135deg, #3a3a5a 0%, #4a4a6a 100%);
        border-color: #7C3AED;
        color: #fff;
        transform: translateY(-2px);
    }
    
    /* 结果卡片 */
    .result-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #1e1e3a 100%);
        border: 1px solid #2a2a4a;
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        transition: all 0.3s ease;
    }
    .result-card:hover {
        border-color: #4a4a7a;
        box-shadow: 0 8px 32px rgba(124, 58, 237, 0.15);
        transform: translateY(-2px);
    }
    
    /* 分数徽章 */
    .score-high {
        background: linear-gradient(135deg, #4CAF50, #2E7D32);
        color: white;
        padding: 0.4rem 1rem;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.95rem;
    }
    .score-mid {
        background: linear-gradient(135deg, #FFC107, #FF8F00);
        color: #1a1a2e;
        padding: 0.4rem 1rem;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.95rem;
    }
    .score-low {
        background: linear-gradient(135deg, #616161, #424242);
        color: #ccc;
        padding: 0.4rem 1rem;
        border-radius: 20px;
        font-weight: 500;
        font-size: 0.95rem;
    }
    
    /* 路径链接 */
    .path-link {
        color: #7C3AED !important;
        text-decoration: none;
        font-size: 0.9rem;
        transition: color 0.2s;
    }
    .path-link:hover {
        color: #A78BFA !important;
        text-decoration: underline;
    }
    
    /* Markdown 内容样式 */
    .result-content h1, .result-content h2, .result-content h3 {
        color: #e0e0e0 !important;
        margin-top: 0.5rem !important;
        margin-bottom: 0.5rem !important;
    }
    .result-content table { width: 100%; border-collapse: collapse; margin: 0.5rem 0; }
    .result-content th { background: #2a2a4a; color: #e0e0e0; padding: 0.5rem; border: 1px solid #3a3a5a; }
    .result-content td { color: #ccc; padding: 0.5rem; border: 1px solid #3a3a5a; }
    .result-content code { background-color: #2a2a4a; padding: 0.2rem 0.5rem; border-radius: 4px; font-size: 0.85rem; color: #A78BFA; }
    .result-content pre { background-color: #1a1a2e; padding: 1rem; border-radius: 8px; overflow-x: auto; border: 1px solid #2a2a4a; }
    .result-content pre code { background: none; padding: 0; }
    .result-content blockquote { border-left: 4px solid #7C3AED; padding-left: 1rem; color: #aaa; margin: 0.5rem 0; }
    .result-content ul, .result-content ol { color: #ccc; }
    .result-content a { color: #7C3AED; }
    .result-content strong { color: #e0e0e0; }
    
    /* 打开按钮 */
    .open-btn {
        background: linear-gradient(135deg, #7C3AED, #6D28D9);
        color: white;
        border: none;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        font-size: 0.85rem;
        cursor: pointer;
        transition: all 0.2s;
        text-decoration: none;
        display: inline-flex;
        align-items: center;
        gap: 0.3rem;
    }
    .open-btn:hover {
        background: linear-gradient(135deg, #8B5CF6, #7C3AED);
        transform: scale(1.02);
    }
    
    /* 统计信息 */
    .stats-bar {
        background: rgba(124, 58, 237, 0.1);
        border: 1px solid rgba(124, 58, 237, 0.3);
        border-radius: 12px;
        padding: 0.8rem 1.5rem;
        margin: 1rem 0;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    /* 分隔线 */
    hr {
        border: none;
        height: 1px;
        background: linear-gradient(90deg, transparent, #3a3a5a, transparent);
        margin: 2rem 0;
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
        return {"error": "无法连接后端服务，请检查后端是否启动"}
    except httpx.TimeoutException:
        return {"error": "搜索超时，请稍后重试"}
    except Exception as e:
        return {"error": f"搜索失败: {str(e)}"}


def get_obsidian_url(file_path: str):
    """生成 Obsidian 打开链接"""
    # 移除绝对路径前缀，获取相对路径
    if file_path.startswith("/Users/"):
        parts = file_path.split("/StorageObsidian/")
        if len(parts) > 1:
            relative_path = parts[1]
        else:
            relative_path = file_path.split("/")[-1]
    else:
        relative_path = file_path
    
    # URL 编码
    encoded_path = urllib.parse.quote(relative_path)
    
    # Obsidian URI
    return f"obsidian://open?vault={OBSIDIAN_VAULT}&file={encoded_path}"


def get_finder_url(file_path: str):
    """生成 Finder 打开链接"""
    return f"file://{file_path}"


# ============== Main UI ==============

# 标题
st.markdown('<h1 class="main-title">🔍 Obsidian 语义检索</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">基于 BGE-M3 向量模型的知识库搜索引擎</p>', unsafe_allow_html=True)

# 搜索框
col_search, col_k = st.columns([6, 1])
with col_search:
    query = st.text_input(
        "搜索",
        placeholder="输入查询内容，如：SQL注入的防御方法、XSS攻击类型...",
        label_visibility="collapsed"
    )
with col_k:
    top_k = st.selectbox("结果数", [5, 10, 15, 20], index=1, label_visibility="collapsed")

# 示例查询
if not query:
    st.markdown("<div style='text-align: center; margin: 1rem 0;'>", unsafe_allow_html=True)
    examples = [
        "SQL注入防御", "XSS攻击", "内网渗透", 
        "Docker安全", "Kubernetes", "密码学"
    ]
    cols = st.columns(len(examples))
    for i, ex in enumerate(examples):
        if cols[i].button(ex, key=f"ex_{i}", use_container_width=True):
            st.session_state["query"] = ex
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)

# 执行搜索
if query:
    with st.spinner("🔍 搜索中..."):
        result = search(query, top_k)
    
    if "error" in result:
        st.error(f"❌ {result['error']}")
    elif "results" in result:
        if not result["results"]:
            st.info("🔍 未找到相关结果，请尝试其他关键词")
        else:
            # 结果统计
            st.markdown(f"""
            <div class="stats-bar">
                <span>📊 找到 <strong>{result['total']}</strong> 条相关结果</span>
                <span>⏱️ 耗时 {result['took_ms']}ms</span>
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
                    if len(parts) > 1:
                        relative_path = parts[1]
                    else:
                        relative_path = source.split("/")[-1]
                else:
                    relative_path = source
                
                # Obsidian 链接
                obsidian_url = get_obsidian_url(source)
                finder_url = get_finder_url(source)
                
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
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1rem;">
                        <div>
                            <span class="{score_class}">{score:.0%}</span>
                        </div>
                        <div style="text-align: right;">
                            <a href="{obsidian_url}" class="open-btn" target="_blank">
                                📝 在 Obsidian 中打开
                            </a>
                        </div>
                    </div>
                    <div style="margin-bottom: 0.5rem;">
                        <a href="{obsidian_url}" class="path-link" title="点击在 Obsidian 中打开">
                            📄 {relative_path}
                        </a>
                        {f'<span style="color: #4CAF50; margin-left: 0.5rem;">› {heading}</span>' if heading else ''}
                    </div>
                    <div style="color: #888; font-size: 0.8rem; margin-bottom: 1rem;">
                        <a href="{finder_url}" style="color: #666; text-decoration: none;" title="在 Finder 中显示">
                            📁 {source}
                        </a>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Markdown 内容
                if len(content) > 800:
                    content = content[:800]
                    last_newline = content.rfind("\n")
                    if last_newline > 500:
                        content = content[:last_newline]
                    content += "\n\n---\n*📖 点击上方「在 Obsidian 中打开」查看完整内容*"
                
                st.markdown(f'<div class="result-content">{content}</div>', unsafe_allow_html=True)
                st.markdown("<hr>", unsafe_allow_html=True)