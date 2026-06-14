"""
侧边栏组件
Sidebar Component
"""

import streamlit as st
from utils.session import clear_auth, get_api_url, set_api_url


def _get_user_initial(username: str) -> str:
    return (username[:1] or "U").upper()


def render_sidebar():
    """渲染侧边栏"""
    with st.sidebar:
        st.markdown(
            """
            <div class="sidebar-brand">
                <div class="sidebar-brand-icon">🏛️</div>
                <p class="sidebar-brand-title">金融监管知识库</p>
                <p class="sidebar-brand-sub">FinReg Knowledge Base</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown('<p class="sidebar-section-title">系统配置</p>', unsafe_allow_html=True)

        api_url_input = st.text_input(
            "API 地址",
            value=get_api_url(),
            help="FastAPI 服务地址",
            key="sidebar_api_url",
        )
        set_api_url(api_url_input)

        st.markdown(
            """
            <div class="api-status api-status-connected">
                <span class="api-status-dot"></span>
                <span>API 已配置</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("---")

        user_info = st.session_state.get("user_info")
        if user_info:
            username = user_info.get("username", "用户")
            initial = _get_user_initial(username)
            st.markdown(
                f"""
                <div class="sidebar-user-card">
                    <div class="sidebar-avatar">{initial}</div>
                    <p class="sidebar-user-name">{username}</p>
                    <p class="sidebar-user-role">{user_info.get('role', '普通用户')}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

        if st.button("退出登录", use_container_width=True, key="sidebar_logout"):
            clear_auth()
            st.rerun()

        st.markdown("---")

        st.markdown('<p class="sidebar-section-title">使用说明</p>', unsafe_allow_html=True)
        st.markdown(
            """
            <div class="sidebar-help-item">💬 <strong>问答</strong> — 输入监管问题，检索法规并生成答案</div>
            <div class="sidebar-help-item">📤 <strong>上传</strong> — 支持 PDF、DOCX、TXT、图片 OCR</div>
            <div class="sidebar-help-item">📊 <strong>统计</strong> — 查看知识库文档与向量规模</div>
            <div class="sidebar-help-item">🧪 <strong>人工评测</strong> — 对 AI 回答进行人工标注，结果本地保存</div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("---")

        st.markdown(
            """
            <div style="text-align: center; color: #64748b; font-size: 11px; padding: 8px 0;">
                <p style="margin: 0;">v1.0 · Streamlit</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
