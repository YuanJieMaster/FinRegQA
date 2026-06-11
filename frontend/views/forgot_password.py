"""
忘记密码页面组件
Forgot Password Page Component
"""

import streamlit as st
from utils.session import set_current_page, get_api_url
from utils.api import api_request_password_reset
from components.ui import render_auth_brand, render_auth_card_header, mark_auth_page


def render_forgot_password_page():
    """渲染忘记密码页面"""
    mark_auth_page()

    col_brand, col_form = st.columns([1.15, 1], gap="medium")

    with col_brand:
        render_auth_brand("密码重置 · 安全验证")

    with col_form:
        st.markdown('<div class="auth-card">', unsafe_allow_html=True)
        render_auth_card_header("忘记密码", "请输入您注册时使用的邮箱地址")

        email = st.text_input("邮箱地址", placeholder="请输入注册邮箱", key="forgot_email")

        submit_btn = st.button("发送重置链接", type="primary", use_container_width=True, key="forgot_submit")

        st.markdown('<hr class="auth-divider">', unsafe_allow_html=True)

        back_btn = st.button("返回登录", use_container_width=True, key="forgot_back")

        st.markdown("</div>", unsafe_allow_html=True)

    if submit_btn:
        if not email:
            st.error("请输入邮箱地址")
        else:
            with st.spinner("发送中..."):
                result = api_request_password_reset(email, get_api_url())

                if result["success"]:
                    st.success("如果邮箱已注册，将会收到密码重置邮件")
                else:
                    st.error(f"发送失败: {result['error']}")

    if back_btn:
        set_current_page("login")
        st.rerun()
