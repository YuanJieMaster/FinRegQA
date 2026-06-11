"""
UI 组件 — 认证页布局壳
Auth page shell with split brand panel + glass card form.
"""

import streamlit as st

AUTH_FEATURES = [
    ("🔍", "智能检索", "向量 + 关键词混合检索"),
    ("📋", "法规问答", "RAG 生成，附引用依据"),
    ("📊", "知识管理", "文档导入与评估"),
]

AUTH_PAGE_MARKER = '<div class="auth-page-marker" aria-hidden="true"></div>'


def mark_auth_page():
    """标记当前为认证页，触发紧凑布局样式"""
    st.markdown(AUTH_PAGE_MARKER, unsafe_allow_html=True)


def render_auth_brand(subtitle: str = "智能问答系统"):
    """渲染认证页左侧品牌面板"""
    features_html = "".join(
        f'<li class="auth-feature-item">'
        f'<span class="auth-feature-icon">{icon}</span>'
        f"<span><strong>{title}</strong> — {desc}</span>"
        f"</li>"
        for icon, title, desc in AUTH_FEATURES
    )
    st.markdown(
        f"""
        <div class="auth-brand-panel">
            <div class="auth-brand-logo">🏛️</div>
            <h1 class="auth-brand-title">金融监管知识库</h1>
            <p class="auth-brand-tagline">{subtitle}</p>
            <ul class="auth-feature-list">{features_html}</ul>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_auth_card_header(title: str, subtitle: str):
    """渲染认证表单卡片标题"""
    st.markdown(
        f"""
        <p class="auth-card-title">{title}</p>
        <p class="auth-card-subtitle">{subtitle}</p>
        """,
        unsafe_allow_html=True,
    )
