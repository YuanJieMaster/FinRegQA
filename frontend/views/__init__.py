"""
页面模块
Pages Package
"""

from views.login import render_login_page
from views.register import render_register_page
from views.forgot_password import render_forgot_password_page
from views.dashboard import render_main_page

__all__ = [
    "render_login_page",
    "render_register_page",
    "render_forgot_password_page",
    "render_main_page",
]
