"""
自定义 CSS 样式
Custom CSS Styles Module
"""

# 全局样式
GLOBAL_STYLES = """
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
</style>
"""

# 认证页面样式
AUTH_STYLES = """
<style>
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
    
    /* 选择框样式 */
    .stSelectbox > div > div {
        background-color: #f8fafc;
        border-radius: 8px;
        border: 1px solid #e2e8f0;
    }
    
    /* 按钮样式 */
    .stButton > button {
        border-radius: 8px;
        padding: 10px 20px;
        font-weight: 500;
        border: none;
    }
    
    /* 分隔线样式 */
    hr {
        border: none;
        height: 1px;
        background: #e2e8f0;
        margin: 24px 0;
    }
</style>
"""

# 主页面样式
MAIN_STYLES = """
<style>
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
    
    /* 警告提示框 */
    .warning-box {
        background: #fef3c7;
        padding: 16px;
        border-radius: 10px;
        color: #92400e;
        margin: 16px 0;
        border: 1px solid #fcd34d;
    }
    
    /* 信息提示框 */
    .info-box {
        background: #eff6ff;
        padding: 16px;
        border-radius: 10px;
        color: #1e40af;
        margin: 16px 0;
        border: 1px solid #bfdbfe;
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
    
    /* 文件上传器样式 */
    [data-testid="stFileUploader"] {
        background: #f8fafc;
        border-radius: 12px;
        padding: 24px;
        border: 2px dashed #cbd5e1;
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
    
    /* section标题 */
    .section-title {
        font-size: 16px;
        font-weight: 600;
        color: #0f172a;
        margin: 0 0 16px 0;
    }
    
    /* section card */
    .section-card {
        background: #ffffff;
        border-radius: 12px;
        padding: 24px;
        border: 1px solid #e2e8f0;
        margin-bottom: 16px;
    }
    
    /* 页脚样式 */
    .footer {
        text-align: center;
        padding: 24px 0 12px;
        color: #94a3b8;
        font-size: 12px;
    }
    
    /* 页面头部 */
    .page-header {
        margin-bottom: 24px;
    }
    
    /* 徽章样式 */
    .badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 500;
    }
    
    .badge-success {
        background: #dcfce7;
        color: #166534;
    }
    
    .badge-warning {
        background: #fef3c7;
        color: #92400e;
    }
    
    .badge-danger {
        background: #fee2e2;
        color: #991b1b;
    }
    
    .badge-info {
        background: #dbeafe;
        color: #1e40af;
    }
    
    /* 渐变卡片 */
    .gradient-card {
        padding: 24px;
        border-radius: 12px;
        text-align: center;
    }
    
    .gradient-card-primary {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
    }
    
    .gradient-card-success {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        color: white;
    }
    
    /* 加载动画 */
    .loading-spinner {
        display: flex;
        justify-content: center;
        align-items: center;
        padding: 40px;
    }
    
    /* 数据表格样式优化 */
    .dataframe {
        border: none !important;
    }
    
    /* 响应式布局 */
    @media (max-width: 768px) {
        .section-card {
            padding: 16px;
        }
        
        .main-title {
            font-size: 22px;
        }
    }
</style>
"""

# 侧边栏样式
SIDEBAR_STYLES = """
<style>
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
    
    /* 侧边栏用户信息 */
    .sidebar-user-card {
        background: rgba(255, 255, 255, 0.1);
        padding: 16px;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 16px;
    }
    
    .sidebar-user-name {
        color: #fff;
        font-size: 18px;
        font-weight: 600;
        margin: 8px 0 0 0;
    }
    
    .sidebar-user-role {
        color: #94a3b8;
        font-size: 12px;
        margin: 4px 0 0 0;
    }
    
    /* 侧边栏菜单项 */
    .sidebar-menu-item {
        padding: 12px 16px;
        border-radius: 8px;
        margin: 4px 0;
        transition: background 0.2s;
    }
    
    .sidebar-menu-item:hover {
        background: rgba(255, 255, 255, 0.1);
    }
    
    /* 侧边栏分隔线 */
    .sidebar-divider {
        border: none;
        height: 1px;
        background: rgba(255, 255, 255, 0.1);
        margin: 16px 0;
    }
    
    /* API 状态指示器 */
    .api-status {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 8px 12px;
        border-radius: 8px;
        font-size: 13px;
    }
    
    .api-status-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
    }
    
    .api-status-connected {
        background: rgba(34, 197, 94, 0.2);
        color: #4ade80;
    }
    
    .api-status-connected .api-status-dot {
        background: #22c55e;
    }
    
    .api-status-disconnected {
        background: rgba(239, 68, 68, 0.2);
        color: #f87171;
    }
    
    .api-status-disconnected .api-status-dot {
        background: #ef4444;
    }
</style>
"""

# 评估模块样式
EVALUATION_STYLES = """
<style>
    /* 评估结果卡片 */
    .eval-result-card {
        background: #ffffff;
        border-radius: 12px;
        padding: 20px;
        border: 1px solid #e2e8f0;
        margin: 12px 0;
    }
    
    /* 评分展示 */
    .score-display {
        text-align: center;
        padding: 24px;
        border-radius: 12px;
        margin: 16px 0;
    }
    
    .score-value {
        font-size: 48px;
        font-weight: 700;
        margin: 8px 0;
    }
    
    .score-label {
        font-size: 14px;
        opacity: 0.8;
    }
    
    /* 进度条样式 */
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #6366f1, #8b5cf6);
    }
    
    /* 指标对比图表 */
    .metric-comparison {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 16px;
        margin: 16px 0;
    }
    
    .metric-item {
        background: #f8fafc;
        padding: 16px;
        border-radius: 8px;
        text-align: center;
    }
    
    .metric-value {
        font-size: 24px;
        font-weight: 700;
        color: #0f172a;
    }
    
    .metric-label {
        font-size: 12px;
        color: #64748b;
        margin-top: 4px;
    }
    
    /* 历史报告项 */
    .report-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 12px 16px;
        background: #f8fafc;
        border-radius: 8px;
        margin: 8px 0;
    }
    
    .report-info {
        flex: 1;
    }
    
    .report-title {
        font-weight: 500;
        color: #0f172a;
    }
    
    .report-date {
        font-size: 12px;
        color: #64748b;
    }
    
    /* 批量测试进度 */
    .batch-progress {
        background: #f8fafc;
        padding: 20px;
        border-radius: 12px;
        margin: 16px 0;
    }
    
    .batch-progress-header {
        display: flex;
        justify-content: space-between;
        margin-bottom: 12px;
    }
    
    .batch-progress-text {
        color: #64748b;
        font-size: 14px;
    }
    
    .batch-progress-percent {
        color: #6366f1;
        font-weight: 600;
    }
</style>
"""


def get_all_styles() -> str:
    """获取所有样式"""
    return f"{GLOBAL_STYLES}{AUTH_STYLES}{MAIN_STYLES}{SIDEBAR_STYLES}{EVALUATION_STYLES}"
