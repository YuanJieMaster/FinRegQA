"""
Database initialization script.
"""

import sys
from pathlib import Path

import pymysql

# Add the project root to the Python path.
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.config import settings


def create_database() -> None:
    """Create the configured MySQL database if it does not exist."""
    connection = pymysql.connect(
        host=settings.MYSQL_HOST,
        port=settings.MYSQL_PORT,
        user=settings.MYSQL_USER,
        password=settings.MYSQL_PASSWORD,
    )

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{settings.MYSQL_DATABASE}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
            print(f"Database '{settings.MYSQL_DATABASE}' created successfully")
    finally:
        connection.close()


def init_tables() -> None:
    """Initialize SQLAlchemy-managed tables."""
    from app.core.database import Base, engine
    from app.models import PasswordResetToken, User, UserSession  # noqa: F401

    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully")


if __name__ == "__main__":
    print("Initializing database...")
    create_database()
    init_tables()
    print("Database initialization completed")
