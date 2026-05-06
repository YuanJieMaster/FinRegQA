"""
会话状态管理模块
Session State Management Module
"""

import streamlit as st


def init_session_state():
    """初始化 session_state"""
    defaults = {
        "authenticated": False,
        "access_token": None,
        "refresh_token": None,
        "user_info": None,
        "current_page": "login",
        "api_url": "http://localhost:8000",
        # 知识库管理页状态
        "kb_page": 1,
        "kb_page_size": 20,
        # 评估页状态
        "eval_results": None,
        # 问答历史
        "qa_history": [],
    }
    
    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value


def save_tokens(access_token: str, refresh_token: str):
    """保存令牌到 session_state"""
    st.session_state.access_token = access_token
    st.session_state.refresh_token = refresh_token
    st.session_state.authenticated = True


def save_user_info(username: str, email: str = None, role: str = None):
    """保存用户信息"""
    st.session_state.user_info = {
        "username": username,
        "email": email,
        "role": role or "user"
    }


def clear_auth():
    """清除认证状态"""
    st.session_state.authenticated = False
    st.session_state.access_token = None
    st.session_state.refresh_token = None
    st.session_state.user_info = None
    st.session_state.current_page = "login"
    st.session_state.qa_history = []


def set_current_page(page: str):
    """设置当前页面"""
    st.session_state.current_page = page


def is_authenticated() -> bool:
    """检查是否已认证"""
    return st.session_state.get("authenticated", False)


def get_api_url() -> str:
    """获取 API 地址"""
    return st.session_state.get("api_url", "http://localhost:8000")


def set_api_url(url: str):
    """设置 API 地址"""
    st.session_state.api_url = url


def add_qa_history(question: str, answer: str, references: list = None):
    """添加问答历史"""
    history = st.session_state.get("qa_history", [])
    history.insert(0, {
        "question": question,
        "answer": answer,
        "references": references or [],
        "timestamp": None  # 可扩展时间戳
    })
    # 只保留最近20条
    st.session_state.qa_history = history[:20]


def get_qa_history() -> list:
    """获取问答历史"""
    return st.session_state.get("qa_history", [])


def clear_qa_history():
    """清除问答历史"""
    st.session_state.qa_history = []


def set_kb_page(page: int):
    """设置知识库页码"""
    st.session_state.kb_page = page


def get_kb_page() -> int:
    """获取知识库页码"""
    return st.session_state.get("kb_page", 1)


def set_kb_page_size(size: int):
    """设置每页条数"""
    st.session_state.kb_page_size = size


def get_kb_page_size() -> int:
    """获取每页条数"""
    return st.session_state.get("kb_page_size", 20)
