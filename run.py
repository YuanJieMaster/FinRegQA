#!/usr/bin/env python
"""
一键启动脚本
Startup script for FinRegQA system

同时启动 FastAPI 后端和 Streamlit 前端
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def main():
    print("=" * 80)
    print("金融监管知识库系统启动")
    print("=" * 80)
    
    # 检查依赖
    print("\n✓ 检查依赖...")
    try:
        import fastapi
        import streamlit
        import uvicorn
        print("  ✓ FastAPI 已安装")
        print("  ✓ Streamlit 已安装")
    except ImportError as e:
        print(f"  ✗ 缺少依赖: {e}")
        print("\n请先运行: pip install -r requirements.txt")
        sys.exit(1)
    
    # 检查 .env 文件
    print("\n✓ 检查配置...")
    env_file = Path(".env")
    if env_file.exists():
        print(f"  ✓ 找到 .env 配置文件")
    else:
        print(f"  ⚠ 未找到 .env 文件，将使用默认配置")
    
    # 启动 FastAPI 后端
    print("\n" + "=" * 80)
    print("启动 FastAPI 后端服务...")
    print("=" * 80)
    
    api_process = subprocess.Popen(
        [sys.executable, "api.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # 等待 API 启动
    time.sleep(3)
    
    if api_process.poll() is not None:
        print("✗ FastAPI 启动失败")
        sys.exit(1)
    
    print("✓ FastAPI 已启动 (http://localhost:8000)")
    print("  API 文档: http://localhost:8000/docs")
    
    # 启动 Streamlit 前端
    print("\n" + "=" * 80)
    print("启动 Streamlit 前端...")
    print("=" * 80)
    
    try:
        subprocess.run(
            [sys.executable, "-m", "streamlit", "run", "frontend.py"],
            check=False
        )
    except KeyboardInterrupt:
        print("\n\n正在关闭服务...")
        api_process.terminate()
        api_process.wait()
        print("✓ 服务已关闭")
    except Exception as e:
        print(f"✗ 启动失败: {e}")
        api_process.terminate()
        sys.exit(1)


if __name__ == "__main__":
    main()
