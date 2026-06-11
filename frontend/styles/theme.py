"""
自定义 CSS 样式 — 金融级高级感 UI
Premium fintech dashboard styling: glassmorphism, design tokens, refined typography.
"""

from styles.tokens import DESIGN_TOKENS_CSS

FONT_IMPORT = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;600;700&display=swap" rel="stylesheet">
"""

GLOBAL_STYLES = f"""
<style>
{DESIGN_TOKENS_CSS}

    /* ── 全局基础 ── */
    html, body, [class*="css"] {{
        font-family: var(--font-sans);
    }}

    .main {{
        padding: 0;
    }}

    #MainMenu {{ visibility: hidden; }}
    footer {{ visibility: hidden; }}

    div[data-testid="stDecoration"] {{
        background: linear-gradient(90deg, var(--primary-dark), var(--primary));
        height: 3px;
    }}

    .stApp {{
        background: var(--bg-gradient);
        background-attachment: fixed;
    }}

    .block-container {{
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        max-width: 1280px;
    }}

    /* 主按钮 */
    .stButton > button[kind="primary"],
    .stButton > button[data-testid="baseButton-primary"] {{
        background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: var(--radius-sm) !important;
        font-weight: 600 !important;
        box-shadow: var(--shadow-sm), 0 2px 8px var(--accent-glow) !important;
        transition: transform 0.15s ease, box-shadow 0.15s ease !important;
    }}

    .stButton > button[kind="primary"]:hover,
    .stButton > button[data-testid="baseButton-primary"]:hover {{
        transform: translateY(-1px);
        box-shadow: var(--shadow-md), 0 4px 16px var(--accent-glow) !important;
    }}

    .stButton > button {{
        border-radius: var(--radius-sm) !important;
        font-weight: 500 !important;
        transition: all 0.15s ease !important;
    }}

    /* 输入框 */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stNumberInput > div > div > input {{
        background: var(--surface-solid) !important;
        border: 1px solid var(--card-border) !important;
        border-radius: var(--radius-sm) !important;
        font-size: 14px !important;
        transition: border-color 0.15s, box-shadow 0.15s !important;
    }}

    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {{
        border-color: var(--primary) !important;
        box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12) !important;
    }}

    .stSelectbox > div > div {{
        background: var(--surface-solid);
        border-radius: var(--radius-sm);
        border: 1px solid var(--card-border);
    }}

    /* 滚动条 */
    ::-webkit-scrollbar {{ width: 6px; height: 6px; }}
    ::-webkit-scrollbar-track {{ background: transparent; }}
    ::-webkit-scrollbar-thumb {{
        background: #cbd5e1;
        border-radius: 3px;
    }}
    ::-webkit-scrollbar-thumb:hover {{ background: #94a3b8; }}
</style>
"""

AUTH_STYLES = """
<style>
    /* ── 认证页：紧凑布局，列顶对齐 ── */
    .auth-page-wrap {
        margin: 0;
        padding: 0;
    }

    .auth-page-marker {
        display: none;
    }

    /* 认证页主容器：收窄宽度、减少上下留白 */
    section.main:has(.auth-page-marker) .block-container {
        padding-top: 1.25rem !important;
        padding-bottom: 1.5rem !important;
        max-width: 920px !important;
    }

    section.main:has(.auth-page-marker) div[data-testid="stHorizontalBlock"] {
        align-items: flex-start !important;
    }

    section.main:has(.auth-page-marker) [data-testid="column"] {
        align-self: flex-start !important;
    }

    .stApp:has(.auth-page-marker) [data-testid="stSidebar"] {
        display: none !important;
    }

    .stApp:has(.auth-page-marker) section.main {
        margin-left: 0 !important;
        max-width: 100% !important;
    }

    .stApp:has(.auth-page-marker) header[data-testid="stHeader"] {
        visibility: hidden;
        height: 0;
    }

    section.main:has(.auth-page-marker) .stTextInput {
        margin-bottom: 0.35rem;
    }

    .auth-brand-panel {
        background: var(--bg-auth);
        border-radius: var(--radius-lg);
        padding: 28px 28px 24px;
        display: flex;
        flex-direction: column;
        justify-content: flex-start;
        position: relative;
        overflow: hidden;
        border: 1px solid rgba(255, 255, 255, 0.06);
        box-shadow: var(--shadow-md);
    }

    .auth-brand-panel::before {
        content: "";
        position: absolute;
        top: -40%;
        right: -20%;
        width: 60%;
        height: 80%;
        background: radial-gradient(circle, rgba(37, 99, 235, 0.25) 0%, transparent 70%);
        pointer-events: none;
    }

    .auth-brand-logo {
        width: 44px;
        height: 44px;
        background: linear-gradient(135deg, var(--primary-light), var(--accent));
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 22px;
        margin-bottom: 16px;
        box-shadow: 0 6px 18px rgba(37, 99, 235, 0.35);
    }

    .auth-brand-title {
        font-size: 24px;
        font-weight: 700;
        color: var(--text-inverse);
        margin: 0 0 8px 0;
        letter-spacing: -0.02em;
        line-height: 1.25;
    }

    .auth-brand-tagline {
        color: var(--sidebar-muted);
        font-size: 13px;
        margin: 0 0 18px 0;
        line-height: 1.5;
    }

    .auth-feature-list {
        list-style: none;
        padding: 0;
        margin: 0;
    }

    .auth-feature-item {
        display: flex;
        align-items: flex-start;
        gap: 10px;
        padding: 8px 12px;
        margin-bottom: 6px;
        background: var(--glass-bg);
        backdrop-filter: blur(var(--glass-blur));
        -webkit-backdrop-filter: blur(var(--glass-blur));
        border: 1px solid var(--glass-border);
        border-radius: var(--radius-sm);
        color: #e2e8f0;
        font-size: 13px;
        line-height: 1.45;
    }

    .auth-feature-item:last-child {
        margin-bottom: 0;
    }

    .auth-feature-icon {
        flex-shrink: 0;
        width: 24px;
        height: 24px;
        background: rgba(37, 99, 235, 0.3);
        border-radius: 6px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 12px;
    }

    .auth-card {
        background: var(--surface);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border-radius: var(--radius-lg);
        padding: 28px 26px 24px;
        border: 1px solid var(--card-border);
        box-shadow: var(--shadow-md);
    }

    .auth-card-title {
        font-size: 20px;
        font-weight: 700;
        color: var(--text-primary);
        margin: 0 0 4px 0;
    }

    .auth-card-subtitle {
        color: var(--text-muted);
        font-size: 13px;
        margin: 0 0 18px 0;
    }

    hr.auth-divider {
        border: none;
        height: 1px;
        background: var(--card-border);
        margin: 14px 0;
    }
</style>
"""

MAIN_STYLES = """
<style>
    /* ── 页头 Hero ── */
    .hero-header {
        background: linear-gradient(135deg, rgba(255,255,255,0.95) 0%, rgba(238,242,255,0.9) 100%);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid var(--card-border);
        border-radius: var(--radius-lg);
        padding: 28px 32px;
        margin-bottom: 24px;
        box-shadow: var(--shadow-md);
        position: relative;
        overflow: hidden;
    }

    .hero-header::after {
        content: "";
        position: absolute;
        top: 0;
        right: 0;
        width: 200px;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(37, 99, 235, 0.04));
        pointer-events: none;
    }

    .hero-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 12px;
        background: var(--info-bg);
        border: 1px solid rgba(37, 99, 235, 0.15);
        border-radius: 999px;
        font-size: 12px;
        font-weight: 500;
        color: var(--primary-dark);
        margin-bottom: 12px;
    }

    .hero-badge-dot {
        width: 6px;
        height: 6px;
        background: var(--success);
        border-radius: 50%;
        animation: pulse-dot 2s ease-in-out infinite;
    }

    @keyframes pulse-dot {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }

    .main-title {
        font-size: 26px;
        font-weight: 700;
        color: var(--text-primary);
        margin: 0 0 8px 0;
        letter-spacing: -0.02em;
    }

    .main-subtitle {
        color: var(--text-muted);
        font-size: 14px;
        margin: 0;
    }

    .hero-tags {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-top: 16px;
    }

    .hero-tag {
        padding: 4px 10px;
        background: var(--surface-muted);
        border-radius: 6px;
        font-size: 12px;
        color: var(--text-secondary);
        border: 1px solid var(--card-border);
    }

    /* ── Tab 胶囊式 ── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
        background: rgba(255, 255, 255, 0.6);
        backdrop-filter: blur(8px);
        padding: 6px;
        border-radius: var(--radius-md);
        border: 1px solid var(--card-border);
        margin-bottom: 8px;
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: var(--radius-sm) !important;
        padding: 10px 18px !important;
        font-weight: 500 !important;
        font-size: 14px !important;
        color: var(--text-muted) !important;
        background: transparent !important;
        border: none !important;
        transition: all 0.15s ease !important;
    }

    .stTabs [data-baseweb="tab"]:hover {
        color: var(--text-primary) !important;
        background: rgba(37, 99, 235, 0.06) !important;
    }

    .stTabs [aria-selected="true"] {
        color: var(--primary) !important;
        background: var(--surface-solid) !important;
        box-shadow: var(--shadow-sm) !important;
        font-weight: 600 !important;
    }

    .stTabs [data-baseweb="tab-panel"] {
        padding-top: 16px;
    }

    /* ── 内容卡片（玻璃拟态） ── */
    .section-card {
        background: var(--surface);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border-radius: var(--radius-lg);
        padding: 24px 28px;
        border: 1px solid var(--card-border);
        margin-bottom: 16px;
        box-shadow: var(--shadow-md);
        transition: box-shadow 0.2s ease;
    }

    .section-card:hover {
        box-shadow: var(--shadow-lg);
    }

    .section-title {
        font-size: 16px;
        font-weight: 600;
        color: var(--text-primary);
        margin: 0 0 16px 0;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    .section-title-icon {
        width: 32px;
        height: 32px;
        background: var(--info-bg);
        border-radius: 8px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-size: 16px;
    }

    /* ── 问答 & 引用 ── */
    .answer-box {
        background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
        padding: 24px;
        border-radius: var(--radius-md);
        border: 1px solid var(--card-border);
        border-left: 3px solid var(--primary);
        margin: 16px 0;
        font-size: 15px;
        line-height: 1.75;
        color: var(--text-secondary);
        box-shadow: var(--shadow-sm);
    }

    .streaming-cursor {
        display: inline;
        animation: blink 1s step-end infinite;
        color: var(--primary);
        font-weight: bold;
    }

    @keyframes blink {
        0%, 100% { opacity: 1; }
        50% { opacity: 0; }
    }

    .reference-box {
        background: var(--surface-solid);
        padding: 16px 18px;
        border-radius: var(--radius-md);
        margin: 8px 0;
        border: 1px solid var(--card-border);
        border-left: 3px solid var(--accent);
    }

    .example-chip {
        display: inline-block;
        padding: 6px 14px;
        margin: 4px 6px 4px 0;
        background: var(--surface-solid);
        border: 1px solid var(--card-border);
        border-radius: 999px;
        font-size: 13px;
        color: var(--text-secondary);
        cursor: default;
    }

    /* ── 状态框 ── */
    .success-box {
        background: var(--success-bg);
        padding: 16px 18px;
        border-radius: var(--radius-md);
        color: #065f46;
        margin: 16px 0;
        border: 1px solid rgba(16, 185, 129, 0.25);
    }

    .error-box {
        background: var(--error-bg);
        padding: 16px 18px;
        border-radius: var(--radius-md);
        color: #991b1b;
        margin: 16px 0;
        border: 1px solid rgba(239, 68, 68, 0.2);
    }

    .warning-box {
        background: var(--warning-bg);
        padding: 16px 18px;
        border-radius: var(--radius-md);
        color: #92400e;
        margin: 16px 0;
        border: 1px solid rgba(245, 158, 11, 0.25);
    }

    .info-box {
        background: var(--info-bg);
        padding: 18px 20px;
        border-radius: var(--radius-md);
        color: #1e40af;
        margin: 16px 0;
        border: 1px solid rgba(37, 99, 235, 0.15);
    }

    /* ── Metric 卡片 ── */
    [data-testid="stMetric"] {
        background: var(--surface);
        backdrop-filter: blur(8px);
        border-radius: var(--radius-md);
        padding: 20px 22px;
        border: 1px solid var(--card-border);
        box-shadow: var(--shadow-sm);
        transition: transform 0.15s, box-shadow 0.15s;
    }

    [data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        box-shadow: var(--shadow-md);
    }

    [data-testid="stMetricLabel"] {
        color: var(--text-muted);
        font-weight: 500;
        font-size: 13px;
    }

    [data-testid="stMetricValue"] {
        color: var(--text-primary);
        font-weight: 700;
        font-size: 28px;
        background: linear-gradient(135deg, var(--primary-dark), var(--primary));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }

    /* ── 上传 & 展开器 ── */
    [data-testid="stFileUploader"] {
        background: var(--surface-muted);
        border-radius: var(--radius-md);
        padding: 28px;
        border: 2px dashed #cbd5e1;
        transition: border-color 0.15s;
    }

    [data-testid="stFileUploader"]:hover {
        border-color: var(--primary-light);
    }

    .streamlit-expanderHeader {
        background: var(--surface-muted);
        border-radius: var(--radius-sm);
        border: 1px solid var(--card-border);
        font-weight: 500;
    }

    [data-testid="stVegaLiteChart"] {
        background: var(--surface-solid);
        border-radius: var(--radius-md);
        padding: 16px;
        border: 1px solid var(--card-border);
    }

    /* ── 徽章 ── */
    .badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 500;
    }

    .badge-success { background: var(--success-bg); color: #065f46; }
    .badge-warning { background: var(--warning-bg); color: #92400e; }
    .badge-danger { background: var(--error-bg); color: #991b1b; }
    .badge-info { background: var(--info-bg); color: #1e40af; }

    /* ── 页脚 ── */
    .footer {
        text-align: center;
        padding: 28px 0 12px;
        margin-top: 32px;
        border-top: 1px solid var(--card-border);
        color: var(--text-muted);
        font-size: 12px;
    }

    .footer-brand {
        font-weight: 600;
        color: var(--text-secondary);
    }

    @media (max-width: 768px) {
        .section-card { padding: 18px 20px; }
        .main-title { font-size: 22px; }
        .auth-brand-panel { padding: 22px 20px 20px; }
        .auth-card { padding: 22px 20px 20px; }
    }
</style>
"""

SIDEBAR_STYLES = """
<style>
    /* ── 深色玻璃侧栏 ── */
    [data-testid="stSidebar"] {
        background: var(--sidebar-bg) !important;
        backdrop-filter: blur(var(--glass-blur));
        -webkit-backdrop-filter: blur(var(--glass-blur));
        border-right: 1px solid var(--sidebar-border);
    }

    [data-testid="stSidebar"] > div:first-child {
        background: transparent;
    }

    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] h4 {
        color: var(--sidebar-text) !important;
    }

    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] label {
        color: var(--sidebar-muted) !important;
    }

    [data-testid="stSidebar"] .stTextInput > div > div > input {
        background: rgba(255, 255, 255, 0.06) !important;
        border-color: rgba(255, 255, 255, 0.12) !important;
        color: var(--sidebar-text) !important;
    }

    [data-testid="stSidebar"] hr {
        border-color: rgba(255, 255, 255, 0.08);
    }

    .sidebar-brand {
        text-align: center;
        padding: 8px 0 20px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        margin-bottom: 20px;
    }

    .sidebar-brand-icon {
        width: 48px;
        height: 48px;
        margin: 0 auto 12px;
        background: linear-gradient(135deg, var(--primary), var(--accent));
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 24px;
        box-shadow: 0 4px 16px rgba(37, 99, 235, 0.35);
    }

    .sidebar-brand-title {
        color: var(--sidebar-text);
        font-size: 16px;
        font-weight: 700;
        margin: 0;
    }

    .sidebar-brand-sub {
        color: var(--sidebar-muted);
        font-size: 11px;
        margin: 4px 0 0 0;
    }

    .sidebar-user-card {
        background: rgba(255, 255, 255, 0.06);
        backdrop-filter: blur(8px);
        padding: 18px 16px;
        border-radius: var(--radius-md);
        text-align: center;
        margin-bottom: 16px;
        border: 1px solid rgba(255, 255, 255, 0.08);
    }

    .sidebar-avatar {
        width: 48px;
        height: 48px;
        margin: 0 auto 10px;
        background: linear-gradient(135deg, #3b82f6, #0ea5e9);
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 20px;
        font-weight: 700;
        color: white;
    }

    .sidebar-user-name {
        color: var(--sidebar-text);
        font-size: 16px;
        font-weight: 600;
        margin: 0;
    }

    .sidebar-user-role {
        color: var(--sidebar-muted);
        font-size: 12px;
        margin: 4px 0 0 0;
    }

    .sidebar-section-title {
        color: var(--sidebar-muted);
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin: 16px 0 8px 0;
    }

    .api-status {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 10px 14px;
        border-radius: var(--radius-sm);
        font-size: 12px;
        margin-top: 8px;
    }

    .api-status-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        flex-shrink: 0;
    }

    .api-status-connected {
        background: rgba(34, 197, 94, 0.15);
        color: #4ade80;
        border: 1px solid rgba(34, 197, 94, 0.2);
    }

    .api-status-connected .api-status-dot {
        background: #22c55e;
        box-shadow: 0 0 8px rgba(34, 197, 94, 0.5);
    }

    .sidebar-help-item {
        padding: 8px 0;
        font-size: 13px;
        color: var(--sidebar-muted);
        line-height: 1.5;
    }
</style>
"""

EVALUATION_STYLES = """
<style>
    .eval-result-card {
        background: var(--surface);
        backdrop-filter: blur(8px);
        border-radius: var(--radius-md);
        padding: 20px;
        border: 1px solid var(--card-border);
        margin: 12px 0;
        box-shadow: var(--shadow-sm);
    }

    .score-display {
        text-align: center;
        padding: 32px;
        border-radius: var(--radius-lg);
        margin: 16px 0;
        background: linear-gradient(135deg, rgba(37, 99, 235, 0.08) 0%, rgba(14, 165, 233, 0.06) 100%);
        border: 1px solid rgba(37, 99, 235, 0.12);
    }

    .score-value {
        font-size: 48px;
        font-weight: 700;
        margin: 8px 0;
        background: linear-gradient(135deg, var(--primary-dark), var(--accent));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }

    .score-label {
        font-size: 14px;
        color: var(--text-muted);
    }

    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, var(--primary), var(--accent));
        border-radius: 4px;
    }

    .metric-comparison {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 16px;
        margin: 16px 0;
    }

    .metric-item {
        background: var(--surface-muted);
        padding: 16px;
        border-radius: var(--radius-sm);
        text-align: center;
        border: 1px solid var(--card-border);
    }

    .report-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 14px 16px;
        background: var(--surface-muted);
        border-radius: var(--radius-sm);
        margin: 8px 0;
        border: 1px solid var(--card-border);
    }

    .batch-progress {
        background: var(--surface-muted);
        padding: 20px;
        border-radius: var(--radius-md);
        margin: 16px 0;
        border: 1px solid var(--card-border);
    }
</style>
"""


def get_font_import() -> str:
    """Google Fonts 引入（需在 markdown 前加载）"""
    return FONT_IMPORT


def get_all_styles() -> str:
    """获取所有样式"""
    return (
        f"{GLOBAL_STYLES}"
        f"{AUTH_STYLES}"
        f"{MAIN_STYLES}"
        f"{SIDEBAR_STYLES}"
        f"{EVALUATION_STYLES}"
    )
