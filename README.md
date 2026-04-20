# FinRegQA 金融制度知识问答系统

基于RAG技术的金融制度知识问答系统后端API。

## 项目结构

```
FinRegQA/
├── main.py                    # FastAPI应用入口
├── requirements.txt           # 依赖包
├── .env.example               # 环境变量示例
├── docker-compose.yml         # Docker编排配置
├── README.md                  # 项目文档
├── app/
│   ├── __init__.py           # 应用模块入口
│   ├── core/                  # 核心模块
│   │   ├── __init__.py
│   │   ├── config/            # 配置管理
│   │   │   ├── __init__.py
│   │   │   └── settings.py    # 配置类
│   │   ├── database.py        # 数据库连接
│   │   ├── security.py        # JWT/密码安全
│   │   └── email.py           # QQ邮箱发送
│   ├── models/                # 数据模型
│   │   └── user.py           # 用户模型
│   ├── schemas/               # Pydantic schemas
│   │   └── user.py           # 用户schemas
│   ├── crud/                  # CRUD操作
│   │   └── user.py           # 用户CRUD
│   ├── api/                   # API路由
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── auth.py       # 认证API
│   │       └── users.py      # 用户API
│   └── services/              # 业务服务
│       ├── __init__.py
│       ├── knowledge_base.py  # 知识库服务
│       └── text_processor.py # 文本处理服务
├── scripts/                    # 脚本目录
│   └── init_db.py            # 数据库初始化
├── data/                      # 数据目录
│   └── faiss_index/          # FAISS索引
└── docs/                      # 文档目录
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，填写以下配置：

```env
# MySQL数据库
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=finregqa

# JWT密钥
SECRET_KEY=your-super-secret-key-change-in-production

# QQ邮箱SMTP
SMTP_USER=your_qq_email@qq.com
SMTP_PASSWORD=your_qq_authorization_code
```

### 3. 初始化数据库

```bash
python scripts/init_db.py
```

### 4. 启动服务

```bash
python main.py
```

访问 API 文档: http://localhost:8000/docs

## API接口

### 认证接口

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | /api/v1/auth/register | 用户注册 |
| POST | /api/v1/auth/login | 用户登录 |
| POST | /api/v1/auth/logout | 用户登出 |
| POST | /api/v1/auth/refresh | 刷新Token |
| POST | /api/v1/auth/password/change | 修改密码 |
| POST | /api/v1/auth/password/reset-request | 请求密码重置 |
| POST | /api/v1/auth/password/reset-confirm | 确认密码重置 |
| GET | /api/v1/auth/verify-email | 验证邮箱 |

### 用户接口

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | /api/v1/users/me | 获取个人信息 |
| PUT | /api/v1/users/me | 修改个人信息 |
| GET | /api/v1/users/me/sessions | 获取会话列表 |
| DELETE | /api/v1/users/me/sessions/{id} | 撤销会话 |

## 技术栈

- **Web框架**: FastAPI
- **数据库**: MySQL
- **向量检索**: Milvus
- **文本嵌入**: sentence-transformers
- **认证**: JWT (python-jose)
- **密码加密**: bcrypt (passlib)
- **邮件发送**: QQ邮箱 SMTP
