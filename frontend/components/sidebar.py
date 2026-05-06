"""
侧边栏组件
Sidebar Component
"""

import streamlit as st
from utils.session import clear_auth, get_api_url, set_api_url


def render_sidebar():
    """渲染侧边栏"""
    with st.sidebar:
        # 系统配置标题
        st.markdown("""
        <div style="text-align: center; padding: 1rem 0;">
            <h2 style="color: #fff; margin: 0;">⚙️ 系统配置</h2>
        </div>
        """, unsafe_allow_html=True)
        
        # API 地址配置
        api_url_input = st.text_input(
            "API 地址",
            value=get_api_url(),
            help="FastAPI 服务地址"
        )
        st.session_state.api_url = api_url_input
        st.session_state.api_url_input = api_url_input
        
        st.markdown("---")
        
        # 用户信息显示
        user_info = st.session_state.get("user_info")
        if user_info:
            st.markdown(f"""
            <div class="sidebar-user-card">
                <div style="font-size: 48px; margin-bottom: 8px;">👤</div>
                <p class="sidebar-user-name">{user_info.get('username', '用户')}</p>
                <p class="sidebar-user-role">{user_info.get('role', '普通用户')}</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("### 👤 用户")
        
        # 退出登录按钮
        if st.button("🚪 退出登录", use_container_width=True):
            clear_auth()
            st.rerun()
        
        st.markdown("---")
        
        # 使用说明
        st.markdown("### 📖 使用说明")
        st.markdown("""
        1. **问答**：输入金融监管相关问题，系统会检索法规并生成答案
        2. **上传文档**：支持 PDF、DOCX、TXT、图片格式（图片使用 OCR 识别）
        3. **统计**：查看知识库中的文档和知识点数量
        """)
        
        st.markdown("---")
        
        # 版本信息
        st.markdown("""
        <div style="text-align: center; color: #64748b; font-size: 12px; padding: 12px 0;">
            <p style="margin: 0;">金融监管知识库 v1.0</p>
            <p style="margin: 4px 0 0 0;">Powered by Streamlit</p>
        </div>
        """, unsafe_allow_html=True)
