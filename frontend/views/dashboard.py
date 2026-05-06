"""
主页面组件
Main Page Component
"""

import streamlit as st
from components import (
    render_sidebar,
    render_qa_page,
    render_upload_page,
    render_stats_page,
    render_knowledge_management_page,
    render_evaluation_page,
)


def render_main_page():
    """渲染主页面"""
    # 侧边栏
    render_sidebar()
    
    # 主标题
    st.markdown("""
    <div class="page-header">
        <h1 class="main-title">🏛️ 金融监管知识库</h1>
        <p class="main-subtitle">基于 MySQL + Milvus + LLM 的智能问答系统</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 创建标签页
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "💬 问答",
        "📤 上传文档",
        "📊 统计信息",
        "📚 知识库管理",
        "📈 准确率评估"
    ])
    
    # 问答页面
    with tab1:
        render_qa_page()
    
    # 上传文档页面
    with tab2:
        render_upload_page()
    
    # 统计页面
    with tab3:
        render_stats_page()
    
    # 知识库管理页面
    with tab4:
        render_knowledge_management_page()
    
    # 评估页面
    with tab5:
        render_evaluation_page()
    
    # 页脚
    api_url = st.session_state.get("api_url", "http://localhost:8000")
    st.markdown(f"""
    <div class="footer">
        <p style="margin: 0;"><strong>🏛️ 金融监管知识库</strong> v1.0</p>
        <p style="margin: 0.5rem 0 0 0;">基于 MySQL + Milvus + LLM 智能问答系统</p>
        <p style="margin: 0.5rem 0 0 0; opacity: 0.7;">API 地址: {api_url}</p>
    </div>
    """, unsafe_allow_html=True)
