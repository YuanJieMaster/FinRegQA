"""
数据库初始化脚本
Database initialization script
"""
import sys
from pathlib import Path

# 将项目根目录添加到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pymysql
from app.core.config import settings


def create_database():
    """创建数据库"""
    connection = pymysql.connect(
        host=settings.MYSQL_HOST,
        port=settings.MYSQL_PORT,
        user=settings.MYSQL_USER,
        password=settings.MYSQL_PASSWORD
    )
    
    try:
        with connection.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{settings.MYSQL_DATABASE}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            print(f"✅ 数据库 '{settings.MYSQL_DATABASE}' 创建成功")
    finally:
        connection.close()


def init_tables():
    """初始化数据表"""
    from app.core.database import engine, Base
    from app.models import User, PasswordResetToken, UserSession, Document, Knowledge, Log
    
    Base.metadata.create_all(bind=engine)
    print("✅ 数据表创建成功 (users, password_reset_tokens, user_sessions, document, knowledge, log)")


if __name__ == "__main__":
    print("开始初始化数据库...")
    create_database()
    init_tables()
    print("✅ 数据库初始化完成")
