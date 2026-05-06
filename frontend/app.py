"""
金融监管知识库 - Streamlit 前端
Financial Knowledge Base Streamlit Frontend

完整的 Web UI，支持：
- 用户登录/注册
- 问答
- 文档上传
- 统计信息展示
- 知识库管理
- 准确率评估
"""

import streamlit as st
from utils.session import init_session_state, is_authenticated, set_current_page, get_api_url
from views.login import render_login_page
from views.register import render_register_page
from views.forgot_password import render_forgot_password_page
from views.dashboard import render_main_page
from styles.theme import get_all_styles


def main():
    """主程序入口"""
    # 页面配置
    st.set_page_config(
        page_title="金融监管知识库",
        page_icon="📚",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    
    # 初始化会话状态
    init_session_state()
    
    # 应用样式
    st.markdown(get_all_styles(), unsafe_allow_html=True)
    
    # 如果已认证，自动跳转到主页
    if is_authenticated():
        set_current_page("main")
    
    # 路由处理
    current_page = st.session_state.get("current_page", "login")
    
    if current_page == "login":
        render_login_page()
    elif current_page == "register":
        render_register_page()
    elif current_page == "forgot_password":
        render_forgot_password_page()
    elif current_page == "main":
        render_main_page()


if __name__ == "__main__":
    main()
