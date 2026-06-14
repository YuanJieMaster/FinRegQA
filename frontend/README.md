# 金融监管知识库前端

模块化的 Streamlit 前端应用，采用清晰的分层架构。

## 目录结构

```
frontend/
├── main.py                 # 应用入口
├── config/                 # 配置模块
│   ├── __init__.py
│   └── settings.py         # 应用配置常量
├── styles/                 # 样式模块
│   ├── __init__.py
│   └── theme.py            # CSS 主题样式
├── utils/                  # 工具模块
│   ├── __init__.py
│   ├── api.py              # API 客户端封装
│   └── session.py          # 会话状态管理
├── pages/                  # 页面模块
│   ├── __init__.py
│   ├── auth.py             # 认证页面导出
│   ├── login.py            # 登录页
│   ├── register.py        # 注册页
│   ├── forgot_password.py  # 忘记密码页
│   └── main.py             # 主页面
└── components/             # 组件模块
    ├── __init__.py
    ├── sidebar.py          # 侧边栏组件
    ├── qa_page.py          # 问答页面组件
    ├── upload_page.py      # 文档上传组件
    ├── stats_page.py       # 统计信息组件
    ├── knowledge_page.py    # 知识库管理组件
```

## 运行方式

```bash
# 安装依赖
pip install -r requirements.txt

# 运行应用
python -m streamlit run app.py
```

## 模块说明

### config/
包含应用的配置常量，如 API 超时设置、地区选项、文件类型等。

### styles/
包含自定义 CSS 样式，定义了认证页面、主页面、侧边栏等多种样式。

### utils/
- `api.py`: API 客户端封装，提供统一的 API 调用接口
- `session.py`: 会话状态管理，管理用户登录状态、页面状态等

### pages/
- `login.py`: 用户登录页面
- `register.py`: 用户注册页面
- `forgot_password.py`: 忘记密码页面
- `main.py`: 主页面，整合所有功能模块

### components/
- `sidebar.py`: 侧边栏组件，包含用户信息、系统配置、使用说明
- `qa_page.py`: 智能问答组件，支持问题输入、地区筛选、搜索模式选择
- `upload_page.py`: 文档上传组件，支持多种文件格式
- `stats_page.py`: 统计信息组件，展示知识库各类统计数据
- `knowledge_page.py`: 知识库管理组件，包含知识点和文档管理

## 架构特点

1. **模块化设计**: 每个功能模块独立封装，便于维护和扩展
2. **清晰的职责分离**: 配置、样式、工具、页面、组件各司其职
3. **统一的 API 调用**: 通过 `api.py` 封装所有 API 请求
4. **集中式状态管理**: 通过 `session.py` 统一管理会话状态
5. **可复用组件**: 各页面组件可在不同场景中复用

## 与后端 API 交互

前端通过 `utils/api.py` 中的函数与后端 API 交互：

- 认证: `/api/v1/auth/*`
- 知识库: `/api/knowledge/*`
