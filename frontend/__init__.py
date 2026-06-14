"""
金融监管知识库前端模块
Financial Knowledge Base Frontend Module
"""

from views.login import render_login_page
from views.register import render_register_page
from views.forgot_password import render_forgot_password_page
from views.dashboard import render_main_page
from .components import (
    render_sidebar,
    render_qa_page,
    render_upload_page,
    render_stats_page,
    render_knowledge_management_page,
    render_human_eval_page,
)
from .utils import (
    init_session_state,
    save_tokens,
    save_user_info,
    clear_auth,
    set_current_page,
    is_authenticated,
    get_api_url,
    set_api_url,
)
from .config import (
    REQUEST_TIMEOUT_ANSWER,
    REQUEST_TIMEOUT_INGEST,
    REQUEST_TIMEOUT_STATS,
    REGION_OPTIONS,
    CATEGORY_OPTIONS,
    DEFAULT_API_URL,
    SUPPORTED_FILE_TYPES,
    PAGE_SIZE_OPTIONS,
)

__all__ = [
    # Pages
    "render_login_page",
    "render_register_page",
    "render_forgot_password_page",
    "render_main_page",
    # Components
    "render_sidebar",
    "render_qa_page",
    "render_upload_page",
    "render_stats_page",
    "render_knowledge_management_page",
    "render_human_eval_page",
    # Utils
    "init_session_state",
    "save_tokens",
    "save_user_info",
    "clear_auth",
    "set_current_page",
    "is_authenticated",
    "get_api_url",
    "set_api_url",
    # Config
    "REQUEST_TIMEOUT_ANSWER",
    "REQUEST_TIMEOUT_INGEST",
    "REQUEST_TIMEOUT_STATS",
    "REGION_OPTIONS",
    "CATEGORY_OPTIONS",
    "DEFAULT_API_URL",
    "SUPPORTED_FILE_TYPES",
    "PAGE_SIZE_OPTIONS",
]
