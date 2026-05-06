"""
注册页面组件
Register Page Component
"""

import streamlit as st
from utils.session import set_current_page, get_api_url
from utils.api import api_register


def render_register_page():
    """渲染注册页面"""
    # Logo 和标题
    st.markdown("""
    <div style="text-align: center; padding-top: 60px; padding-bottom: 24px;">
        <h1 style="font-size: 28px; font-weight: 600; color: #0f172a; margin: 0 0 8px 0;">
            金融监管知识库
        </h1>
        <p style="color: #64748b; font-size: 15px; margin: 0;">创建新账号</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.container():
        col_left, col_center, col_right = st.columns([1, 2, 1])
        
        with col_center:
            st.markdown('<div style="background: #ffffff; border-radius: 16px; padding: 32px 28px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); max-width: 380px; margin: 0 auto;">', unsafe_allow_html=True)
            
            st.markdown("#### 用户注册", unsafe_allow_html=False)
            
            username = st.text_input("用户名", placeholder="6-20位字母、数字或下划线", key="register_username")
            email = st.text_input("邮箱", placeholder="请输入邮箱地址", key="register_email")
            password = st.text_input("密码", type="password", placeholder="至少8位，包含字母和数字", key="register_password")
            confirm_password = st.text_input("确认密码", type="password", placeholder="再次输入密码", key="register_confirm_password")
            
            st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
            
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                submit_btn = st.button("注 册", type="primary", use_container_width=True)
            with col_btn2:
                back_btn = st.button("返回登录", use_container_width=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
    
    # 处理注册逻辑
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
    
    # 处理返回
    if back_btn:
        set_current_page("login")
        st.rerun()
