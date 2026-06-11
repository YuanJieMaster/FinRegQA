"""
注册页面组件
Register Page Component
"""

import streamlit as st
from utils.session import set_current_page, get_api_url
from utils.api import api_register
from components.ui import render_auth_brand, render_auth_card_header, mark_auth_page


def render_register_page():
    """渲染注册页面"""
    mark_auth_page()

    col_brand, col_form = st.columns([1.15, 1], gap="medium")

    with col_brand:
        render_auth_brand("创建账号 · 开始使用")

    with col_form:
        st.markdown('<div class="auth-card">', unsafe_allow_html=True)
        render_auth_card_header("用户注册", "填写以下信息创建新账号")

        username = st.text_input("用户名", placeholder="6-20位字母、数字或下划线", key="register_username")
        email = st.text_input("邮箱", placeholder="请输入邮箱地址", key="register_email")
        password = st.text_input("密码", type="password", placeholder="至少8位，包含字母和数字", key="register_password")
        confirm_password = st.text_input(
            "确认密码", type="password", placeholder="再次输入密码", key="register_confirm_password"
        )

        submit_btn = st.button("注 册", type="primary", use_container_width=True, key="register_submit")

        st.markdown('<hr class="auth-divider">', unsafe_allow_html=True)

        back_btn = st.button("返回登录", use_container_width=True, key="register_back")

        st.markdown("</div>", unsafe_allow_html=True)

    if submit_btn:
        if not username or not email or not password or not confirm_password:
            st.error("请填写所有字段")
        elif password != confirm_password:
            st.error("两次输入的密码不一致")
        else:
            with st.spinner("注册中..."):
                result = api_register(username, email, password, confirm_password, get_api_url())

                if result["success"]:
                    st.success("注册成功！请登录")
                    set_current_page("login")
                    st.rerun()
                else:
                    st.error(f"注册失败: {result['error']}")

    if back_btn:
        set_current_page("login")
        st.rerun()
