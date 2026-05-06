"""
登录页面组件
Login Page Component
"""

import streamlit as st
from utils.session import save_tokens, save_user_info, set_current_page, get_api_url
from utils.api import api_login


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
    
    # 登录表单卡片
    with st.container():
        col_left, col_center, col_right = st.columns([1, 2, 1])
        
        with col_center:
            st.markdown('<div style="background: #ffffff; border-radius: 16px; padding: 32px 28px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); max-width: 380px; margin: 0 auto;">', unsafe_allow_html=True)
            
            st.markdown("#### 用户登录", unsafe_allow_html=False)
            
            username = st.text_input("用户名", placeholder="请输入用户名", key="login_username")
            password = st.text_input("密码", type="password", placeholder="请输入密码", key="login_password")
            
            st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
            
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                login_btn = st.button("登 录", type="primary", use_container_width=True)
            with col_btn2:
                register_btn = st.button("注册账号", use_container_width=True)
            
            st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
            st.markdown("<hr style='border: none; border-top: 1px solid #e2e8f0; margin: 0 0 16px 0;'>", unsafe_allow_html=True)
            
            forgot_btn = st.button("忘记密码？", use_container_width=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
    
    # 处理登录逻辑
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
                    st.success("登录成功！")
                    st.rerun()
                else:
                    st.error(f"登录失败: {result['error']}")
    
    # 处理页面跳转
    if register_btn:
        set_current_page("register")
        st.rerun()
    
    if forgot_btn:
        set_current_page("forgot_password")
        st.rerun()
