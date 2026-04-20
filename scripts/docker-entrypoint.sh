#!/bin/bash
# FinRegQA Docker 启动脚本
# 此脚本在容器启动时自动执行

set -e

echo "=========================================="
echo "FinRegQA 启动中..."
echo "=========================================="

# 等待 MySQL 就绪
echo "Waiting for MySQL..."
until mysql -h"${MYSQL_HOST}" -P"${MYSQL_PORT}" -u"${MYSQL_USER}" -p"${MYSQL_PASSWORD}" -e "SELECT 1" &>/dev/null; do
    echo "  MySQL not ready, waiting 2 seconds..."
    sleep 2
done
echo "MySQL is ready"

# 等待额外的初始化时间
sleep 2

# 初始化数据库表
echo "Initializing database tables..."
cd /app
python -c "
from app.core.database import engine, Base
from app.models import User, PasswordResetToken, UserSession, Document, Knowledge, Log
Base.metadata.create_all(bind=engine)
print('Database tables created')
" || echo "Tables may already exist, skipping..."

# 创建必要的目录
echo "Creating data directories..."
mkdir -p /app/data/uploads
mkdir -p /app/data/milvus_data
touch /app/data/uploads/.gitkeep

echo "=========================================="
echo "Starting FinRegQA application..."
echo "=========================================="

# 启动 uvicorn
exec uvicorn main:app --host 0.0.0.0 --port 8000
