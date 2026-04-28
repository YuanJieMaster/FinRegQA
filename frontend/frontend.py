"""
金融知识库 Streamlit 前端
Financial Knowledge Base Streamlit Frontend

完整的 Web UI，支持：
- 用户登录/注册
- 问答
- 文档上传
- 统计信息展示
"""

import streamlit as st
import requests
import json
from pathlib import Path

# HTTP 请求超时（秒）
REQUEST_TIMEOUT_ANSWER = 180
REQUEST_TIMEOUT_INGEST = 600
REQUEST_TIMEOUT_STATS = 120

REGION_OPTIONS = [
    "全国",
    "浙江省",
    "江苏省",
    "上海市",
    "北京市",
    "广东省",
    "其他（自定义）",
]


def init_session_state():
    """初始化 session_state"""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "access_token" not in st.session_state:
        st.session_state.access_token = None
    if "refresh_token" not in st.session_state:
        st.session_state.refresh_token = None
    if "user_info" not in st.session_state:
        st.session_state.user_info = None
    if "current_page" not in st.session_state:
        st.session_state.current_page = "login"


def save_tokens(access_token: str, refresh_token: str):
    """保存令牌到 session_state"""
    st.session_state.access_token = access_token
    st.session_state.refresh_token = refresh_token
    st.session_state.authenticated = True


def clear_auth():
    """清除认证状态"""
    st.session_state.authenticated = False
    st.session_state.access_token = None
    st.session_state.refresh_token = None
    st.session_state.user_info = None
    st.session_state.current_page = "login"


# 页面配置
st.set_page_config(
    page_title="金融监管知识库",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_session_state()

# 自定义样式
st.markdown("""
<style>
    /* 全局样式 */
    .main {
        padding: 0;
    }
    
    /* 隐藏默认元素 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    div[data-testid="stDecoration"] {
        background-image: none;
        height: 0px;
    }
    
    /* 页面背景 */
    .stApp {
        background: #f1f5f9;
    }
    
    /* 登录/注册容器 */
    .auth-wrapper {
        display: flex;
        justify-content: center;
        align-items: flex-start;
        min-height: 100vh;
        padding: 60px 20px 40px;
    }
    
    .auth-card {
        background: #ffffff;
        border-radius: 16px;
        padding: 40px 36px;
        width: 100%;
        max-width: 380px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1), 0 1px 2px rgba(0, 0, 0, 0.06);
    }
    
    .auth-header {
        text-align: center;
        margin-bottom: 32px;
    }
    
    .auth-header h1 {
        font-size: 24px;
        font-weight: 600;
        color: #0f172a;
        margin: 0 0 8px 0;
    }
    
    .auth-header p {
        color: #64748b;
        font-size: 14px;
        margin: 0;
    }
    
    /* 表单样式 */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 12px 14px;
        font-size: 15px;
    }
    
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: #6366f1;
        box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
        background-color: #fff;
    }
    
    /* 主标题样式 */
    .main-title {
        font-size: 28px;
        font-weight: 600;
        color: #0f172a;
        text-align: center;
        margin: 0 0 8px 0;
    }
    
    .main-subtitle {
        text-align: center;
        color: #64748b;
        font-size: 15px;
        margin: 0 0 24px 0;
    }
    
    /* 标签页样式 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background-color: transparent;
        padding: 0;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 10px 20px;
        font-weight: 500;
        color: #64748b;
        background-color: transparent;
        border-bottom: 2px solid transparent;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        color: #1e293b;
        background-color: rgba(99, 102, 241, 0.05);
    }
    
    .stTabs [aria-selected="true"] {
        color: #6366f1 !important;
        background-color: transparent !important;
        border-bottom: 2px solid #6366f1;
    }
    
    /* 答案框样式 */
    .answer-box {
        background: #ffffff;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        margin: 16px 0;
        font-size: 15px;
        line-height: 1.7;
        color: #334155;
    }
    
    /* 引用框样式 */
    .reference-box {
        background: #f8fafc;
        padding: 16px;
        border-radius: 10px;
        margin: 8px 0;
        border: 1px solid #e2e8f0;
    }
    
    /* 成功提示框 */
    .success-box {
        background: #f0fdf4;
        padding: 16px;
        border-radius: 10px;
        color: #166534;
        margin: 16px 0;
        border: 1px solid #bbf7d0;
    }
    
    /* 错误提示框 */
    .error-box {
        background: #fef2f2;
        padding: 16px;
        border-radius: 10px;
        color: #991b1b;
        margin: 16px 0;
        border: 1px solid #fecaca;
    }
    
    /* 侧边栏样式 */
    [data-testid="stSidebar"] {
        background: #0f172a;
        padding: 24px 20px;
    }
    
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] h4 {
        color: #f8fafc;
    }
    
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span {
        color: #94a3b8;
    }
    
    /* 统计卡片样式 */
    [data-testid="stMetric"] {
        background: #ffffff;
        border-radius: 12px;
        padding: 20px;
        border: 1px solid #e2e8f0;
    }
    
    [data-testid="stMetricLabel"] {
        color: #64748b;
        font-weight: 500;
        font-size: 13px;
    }
    
    [data-testid="stMetricValue"] {
        color: #0f172a;
        font-weight: 700;
        font-size: 28px;
    }
    
    /* 按钮样式 */
    .stButton > button {
        border-radius: 8px;
        padding: 10px 20px;
        font-weight: 500;
        border: none;
    }
    
    /* 文件上传器样式 */
    [data-testid="stFileUploader"] {
        background: #f8fafc;
        border-radius: 12px;
        padding: 24px;
        border: 2px dashed #cbd5e1;
    }
    
    /* 选择框样式 */
    .stSelectbox > div > div {
        background-color: #f8fafc;
        border-radius: 8px;
        border: 1px solid #e2e8f0;
    }
    
    /* 分隔线样式 */
    hr {
        border: none;
        height: 1px;
        background: #e2e8f0;
        margin: 24px 0;
    }
    
    /* 展开器样式 */
    .streamlit-expanderHeader {
        background: #f8fafc;
        border-radius: 8px;
        border: 1px solid #e2e8f0;
        font-weight: 500;
    }
    
    .streamlit-expanderContent {
        background: #ffffff;
        border-radius: 0 0 8px 8px;
        border: 1px solid #e2e8f0;
        border-top: none;
    }
    
    /* 图表容器 */
    [data-testid="stVegaLiteChart"] {
        background: #ffffff;
        border-radius: 12px;
        padding: 16px;
        border: 1px solid #e2e8f0;
    }
    
    /* 页脚样式 */
    .footer {
        text-align: center;
        padding: 24px 0 12px;
        color: #94a3b8;
        font-size: 12px;
    }
    
    /* section标题 */
    .section-title {
        font-size: 16px;
        font-weight: 600;
        color: #0f172a;
        margin: 0 0 16px 0;
    }
    
    /* 滚动条样式 */
    ::-webkit-scrollbar {
        width: 6px;
    }
    
    ::-webkit-scrollbar-track {
        background: #f1f5f9;
    }
    
    ::-webkit-scrollbar-thumb {
        background: #cbd5e1;
        border-radius: 3px;
    }
    
    /* section card */
    .section-card {
        background: #ffffff;
        border-radius: 12px;
        padding: 24px;
        border: 1px solid #e2e8f0;
        margin-bottom: 16px;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================================
# API 辅助函数
# ============================================================================

def get_api_url() -> str:
    """获取 API 地址"""
    if "api_url" in st.session_state:
        return st.session_state.api_url
    return "http://localhost:8000"


def call_api(endpoint: str, method: str = "GET", data: dict = None, files: dict = None, requires_auth: bool = False):
    """调用 API"""
    url = f"{get_api_url()}/api/v1{endpoint}"
    headers = {}
    
    if requires_auth and st.session_state.access_token:
        headers["Authorization"] = f"Bearer {st.session_state.access_token}"
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT_STATS)
        elif method == "POST":
            if files:
                response = requests.post(url, headers=headers, data=data, files=files, timeout=REQUEST_TIMEOUT_INGEST)
            else:
                response = requests.post(url, headers=headers, json=data, timeout=REQUEST_TIMEOUT_ANSWER)
        elif method == "PUT":
            response = requests.put(url, headers=headers, json=data, timeout=REQUEST_TIMEOUT_ANSWER)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers, timeout=REQUEST_TIMEOUT_STATS)
        return response
    except requests.exceptions.ConnectionError:
        return None


# ============================================================================
# 登录页面
# ============================================================================

def show_login_page():
    """显示登录页面"""
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
    
    if login_btn:
        if not username or not password:
            st.error("请输入用户名和密码")
        else:
            with st.spinner("登录中..."):
                try:
                    response = requests.post(
                        f"{get_api_url()}/api/v1/auth/login",
                        data={"username": username, "password": password},
                        timeout=30
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        save_tokens(result["access_token"], result["refresh_token"])
                        st.session_state.user_info = {"username": username}
                        st.session_state.current_page = "main"
                        st.success("登录成功！")
                        st.rerun()
                    else:
                        error_detail = response.json().get("detail", "登录失败")
                        st.error(f"登录失败: {error_detail}")
                except requests.exceptions.ConnectionError:
                    st.error("无法连接到服务器，请确保服务已启动")
                except Exception as e:
                    st.error(f"登录错误: {str(e)}")
    
    if register_btn:
        st.session_state.current_page = "register"
        st.rerun()
    
    if forgot_btn:
        st.session_state.current_page = "forgot_password"
        st.rerun()


# ============================================================================
# 注册页面
# ============================================================================

def show_register_page():
    """显示注册页面"""
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
    
    if submit_btn:
        if not username or not email or not password or not confirm_password:
            st.error("请填写所有字段")
        elif password != confirm_password:
            st.error("两次输入的密码不一致")
        else:
            with st.spinner("注册中..."):
                try:
                    response = requests.post(
                        f"{get_api_url()}/api/v1/auth/register",
                        json={
                            "username": username,
                            "email": email,
                            "password": password,
                            "confirm_password": confirm_password
                        },
                        timeout=30
                    )
                    
                    if response.status_code == 200:
                        st.success("注册成功！请登录")
                        st.session_state.current_page = "login"
                        st.rerun()
                    else:
                        error_detail = response.json().get("detail", "注册失败")
                        st.error(f"注册失败: {error_detail}")
                except requests.exceptions.ConnectionError:
                    st.error("无法连接到服务器")
                except Exception as e:
                    st.error(f"注册错误: {str(e)}")
    
    if back_btn:
        st.session_state.current_page = "login"
        st.rerun()


# ============================================================================
# 忘记密码页面
# ============================================================================

def show_forgot_password_page():
    """显示忘记密码页面"""
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
    
    if submit_btn:
        if not email:
            st.error("请输入邮箱地址")
        else:
            with st.spinner("发送中..."):
                try:
                    response = requests.post(
                        f"{get_api_url()}/api/v1/auth/password/reset-request",
                        json={"email": email},
                        timeout=30
                    )
                    
                    if response.status_code == 200:
                        st.success("如果邮箱已注册，将会收到密码重置邮件")
                    else:
                        error_detail = response.json().get("detail", "发送失败")
                        st.error(f"发送失败: {error_detail}")
                except requests.exceptions.ConnectionError:
                    st.error("无法连接到服务器")
                except Exception as e:
                    st.error(f"错误: {str(e)}")
    
    if back_btn:
        st.session_state.current_page = "login"
        st.rerun()


# ============================================================================
# 主页面
# ============================================================================

def show_main_page():
    """显示主页面"""
    api_url = st.session_state.get("api_url_input", "http://localhost:8000")
    st.session_state.api_url = api_url
    
    # 侧边栏配置
    with st.sidebar:
        st.markdown("""
        <div style="text-align: center; padding: 1rem 0;">
            <h2 style="color: #fff; margin: 0;">⚙️ 系统配置</h2>
        </div>
        """, unsafe_allow_html=True)
        
        api_url_input = st.text_input(
            "API 地址",
            value=api_url,
            help="FastAPI 服务地址"
        )
        st.session_state.api_url_input = api_url_input
        st.session_state.api_url = api_url_input
        
        st.markdown("---")
        
        # 用户信息显示
        if st.session_state.user_info:
            st.markdown(f"""
            <div style="background: rgba(255,255,255,0.1); padding: 1rem; border-radius: 12px; text-align: center;">
                <h3 style="color: #fff; margin: 0;">👤 {st.session_state.user_info.get('username', '用户')}</h3>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("### 👤 用户")
        
        if st.button("🚪 退出登录", use_container_width=True):
            clear_auth()
            st.rerun()
        
        st.markdown("---")
        st.markdown("### 📖 使用说明")
        st.markdown("""
        1. **问答**：输入金融监管相关问题，系统会检索法规并生成答案
        2. **上传文档**：支持 PDF、DOCX、TXT 格式
        3. **统计**：查看知识库中的文档和知识点数量
        """)
    
    # 主标题
    st.markdown("""
    <div class="page-header">
        <h1 class="main-title">🏛️ 金融监管知识库</h1>
        <p class="main-subtitle">基于 MySQL + Milvus + LLM 的智能问答系统</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 创建标签页
    tab1, tab2, tab3, tab4 = st.tabs(["💬 问答", "📤 上传文档", "📊 统计信息", "📚 知识库管理"])
    
    # ============================================================================
    # 标签页 1：问答
    # ============================================================================
    
    with tab1:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        
        st.markdown('<p class="section-title">💬 智能问答</p>', unsafe_allow_html=True)
        
        col1, col2 = st.columns([4, 1])
        
        with col1:
            question = st.text_area(
                "输入问题",
                placeholder="例如：商业银行资本充足率最低要求是什么？",
                height=80,
                key="question_input"
            )
            question_region_option = st.selectbox(
                "地区筛选",
                options=REGION_OPTIONS,
                index=0,
                help="优先检索所选地区法规",
                key="question_region_select",
            )
            question_region_custom = ""
            if question_region_option == "其他（自定义）":
                question_region_custom = st.text_input(
                    "自定义地区",
                    placeholder="例如：宁波市",
                    key="question_region_custom_input",
                )
            question_region = question_region_custom.strip() if question_region_option == "其他（自定义）" else question_region_option
            if question_region == "全国":
                question_region = None
            search_mode = st.selectbox(
                "Search mode",
                options=["hybrid", "vector", "keyword"],
                index=0,
                format_func=lambda value: {
                    "hybrid": "Hybrid",
                    "vector": "Vector",
                    "keyword": "Keyword",
                }[value],
                help="Hybrid combines vector semantic search and keyword search.",
                key="question_search_mode_select",
            )
        
        with col2:
            st.write("")
            st.write("")
            submit_btn = st.button("提交", use_container_width=True, type="primary")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        if submit_btn and question.strip():
            with st.spinner("正在处理..."):
                try:
                    response = requests.post(
                        f"{api_url_input}/api/knowledge/answer",
                        json={
                            "question": question,
                            "region": question_region or None,
                            "mode": search_mode,
                        },
                        timeout=REQUEST_TIMEOUT_ANSWER,
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        
                        st.markdown('<p class="section-title">📝 回答</p>', unsafe_allow_html=True)
                        st.markdown(f'<div class="answer-box">{result["answer"]}</div>', unsafe_allow_html=True)
                        
                        if result.get("references"):
                            st.markdown('<p class="section-title">📚 参考依据</p>', unsafe_allow_html=True)
                            for i, ref in enumerate(result["references"], 1):
                                with st.expander(f"依据 {i}: {ref.get('document_name', '未知文档')}"):
                                    col1, col2 = st.columns([4, 1])
                                    with col1:
                                        st.markdown(f"**条款**: {ref.get('article_number', '-')} {ref.get('section_number', '')}")
                                        st.markdown(f"**分类**: {ref.get('category', '-')} | **地区**: {ref.get('region', '-')}")
                                        st.markdown(f"**内容**: {ref.get('content', '')[:200]}...")
                                    with col2:
                                        sim = ref.get('similarity')
                                        if isinstance(sim, (int, float)):
                                            st.metric("相似度", f"{sim:.3f}")
                        else:
                            st.info("未找到相关法规依据")
                    
                    else:
                        st.error(f"错误: {response.json().get('detail', '未知错误')}")
                
                except requests.exceptions.ConnectionError:
                    st.error(f"无法连接到 API 服务: {api_url_input}")
                except Exception as e:
                    st.error(f"发生错误: {str(e)}")
        
        elif submit_btn:
            st.warning("请输入问题")
    
    
    # ============================================================================
    # 标签页 2：上传文档
    # ============================================================================
    
    with tab2:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        
        st.markdown('<p class="section-title">📤 上传文档</p>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            uploaded_file = st.file_uploader(
                "选择文件",
                type=["pdf", "docx", "doc", "txt"],
                help="支持 PDF、Word、TXT 格式"
            )
            
            category = st.selectbox(
                "文档分类",
                ["风险管理", "资本管理", "流动性管理", "内部控制", "信息披露", "其他"]
            )
        
        with col2:
            region_option = st.selectbox(
                "适用地区",
                options=REGION_OPTIONS,
                index=0,
                key="ingest_region_select",
            )
            region_custom = ""
            if region_option == "其他（自定义）":
                region_custom = st.text_input(
                    "自定义地区",
                    placeholder="例如：杭州市",
                    key="ingest_region_custom_input",
                )
            region = region_custom.strip() if region_option == "其他（自定义）" else region_option
        
            regulation_type = st.text_input(
                "监管类型",
                placeholder="例如：商业银行监管",
            )
            
            source = st.text_input(
                "文档来源",
                placeholder="例如：中国银保监会",
            )
        
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            min_chunk_size = st.number_input(
                "最小分块大小",
                value=1,
                min_value=1,
            )
        
        with col2:
            keep_separator = st.checkbox("保留分隔符", value=True)
        
        with col3:
            batch_size = st.number_input(
                "批处理大小",
                value=100,
                min_value=10,
            )
        
        if st.button("上传并导入", type="primary", use_container_width=True):
            if not uploaded_file:
                st.error("请选择文件")
            elif not regulation_type.strip():
                st.error("请输入监管类型")
            else:
                with st.spinner("正在处理文件..."):
                    try:
                        files = {"file": (uploaded_file.name, uploaded_file.getbuffer())}
                        data = {
                            "category": category,
                            "regulation_type": regulation_type,
                            "region": region or None,
                            "source": source or None,
                            "min_chunk_size": min_chunk_size,
                            "keep_separator": keep_separator,
                            "batch_size": batch_size,
                        }
                        
                        response = requests.post(
                            f"{api_url_input}/api/knowledge/ingest",
                            files=files,
                            data=data,
                            timeout=REQUEST_TIMEOUT_INGEST,
                        )
                        
                        if response.status_code == 200:
                            result = response.json()
                            st.markdown(f'<div class="success-box">文档导入成功！</div>', unsafe_allow_html=True)
                            
                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                st.metric("文档 ID", result["document_id"])
                            with col2:
                                st.metric("分块数", result["chunk_count"])
                            with col3:
                                st.metric("成功", result["success"])
                            with col4:
                                st.metric("失败", result["failed"])
                        else:
                            st.error(f"导入失败: {response.json().get('detail', '未知错误')}")
                    
                    except requests.exceptions.ConnectionError:
                        st.error("无法连接到 API 服务")
                    except Exception as e:
                        st.error(f"发生错误: {str(e)}")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    
    # ============================================================================
    # 标签页 3：统计信息
    # ============================================================================
    
    with tab3:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        
        col_header1, col_header2 = st.columns([4, 1])
        with col_header1:
            st.markdown('<p class="section-title">📊 知识库统计</p>', unsafe_allow_html=True)
        with col_header2:
            if st.button("刷新", use_container_width=True):
                st.rerun()
        
        with st.spinner("加载中..."):
            try:
                response = requests.get(
                    f"{api_url_input}/api/knowledge/stats", timeout=REQUEST_TIMEOUT_STATS
                )
                
                if response.status_code == 200:
                    stats = response.json()
                    
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("文档数", stats["document_count"])
                    
                    with col2:
                        st.metric("知识点数", stats["knowledge_count"])
                    
                    with col3:
                        st.metric("向量数", stats.get("milvus_vector_count", stats.get("knowledge_count", 0)))
                    
                    with col4:
                        if stats["knowledge_count"] > 0:
                            avg_per_doc = stats["knowledge_count"] / max(stats["document_count"], 1)
                            st.metric("平均/文档", f"{avg_per_doc:.1f}")
                    
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    if stats["category_distribution"]:
                        st.markdown('<div class="section-card">', unsafe_allow_html=True)
                        st.markdown('<p class="section-title">📂 分类分布</p>', unsafe_allow_html=True)
                        col1, col2 = st.columns(2)
                        with col1:
                            st.bar_chart(stats["category_distribution"])
                        with col2:
                            for cat, count in stats["category_distribution"].items():
                                st.write(f"- **{cat}**: {count}")
                        st.markdown('</div>', unsafe_allow_html=True)
                    
                    if stats["regulation_distribution"]:
                        st.markdown('<div class="section-card">', unsafe_allow_html=True)
                        st.markdown('<p class="section-title">📋 监管类型分布</p>', unsafe_allow_html=True)
                        col1, col2 = st.columns(2)
                        with col1:
                            st.bar_chart(stats["regulation_distribution"])
                        with col2:
                            for reg_type, count in stats["regulation_distribution"].items():
                                st.write(f"- **{reg_type}**: {count}")
                        st.markdown('</div>', unsafe_allow_html=True)
                    
                    if stats.get("region_distribution"):
                        st.markdown('<div class="section-card">', unsafe_allow_html=True)
                        st.markdown('<p class="section-title">🌍 地区分布</p>', unsafe_allow_html=True)
                        col1, col2 = st.columns(2)
                        with col1:
                            st.bar_chart(stats["region_distribution"])
                        with col2:
                            for region_name, count in stats["region_distribution"].items():
                                st.write(f"- **{region_name}**: {count}")
                        st.markdown('</div>', unsafe_allow_html=True)
                
                else:
                    st.error(f"获取统计信息失败: {response.json().get('detail', '未知错误')}")
            
            except requests.exceptions.ConnectionError:
                st.error(f"无法连接到 API 服务: {api_url_input}")
            except Exception as e:
                st.error(f"发生错误: {str(e)}")


    # ============================================================================
    # 标签页 4：知识库管理
    # ============================================================================

    with tab4:
        # 子标签页：知识点管理和文档管理
        sub_tab1, sub_tab2 = st.tabs(["📝 知识点管理", "📄 文档管理"])

        # ---------------------------------------------------------
        # 子标签页 1：知识点管理
        # ---------------------------------------------------------
        with sub_tab1:
            st.markdown('<div class="section-card">', unsafe_allow_html=True)

            # 筛选区域
            st.markdown('<p class="section-title">🔍 筛选条件</p>', unsafe_allow_html=True)

            col_filter1, col_filter2, col_filter3 = st.columns(3)

            with col_filter1:
                filter_category = st.selectbox(
                    "分类",
                    options=["全部"] + REGION_OPTIONS[:-1],
                    key="kb_filter_category"
                )
                filter_category_value = None if filter_category == "全部" else filter_category

            with col_filter2:
                filter_region = st.selectbox(
                    "地区",
                    options=["全部"] + REGION_OPTIONS,
                    key="kb_filter_region"
                )
                filter_region_value = None if filter_region == "全部" else filter_region

            with col_filter3:
                filter_search = st.text_input(
                    "关键词搜索",
                    placeholder="搜索内容...",
                    key="kb_filter_search"
                )

            col_page1, col_page2 = st.columns([4, 1])
            with col_page1:
                page_number = st.number_input(
                    "页码",
                    min_value=1,
                    value=st.session_state.get("kb_page", 1),
                    step=1,
                    key="kb_page_input"
                )
                st.session_state.kb_page = page_number
            with col_page2:
                page_size = st.selectbox(
                    "每页条数",
                    options=[10, 20, 50, 100],
                    index=1,
                    key="kb_page_size"
                )

            if st.button("搜索", key="kb_search_btn", use_container_width=True):
                st.session_state.kb_page = 1
                st.rerun()

            st.markdown("---")

            # 加载知识点列表
            with st.spinner("加载知识点列表..."):
                try:
                    params = {
                        "page": st.session_state.get("kb_page", 1),
                        "page_size": page_size,
                    }
                    if filter_category_value:
                        params["category"] = filter_category_value
                    if filter_region_value:
                        params["region"] = filter_region_value
                    if filter_search:
                        params["search"] = filter_search

                    response = requests.get(
                        f"{api_url_input}/api/knowledge/list",
                        params=params,
                        timeout=REQUEST_TIMEOUT_STATS
                    )

                    if response.status_code == 200:
                        data = response.json()
                        knowledge_items = data.get("items", [])
                        total = data.get("total", 0)
                        total_pages = data.get("total_pages", 1)

                        st.markdown(f"""
                        <div style="display: flex; justify-content: space-between; align-items: center; margin: 16px 0;">
                            <span style="color: #64748b;">共找到 <strong style="color: #0f172a;">{total}</strong> 条知识点</span>
                            <span style="color: #64748b;">第 {st.session_state.get('kb_page', 1)} / {total_pages} 页</span>
                        </div>
                        """, unsafe_allow_html=True)

                        if knowledge_items:
                            # 显示知识点列表
                            for idx, item in enumerate(knowledge_items):
                                item_id = item.get("id", 0)
                                with st.expander(
                                    f"**知识点 #{item_id}** | {item.get('category', '未分类')} | {item.get('region', '全国')}",
                                    expanded=False
                                ):
                                    # 显示知识点详情
                                    col_view1, col_view2, col_view3 = st.columns([6, 2, 2])
                                    with col_view1:
                                        st.markdown(f"**内容预览**: {item.get('content', '')[:200]}...")
                                        if len(item.get('content', '')) > 200:
                                            with st.expander("查看完整内容"):
                                                st.text(item.get('content', ''))
                                    with col_view2:
                                        st.write(f"**条款**: {item.get('article_number', '-')} {item.get('section_number', '')}")
                                        st.write(f"**监管类型**: {item.get('regulation_type', '-')}")
                                        st.write(f"**文档**: {item.get('document_name', '-')}")
                                    with col_view3:
                                        st.write(f"**创建时间**: {item.get('created_at', '-')}")
                                        st.write(f"**更新时间**: {item.get('updated_at', '-')}")

                                    # 编辑和删除按钮
                                    st.markdown("---")
                                    col_btn_edit, col_btn_del = st.columns(2)

                                    with col_btn_edit:
                                        if st.button("编辑", key=f"edit_{item_id}", use_container_width=True):
                                            st.session_state[f"edit_mode_{item_id}"] = True

                                    with col_btn_del:
                                        if st.button("删除", key=f"delete_{item_id}", use_container_width=True):
                                            st.session_state[f"confirm_delete_{item_id}"] = True

                                    # 删除确认对话框
                                    if st.session_state.get(f"confirm_delete_{item_id}", False):
                                        st.warning(f"确定要删除知识点 #{item_id} 吗？此操作不可恢复！")
                                        col_confirm_yes, col_confirm_no = st.columns(2)
                                        with col_confirm_yes:
                                            if st.button("确认删除", key=f"confirm_yes_{item_id}", type="primary", use_container_width=True):
                                                try:
                                                    del_response = requests.delete(
                                                        f"{api_url_input}/api/knowledge/delete/{item_id}",
                                                        timeout=30
                                                    )
                                                    if del_response.status_code == 200:
                                                        st.success("删除成功！")
                                                        st.session_state[f"confirm_delete_{item_id}"] = False
                                                        st.rerun()
                                                    else:
                                                        st.error(f"删除失败: {del_response.json().get('detail', '未知错误')}")
                                                except Exception as e:
                                                    st.error(f"删除错误: {str(e)}")
                                        with col_confirm_no:
                                            if st.button("取消", key=f"confirm_no_{item_id}", use_container_width=True):
                                                st.session_state[f"confirm_delete_{item_id}"] = False
                                                st.rerun()

                                    # 编辑表单
                                    if st.session_state.get(f"edit_mode_{item_id}", False):
                                        st.markdown("---")
                                        st.markdown("**编辑知识点**")

                                        edit_category = st.text_input(
                                            "分类",
                                            value=item.get('category') or "",
                                            key=f"edit_category_{item_id}"
                                        )
                                        edit_region = st.text_input(
                                            "地区",
                                            value=item.get('region') or "",
                                            key=f"edit_region_{item_id}"
                                        )
                                        edit_regulation_type = st.text_input(
                                            "监管类型",
                                            value=item.get('regulation_type') or "",
                                            key=f"edit_regulation_type_{item_id}"
                                        )
                                        edit_article = st.text_input(
                                            "条款编号",
                                            value=item.get('article_number') or "",
                                            key=f"edit_article_{item_id}"
                                        )
                                        edit_section = st.text_input(
                                            "章节编号",
                                            value=item.get('section_number') or "",
                                            key=f"edit_section_{item_id}"
                                        )
                                        edit_content = st.text_area(
                                            "内容",
                                            value=item.get('content') or "",
                                            height=150,
                                            key=f"edit_content_{item_id}"
                                        )

                                        col_save, col_cancel = st.columns(2)
                                        with col_save:
                                            if st.button("保存修改", key=f"save_{item_id}", type="primary", use_container_width=True):
                                                try:
                                                    update_data = {
                                                        "category": edit_category,
                                                        "region": edit_region,
                                                        "regulation_type": edit_regulation_type,
                                                        "article_number": edit_article,
                                                        "section_number": edit_section,
                                                        "content": edit_content,
                                                    }
                                                    update_response = requests.put(
                                                        f"{api_url_input}/api/knowledge/update/{item_id}",
                                                        json=update_data,
                                                        timeout=30
                                                    )
                                                    if update_response.status_code == 200:
                                                        st.success("更新成功！")
                                                        st.session_state[f"edit_mode_{item_id}"] = False
                                                        st.rerun()
                                                    else:
                                                        st.error(f"更新失败: {update_response.json().get('detail', '未知错误')}")
                                                except Exception as e:
                                                    st.error(f"更新错误: {str(e)}")
                                        with col_cancel:
                                            if st.button("取消编辑", key=f"cancel_{item_id}", use_container_width=True):
                                                st.session_state[f"edit_mode_{item_id}"] = False
                                                st.rerun()
                        else:
                            st.info("未找到符合条件的知识点")
                    else:
                        st.error(f"获取知识点列表失败: {response.json().get('detail', '未知错误')}")

                except requests.exceptions.ConnectionError:
                    st.error(f"无法连接到 API 服务: {api_url_input}")
                except Exception as e:
                    st.error(f"发生错误: {str(e)}")

            st.markdown('</div>', unsafe_allow_html=True)

        # ---------------------------------------------------------
        # 子标签页 2：文档管理
        # ---------------------------------------------------------
        with sub_tab2:
            st.markdown('<div class="section-card">', unsafe_allow_html=True)

            st.markdown("""
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <p class="section-title" style="margin: 0;">📄 文档列表</p>
                <p style="color: #64748b; margin: 0; font-size: 14px;">点击文档名称查看详情或删除</p>
            </div>
            """, unsafe_allow_html=True)

            if st.button("刷新列表", key="refresh_docs_btn", use_container_width=True):
                st.rerun()

            with st.spinner("加载文档列表..."):
                try:
                    response = requests.get(
                        f"{api_url_input}/api/knowledge/documents",
                        timeout=REQUEST_TIMEOUT_STATS
                    )

                    if response.status_code == 200:
                        documents = response.json()

                        if documents:
                            # 创建文档表格
                            for doc in documents:
                                doc_id = doc.get("id", 0)
                                doc_name = doc.get("name", "未知文档")
                                doc_source = doc.get("source") or "-"
                                doc_type = doc.get("file_type") or "-"
                                doc_count = doc.get("knowledge_count", 0)
                                doc_created = doc.get("created_at", "-")
                                doc_updated = doc.get("updated_at", "-")

                                with st.expander(
                                    f"**文档 #{doc_id}**: {doc_name} | 知识点: {doc_count} | 来源: {doc_source}",
                                    expanded=False
                                ):
                                    col_doc1, col_doc2 = st.columns([3, 1])
                                    with col_doc1:
                                        st.markdown(f"""
                                        - **文档名称**: {doc_name}
                                        - **来源**: {doc_source}
                                        - **文件类型**: {doc_type}
                                        - **知识点数量**: {doc_count}
                                        - **创建时间**: {doc_created}
                                        - **更新时间**: {doc_updated}
                                        """)

                                    with col_doc2:
                                        st.write("")
                                        st.write("")
                                        if st.button(f"删除文档", key=f"del_doc_{doc_id}", use_container_width=True):
                                            st.session_state[f"confirm_del_doc_{doc_id}"] = True

                                    # 删除确认对话框
                                    if st.session_state.get(f"confirm_del_doc_{doc_id}", False):
                                        st.warning(f"⚠️ 确定要删除文档 **\"{doc_name}\"** 吗？此操作将同时删除所有关联的知识点（共 {doc_count} 条）！")
                                        col_confirm_yes, col_confirm_no = st.columns(2)
                                        with col_confirm_yes:
                                            if st.button("确认删除", key=f"doc_confirm_yes_{doc_id}", type="primary", use_container_width=True):
                                                try:
                                                    del_response = requests.delete(
                                                        f"{api_url_input}/api/knowledge/documents/{doc_id}",
                                                        timeout=30
                                                    )
                                                    if del_response.status_code == 200:
                                                        st.success("文档删除成功！")
                                                        st.session_state[f"confirm_del_doc_{doc_id}"] = False
                                                        st.rerun()
                                                    else:
                                                        st.error(f"删除失败: {del_response.json().get('detail', '未知错误')}")
                                                except Exception as e:
                                                    st.error(f"删除错误: {str(e)}")
                                        with col_confirm_no:
                                            if st.button("取消", key=f"doc_confirm_no_{doc_id}", use_container_width=True):
                                                st.session_state[f"confirm_del_doc_{doc_id}"] = False
                                                st.rerun()
                        else:
                            st.info("暂无文档")
                    else:
                        st.error(f"获取文档列表失败: {response.json().get('detail', '未知错误')}")

                except requests.exceptions.ConnectionError:
                    st.error(f"无法连接到 API 服务: {api_url_input}")
                except Exception as e:
                    st.error(f"发生错误: {str(e)}")

            st.markdown('</div>', unsafe_allow_html=True)
    
    
    # ============================================================================
    # 页脚
    # ============================================================================
    
    st.markdown("""
    <div class="footer">
        <p style="margin: 0;"><strong>🏛️ 金融监管知识库</strong> v1.0</p>
        <p style="margin: 0.5rem 0 0 0;">基于 MySQL + Milvus + LLM 智能问答系统</p>
        <p style="margin: 0.5rem 0 0 0; opacity: 0.7;">API 地址: """ + api_url_input + """</p>
    </div>
    """, unsafe_allow_html=True)


# ============================================================================
# 主程序入口
# ============================================================================

def main():
    """主程序入口"""
    # 如果已认证，自动跳转到主页
    if st.session_state.get("authenticated", False):
        st.session_state.current_page = "main"
    
    current_page = st.session_state.get("current_page", "login")
    
    if current_page == "login":
        show_login_page()
    elif current_page == "register":
        show_register_page()
    elif current_page == "forgot_password":
        show_forgot_password_page()
    elif current_page == "main":
        show_main_page()


if __name__ == "__main__":
    main()
