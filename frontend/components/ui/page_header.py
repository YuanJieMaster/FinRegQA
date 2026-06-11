"""
UI 组件 — 页面头部
Dashboard hero header component.
"""

import streamlit as st


def render_hero_header(
    title: str = "金融监管知识库",
    subtitle: str = "基于 MySQL + Milvus + LLM 的智能问答系统",
    tags: list[str] | None = None,
):
    """渲染主页面 Hero 头部"""
    if tags is None:
        tags = ["RAG 检索", "向量搜索", "流式问答", "知识库管理"]

    tags_html = "".join(f'<span class="hero-tag">{tag}</span>' for tag in tags)

    st.markdown(
        f"""
        <div class="hero-header">
            <div class="hero-badge">
                <span class="hero-badge-dot"></span>
                系统运行中
            </div>
            <h1 class="main-title">{title}</h1>
            <p class="main-subtitle">{subtitle}</p>
            <div class="hero-tags">{tags_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
