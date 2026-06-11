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
from components.ui import render_hero_header


def render_main_page():
    """渲染主页面"""
    render_sidebar()
    render_hero_header()

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "问答",
        "上传文档",
        "统计信息",
        "知识库管理",
        "准确率评估",
    ])

    with tab1:
        render_qa_page()

    with tab2:
        render_upload_page()

    with tab3:
        render_stats_page()

    with tab4:
        render_knowledge_management_page()

    with tab5:
        render_evaluation_page()

    api_url = st.session_state.get("api_url", "http://localhost:8000")
    st.markdown(
        f"""
        <div class="footer">
            <p style="margin: 0;"><span class="footer-brand">金融监管知识库</span> · v1.0</p>
            <p style="margin: 8px 0 0 0; opacity: 0.75;">MySQL + Milvus + LLM 智能问答系统</p>
            <p style="margin: 6px 0 0 0; opacity: 0.55; font-size: 11px;">API: {api_url}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
