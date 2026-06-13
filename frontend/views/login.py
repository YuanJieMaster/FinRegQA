"""
登录页面组件
Login Page Component
"""

import streamlit as st
from utils.session import save_tokens, save_user_info, set_current_page, get_api_url
from utils.api import api_login
from components.ui import render_auth_brand, render_auth_card_header, mark_auth_page


def render_login_page():
    """渲染登录页面"""
    # Logo 和标题
    st.markdown("""
    <div style="text-align: center; padding-top: 80px; padding-bottom: 24px;">
        <h1 style="font-size: 28px; font-weight: 600; color: #0f172a; margin: 0 0 8px 0;">
            金融监管知识库
        </h1>
        <p style="color: #64748b; font-size: 15px; margin: 0;">智能问答系统</p>
    </div>
    """, unsafe_allow_html=True)
    mark_auth_page()

    col_brand, col_form = st.columns([0.8, 1], gap="large")

    with col_brand:
        render_auth_brand("智能问答系统 · 安全登录")

    with col_form:
        # st.markdown('<div class="auth-card">', unsafe_allow_html=True)
        # render_auth_card_header("用户登录", "")

        username = st.text_input("用户名", placeholder="请输入用户名", key="login_username")
        password = st.text_input("密码", type="password", placeholder="请输入密码", key="login_password")

        login_btn = st.button("登 录", type="primary", use_container_width=True, key="login_submit")

        st.markdown('<hr class="auth-divider">', unsafe_allow_html=True)

        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            register_btn = st.button("注册账号", use_container_width=True, key="login_register")
        with col_btn2:
            forgot_btn = st.button("忘记密码", use_container_width=True, key="login_forgot")

        # st.markdown("</div>", unsafe_allow_html=True)

    if login_btn:
        if not username or not password:
            st.error("请输入用户名和密码")
        else:
            with st.spinner("登录中..."):
                result = api_login(username, password, get_api_url())

                if result["success"]:
                    data = result["data"]
                    save_tokens(data["access_token"], data["refresh_token"])
                    save_user_info(username)
                    set_current_page("main")
                    st.toast("登录成功！", icon="✅")
                    st.rerun()
                else:
                    st.error(f"登录失败: {result['error']}")

    if register_btn:
        set_current_page("register")
        st.rerun()

    if forgot_btn:
        set_current_page("forgot_password")
        st.rerun()
