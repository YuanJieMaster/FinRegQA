"""
设计 Token — 金融级高级感 UI
Design tokens inspired by premium fintech dashboards (glassmorphism + deep navy).
"""

DESIGN_TOKENS_CSS = """
:root {
    /* Brand — 深蓝金融主色 */
    --primary: #2563eb;
    --primary-dark: #1e40af;
    --primary-light: #3b82f6;
    --accent: #0ea5e9;
    --accent-glow: rgba(37, 99, 235, 0.35);

    /* Surfaces */
    --bg-page: #f8fafc;
    --bg-gradient: linear-gradient(165deg, #f8fafc 0%, #eef2ff 35%, #f1f5f9 70%, #e2e8f0 100%);
    --bg-auth: radial-gradient(ellipse 120% 80% at 20% 0%, #1e3a8a 0%, #0f172a 45%, #020617 100%);
    --surface: rgba(255, 255, 255, 0.78);
    --surface-solid: #ffffff;
    --surface-muted: rgba(241, 245, 249, 0.9);

    /* Glass */
    --glass-bg: rgba(255, 255, 255, 0.12);
    --glass-border: rgba(255, 255, 255, 0.16);
    --glass-blur: 20px;
    --card-border: rgba(226, 232, 240, 0.85);

    /* Sidebar — 深色玻璃侧栏 */
    --sidebar-bg: rgba(15, 23, 42, 0.88);
    --sidebar-border: rgba(255, 255, 255, 0.08);
    --sidebar-text: #f1f5f9;
    --sidebar-muted: #94a3b8;

    /* Typography */
    --font-sans: "Noto Sans SC", "PingFang SC", "Microsoft YaHei", system-ui, sans-serif;
    --text-primary: #0f172a;
    --text-secondary: #475569;
    --text-muted: #64748b;
    --text-inverse: #f8fafc;

    /* Semantic */
    --success: #059669;
    --success-bg: rgba(16, 185, 129, 0.12);
    --warning: #d97706;
    --warning-bg: rgba(245, 158, 11, 0.12);
    --error: #dc2626;
    --error-bg: rgba(239, 68, 68, 0.1);
    --info: #2563eb;
    --info-bg: rgba(37, 99, 235, 0.08);

    /* Radius & shadow */
    --radius-sm: 8px;
    --radius-md: 12px;
    --radius-lg: 16px;
    --radius-xl: 20px;
    --shadow-sm: 0 1px 2px rgba(15, 23, 42, 0.06);
    --shadow-md: 0 4px 16px rgba(15, 23, 42, 0.08), 0 1px 3px rgba(15, 23, 42, 0.04);
    --shadow-lg: 0 12px 40px rgba(15, 23, 42, 0.12), 0 4px 12px rgba(15, 23, 42, 0.06);
    --shadow-glow: 0 0 0 1px rgba(37, 99, 235, 0.08), 0 8px 32px rgba(37, 99, 235, 0.12);

    /* Streamlit theme bridge */
    --primary-color: var(--primary);
    --background-color: var(--bg-page);
    --secondary-background-color: var(--surface-solid);
    --text-color: var(--text-primary);
}
"""
