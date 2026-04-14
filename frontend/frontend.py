"""
金融知识库 Streamlit 前端
Financial Knowledge Base Streamlit Frontend

简洁的 Web UI，支持：
- 问答
- 文档上传
- 统计信息展示
"""

import streamlit as st
import requests
import json
from pathlib import Path

# HTTP 请求超时（秒）：问答/嵌入与 LLM 较慢，导入大文档更久
REQUEST_TIMEOUT_ANSWER = 180
REQUEST_TIMEOUT_INGEST = 600
REQUEST_TIMEOUT_STATS = 120

# 页面配置
st.set_page_config(
    page_title="金融监管知识库",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 自定义样式
st.markdown("""
<style>
    .main {
        padding: 2rem;
    }
    .stTabs [data-baseweb="tab-list"] button {
        font-size: 16px;
        padding: 10px 20px;
    }
    .answer-box {
        background-color: #f0f8ff;
        padding: 1.5rem;
        border-radius: 8px;
        border-left: 4px solid #1f77b4;
        margin: 1rem 0;
    }
    .reference-box {
        background-color: #f5f5f5;
        padding: 1rem;
        border-radius: 6px;
        margin: 0.5rem 0;
        border-left: 3px solid #666;
    }
    .success-box {
        background-color: #d4edda;
        padding: 1rem;
        border-radius: 6px;
        color: #155724;
        margin: 1rem 0;
    }
    .error-box {
        background-color: #f8d7da;
        padding: 1rem;
        border-radius: 6px;
        color: #721c24;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# 侧边栏配置
st.sidebar.title("⚙️ 配置")
api_url = st.sidebar.text_input(
    "API 地址",
    value="http://localhost:8000",
    help="FastAPI 服务地址"
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 📖 使用说明")
st.sidebar.markdown("""
1. **问答**：输入金融监管相关问题，系统会检索法规并生成答案
2. **上传文档**：支持 PDF、DOCX、TXT 格式
3. **统计**：查看知识库中的文档和知识点数量
""")

# 主标题
st.title("📚 金融监管知识库")
st.markdown("基于 PostgreSQL + FAISS + LLM 的智能问答系统")

# 创建标签页
# tab1, tab2, tab3, tab4 = st.tabs(["💬 问答", "📤 上传文档", "📊 统计信息", "🔍 检索测试"])
tab1, tab2, tab3 = st.tabs(["💬 问答", "📤 上传文档", "📊 统计信息"])

# ============================================================================
# 标签页 1：问答
# ============================================================================

with tab1:
    st.header("问答系统")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        question = st.text_area(
            "请输入您的问题",
            placeholder="例如：商业银行资本充足率最低要求是什么？",
            height=100,
            key="question_input"
        )
    
    with col2:
        st.write("")
        st.write("")
        submit_btn = st.button("🔍 提交", use_container_width=True, type="primary")
    
    if submit_btn and question.strip():
        with st.spinner("正在处理您的问题..."):
            try:
                response = requests.post(
                    f"{api_url}/api/knowledge/answer",
                    json={"question": question},
                    timeout=REQUEST_TIMEOUT_ANSWER,
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # 显示答案
                    st.markdown("### 📝 答案")
                    st.markdown(f'<div class="answer-box">{result["answer"]}</div>', unsafe_allow_html=True)
                    
                    # 显示依据
                    if result.get("references"):
                        st.markdown("### 📚 法规依据")
                        for i, ref in enumerate(result["references"], 1):
                            with st.expander(f"依据 {i}: {ref.get('document_name', '未知文档')} - {ref.get('article_number', '')}"):
                                col1, col2 = st.columns([3, 1])
                                with col1:
                                    st.markdown(f"**文档**: {ref.get('document_name', '未知')}")
                                    st.markdown(f"**条款**: {ref.get('article_number', '未标明')} {ref.get('section_number', '')}")
                                    st.markdown(f"**分类**: {ref.get('category', '未分类')}")
                                    st.markdown(f"**监管类型**: {ref.get('regulation_type', '未标明')}")
                                with col2:
                                    sim = ref.get('similarity')
                                    if isinstance(sim, (int, float)):
                                        st.metric("相似度", f"{sim:.3f}")
                                
                                st.markdown("**内容**:")
                                st.text(ref.get('content', ''))
                    else:
                        st.info("未找到相关法规依据")
                
                else:
                    st.error(f"❌ 错误: {response.json().get('detail', '未知错误')}")
            
            except requests.exceptions.ConnectionError:
                st.error(f"❌ 无法连接到 API 服务: {api_url}")
                st.info("请确保 FastAPI 服务已启动: `python api.py`")
            except Exception as e:
                st.error(f"❌ 发生错误: {str(e)}")
    
    elif submit_btn:
        st.warning("⚠️ 请输入问题")


# ============================================================================
# 标签页 2：上传文档
# ============================================================================

with tab2:
    st.header("上传监管文档")
    
    col1, col2 = st.columns(2)
    
    with col1:
        uploaded_file = st.file_uploader(
            "选择文件 (PDF/DOCX/TXT)",
            type=["pdf", "docx", "doc", "txt"],
            help="支持 PDF、Word（.doc/.docx）、纯文本（服务端需 textxtract[pdf,doc,docx]）"
        )
        
        category = st.selectbox(
            "分类",
            ["风险管理", "资本管理", "流动性管理", "内部控制", "信息披露", "其他"],
            help="选择文档所属分类"
        )
    
    with col2:
        regulation_type = st.text_input(
            "监管类型",
            placeholder="例如：商业银行监管",
            help="输入监管类型"
        )
        
        source = st.text_input(
            "文档来源 (可选)",
            placeholder="例如：中国银保监会",
            help="输入文档来源"
        )
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        min_chunk_size = st.number_input(
            "最小分块大小",
            value=1,
            min_value=1,
            help="过滤小于此大小的文本片段"
        )
    
    with col2:
        keep_separator = st.checkbox(
            "保留分隔符",
            value=True,
            help="是否保留章节标识符"
        )
    
    with col3:
        batch_size = st.number_input(
            "批处理大小",
            value=100,
            min_value=10,
            help="每批导入的知识点数"
        )
    
    if st.button("📤 上传并导入", type="primary", use_container_width=True):
        if not uploaded_file:
            st.error("❌ 请选择文件")
        elif not regulation_type.strip():
            st.error("❌ 请输入监管类型")
        else:
            with st.spinner("正在处理文件..."):
                try:
                    files = {"file": (uploaded_file.name, uploaded_file.getbuffer())}
                    data = {
                        "category": category,
                        "regulation_type": regulation_type,
                        "source": source or None,
                        "min_chunk_size": min_chunk_size,
                        "keep_separator": keep_separator,
                        "batch_size": batch_size,
                    }
                    
                    response = requests.post(
                        f"{api_url}/api/knowledge/ingest",
                        files=files,
                        data=data,
                        timeout=REQUEST_TIMEOUT_INGEST,
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        st.markdown(f'<div class="success-box">✅ 文档导入成功！</div>', unsafe_allow_html=True)
                        
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("文档 ID", result["document_id"])
                        with col2:
                            st.metric("分块数", result["chunk_count"])
                        with col3:
                            st.metric("成功", result["success"])
                        with col4:
                            st.metric("失败", result["failed"])
                    else:
                        st.error(f"❌ 导入失败: {response.json().get('detail', '未知错误')}")
                
                except requests.exceptions.ConnectionError:
                    st.error(f"❌ 无法连接到 API 服务: {api_url}")
                except Exception as e:
                    st.error(f"❌ 发生错误: {str(e)}")


# ============================================================================
# 标签页 3：统计信息
# ============================================================================

with tab3:
    st.header("知识库统计")
    
    if st.button("🔄 刷新统计", use_container_width=True):
        st.rerun()
    
    with st.spinner("加载统计信息..."):
        try:
            response = requests.get(
                f"{api_url}/api/knowledge/stats", timeout=REQUEST_TIMEOUT_STATS
            )
            
            if response.status_code == 200:
                stats = response.json()
                
                # 关键指标
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("📄 文档数", stats["document_count"])
                
                with col2:
                    st.metric("💡 知识点数", stats["knowledge_count"])
                
                with col3:
                    st.metric("🔍 索引大小", stats["faiss_index_size"])
                
                with col4:
                    if stats["knowledge_count"] > 0:
                        avg_per_doc = stats["knowledge_count"] / max(stats["document_count"], 1)
                        st.metric("📊 平均每文档", f"{avg_per_doc:.1f}")
                
                # 分类分布
                st.markdown("### 📂 分类分布")
                if stats["category_distribution"]:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.bar_chart(stats["category_distribution"])
                    with col2:
                        for cat, count in stats["category_distribution"].items():
                            st.write(f"- **{cat}**: {count}")
                else:
                    st.info("暂无分类数据")
                
                # 监管类型分布
                st.markdown("### 📋 监管类型分布")
                if stats["regulation_distribution"]:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.bar_chart(stats["regulation_distribution"])
                    with col2:
                        for reg_type, count in stats["regulation_distribution"].items():
                            st.write(f"- **{reg_type}**: {count}")
                else:
                    st.info("暂无监管类型数据")
            
            else:
                st.error(f"❌ 获取统计信息失败: {response.json().get('detail', '未知错误')}")
        
        except requests.exceptions.ConnectionError:
            st.error(f"❌ 无法连接到 API 服务: {api_url}")
        except Exception as e:
            st.error(f"❌ 发生错误: {str(e)}")


# ============================================================================
# 标签页 4：检索测试
# ============================================================================

# with tab4:
#     st.header("检索测试")
#     st.markdown("快速测试几个常见问题")
    
#     test_questions = [
#         "商业银行资本充足率最低要求是什么？",
#         "流动性覆盖率应当不低于多少？",
#         "银行应如何开展风险管理？",
#         "信息披露有什么要求？",
#         "内部控制制度包括哪些内容？",
#     ]
    
#     for i, q in enumerate(test_questions, 1):
#         if st.button(f"🔍 {i}. {q}", use_container_width=True):
#             st.session_state.question_input = q
#             st.rerun()
    
#     st.markdown("---")
#     st.markdown("### 💡 提示")
#     st.markdown("""
#     - 点击上方问题快速测试
#     - 或在"问答"标签页输入自定义问题
#     - 系统会自动检索相关法规并生成答案
#     """)


# ============================================================================
# 页脚
# ============================================================================

st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; font-size: 12px;">
    <p>金融监管知识库 v1.0 | 基于 PostgreSQL + FAISS + LLM</p>
    <p>API 地址: {}</p>
</div>
""".format(api_url), unsafe_allow_html=True)
