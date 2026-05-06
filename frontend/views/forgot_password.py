"""
忘记密码页面组件
Forgot Password Page Component
"""

import streamlit as st
from utils.session import set_current_page, get_api_url
from utils.api import api_request_password_reset


def render_forgot_password_page():
    """渲染忘记密码页面"""
    # Logo 和标题
    st.markdown("""
    <div style="text-align: center; padding-top: 100px; padding-bottom: 24px;">
        <h1 style="font-size: 28px; font-weight: 600; color: #0f172a; margin: 0 0 8px 0;">
            金融监管知识库
        </h1>
        <p style="color: #64748b; font-size: 15px; margin: 0;">重置密码</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.container():
        col_left, col_center, col_right = st.columns([1, 2, 1])
        
        with col_center:
            st.markdown('<div style="background: #ffffff; border-radius: 16px; padding: 32px 28px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); max-width: 380px; margin: 0 auto;">', unsafe_allow_html=True)
            
            st.markdown("#### 忘记密码", unsafe_allow_html=False)
            st.markdown("<p style='color: #64748b; font-size: 14px; margin-bottom: 20px;'>请输入您注册的邮箱地址</p>", unsafe_allow_html=True)
            
            email = st.text_input("邮箱地址", placeholder="请输入注册邮箱", key="forgot_email")
            
            st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
            
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                submit_btn = st.button("发送重置链接", type="primary", use_container_width=True)
            with col_btn2:
                back_btn = st.button("返回登录", use_container_width=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
    
    # 处理提交逻辑
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
    
    # 处理返回
    if back_btn:
        set_current_page("login")
        st.rerun()
