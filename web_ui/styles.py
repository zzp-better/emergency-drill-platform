"""
CSS 样式模块
包含所有 Streamlit UI 的自定义样式
"""

# 自定义 CSS 样式
CUSTOM_CSS = """
<style>
/* ════════════════════════════════════════════════════
   全局字体与颜色变量
════════════════════════════════════════════════════ */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {
    --primary:     #3B82F6;
    --primary-dark:#2563EB;
    --danger:      #EF4444;
    --danger-dark: #DC2626;
    --success:     #10B981;
    --warning:     #F59E0B;
    --sidebar-bg:  #0F172A;
    --sidebar-2:   #1E293B;
    --card-bg:     #FFFFFF;
    --page-bg:     #F1F5F9;
    --text-1:      #0F172A;
    --text-2:      #475569;
    --text-3:      #94A3B8;
    --border:      #E2E8F0;
    --radius:      12px;
    --radius-sm:   8px;
    --shadow-sm:   0 1px 3px rgba(0,0,0,.08), 0 1px 2px rgba(0,0,0,.05);
    --shadow:      0 4px 12px rgba(0,0,0,.08), 0 2px 4px rgba(0,0,0,.04);
    --shadow-lg:   0 10px 30px rgba(0,0,0,.10), 0 4px 10px rgba(0,0,0,.06);
}

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

/* 主内容区背景 */
.stApp {
    background: var(--page-bg);
}

/* ════════════════════════════════════════════════════
   侧边栏
════════════════════════════════════════════════════ */
section[data-testid="stSidebar"] > div {
    background: #1A2235 !important;
    border-right: 1px solid #243049;
}

/* 标题区 */
section[data-testid="stSidebar"] h1 {
    color: #FFFFFF !important;
    font-size: 1.25rem !important;
    font-weight: 800 !important;
    letter-spacing: -0.3px;
    padding: 4px 0 10px 0;
}

/* 主文字 —— 提高至近白色，确保在深色底下清晰可读 */
section[data-testid="stSidebar"] .stMarkdown p,
section[data-testid="stSidebar"] .stRadio label,
section[data-testid="stSidebar"] p {
    color: #E2E8F0 !important;
}

/* 分区小标题（如"系统状态"）*/
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3,
section[data-testid="stSidebar"] .stSubheader {
    color: #64748B !important;
    font-size: 0.65rem !important;
    font-weight: 700 !important;
    text-transform: uppercase;
    letter-spacing: .12em;
}

/* ── 导航 Radio 样式 ── */
section[data-testid="stSidebar"] .stRadio > div {
    gap: 3px !important;
}

/* 每一项默认：大号字 + 近白色文字 */
section[data-testid="stSidebar"] .stRadio label {
    background: transparent !important;
    border-radius: 8px !important;
    padding: 10px 14px !important;
    transition: background .15s, color .15s !important;
    cursor: pointer;
    width: 100%;
    color: #D1D9E6 !important;
    font-size: 0.92rem !important;
    font-weight: 500 !important;
    border-left: 3px solid transparent !important;
}

/* Hover：稍亮背景 + 纯白文字 */
section[data-testid="stSidebar"] .stRadio label:hover {
    background: #243049 !important;
    color: #FFFFFF !important;
}

/* ── 选中状态（双选择器保证兼容性）──
   方案1: :has(input:checked) — 现代浏览器
   方案2: [aria-checked="true"] — 旧版 Streamlit DOM   */
section[data-testid="stSidebar"] label[data-baseweb="radio"]:has(input:checked),
section[data-testid="stSidebar"] .stRadio [aria-checked="true"] {
    background: #3B82F6 !important;
    border-left: 3px solid #93C5FD !important;
    box-shadow: 0 2px 10px rgba(59, 130, 246, 0.4) !important;
}

/* 选中项文字强制白色 */
section[data-testid="stSidebar"] label[data-baseweb="radio"]:has(input:checked) *,
section[data-testid="stSidebar"] label[data-baseweb="radio"]:has(input:checked) {
    color: #FFFFFF !important;
}

/* 隐藏 Radio 原生圆形按钮（用背景色表示选中更清晰）*/
section[data-testid="stSidebar"] [data-baseweb="radio"] > div:first-child {
    display: none !important;
}

/* 分隔线 */
section[data-testid="stSidebar"] hr {
    border-color: #243049 !important;
    margin: 10px 0;
}

/* 侧边栏内的 Alert 组件 */
section[data-testid="stSidebar"] .stAlert {
    border-radius: 8px !important;
    font-size: 0.82rem !important;
}
section[data-testid="stSidebar"] [data-testid="stNotification"] {
    background: #243049 !important;
    border-color: #334E6E !important;
}
section[data-testid="stSidebar"] [data-testid="stNotification"] p,
section[data-testid="stSidebar"] [data-testid="stNotification"] span {
    color: #E2E8F0 !important;
}

/* ════════════════════════════════════════════════════
   页头
════════════════════════════════════════════════════ */
.main-header {
    font-size: 2.4rem;
    font-weight: 800;
    background: linear-gradient(135deg, #EF4444 0%, #3B82F6 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    text-align: center;
    padding: 0.6rem 0 0.2rem 0;
    letter-spacing: -1px;
    line-height: 1.2;
}

/* ════════════════════════════════════════════════════
   通用卡片
════════════════════════════════════════════════════ */
.edap-card {
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 18px 20px;
    margin-bottom: 12px;
    box-shadow: var(--shadow-sm);
    transition: box-shadow .2s, transform .2s;
}
.edap-card:hover {
    box-shadow: var(--shadow);
    transform: translateY(-1px);
}

/* ── Metric 卡片 ── */
.metric-card {
    background: var(--card-bg);
    border-radius: var(--radius);
    padding: 20px 22px;
    box-shadow: var(--shadow);
    border-top: 4px solid transparent;
    position: relative;
    overflow: hidden;
}
.metric-card::after {
    content: '';
    position: absolute;
    top: 0; right: 0;
    width: 80px; height: 80px;
    border-radius: 50%;
    background: currentColor;
    opacity: .04;
    transform: translate(30%, -30%);
}
.metric-card.blue  { border-top-color: #3B82F6; color: #3B82F6; }
.metric-card.green { border-top-color: #10B981; color: #10B981; }
.metric-card.amber { border-top-color: #F59E0B; color: #F59E0B; }
.metric-card.red   { border-top-color: #EF4444; color: #EF4444; }

.metric-card .mc-icon {
    font-size: 1.8rem;
    margin-bottom: 8px;
    display: block;
}
.metric-card .mc-value {
    font-size: 2rem;
    font-weight: 800;
    color: var(--text-1);
    line-height: 1;
    margin-bottom: 4px;
}
.metric-card .mc-label {
    font-size: 0.78rem;
    color: var(--text-3);
    text-transform: uppercase;
    letter-spacing: .06em;
    font-weight: 600;
}
.metric-card .mc-sub {
    font-size: 0.82rem;
    color: var(--text-2);
    margin-top: 6px;
}

/* ════════════════════════════════════════════════════
   状态徽章
════════════════════════════════════════════════════ */
.badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    border-radius: 20px;
    padding: 3px 10px;
    font-size: 0.75rem;
    font-weight: 600;
    line-height: 1.5;
}
.badge-ok   { background: #D1FAE5; color: #065F46; }
.badge-warn { background: #FEF3C7; color: #92400E; }
.badge-err  { background: #FEE2E2; color: #991B1B; }
.badge-info { background: #DBEAFE; color: #1E40AF; }
.badge-gray { background: #F1F5F9; color: #475569; }

.status-success { color: #059669; font-weight: 600; }
.status-error   { color: #DC2626; font-weight: 600; }
.status-warning { color: #D97706; font-weight: 600; }

/* ════════════════════════════════════════════════════
   分区标题
════════════════════════════════════════════════════ */
.section-title {
    font-size: 0.72rem;
    font-weight: 700;
    color: var(--text-3);
    text-transform: uppercase;
    letter-spacing: .1em;
    padding: 0 0 8px 0;
    border-bottom: 2px solid var(--border);
    margin-bottom: 14px;
}

/* ════════════════════════════════════════════════════
   快捷操作卡片（首页）
════════════════════════════════════════════════════ */
.quick-action {
    background: var(--card-bg);
    border: 1.5px solid var(--border);
    border-radius: var(--radius);
    padding: 16px 18px;
    display: flex;
    align-items: center;
    gap: 12px;
    cursor: pointer;
    transition: border-color .2s, box-shadow .2s, transform .2s;
}
.quick-action:hover {
    border-color: var(--primary);
    box-shadow: 0 0 0 3px rgba(59,130,246,.1);
    transform: translateY(-1px);
}
.quick-action .qa-icon { font-size: 1.5rem; }
.quick-action .qa-label { font-size: 0.9rem; font-weight: 600; color: var(--text-1); }
.quick-action .qa-desc { font-size: 0.78rem; color: var(--text-2); }

/* ════════════════════════════════════════════════════
   按钮覆盖
════════════════════════════════════════════════════ */
.stButton > button {
    border-radius: var(--radius-sm) !important;
    font-weight: 600 !important;
    font-size: 0.875rem !important;
    padding: 8px 16px !important;
    transition: all .15s !important;
    border-width: 1.5px !important;
}
.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: var(--shadow-sm);
}
/* Primary button */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%) !important;
    border-color: var(--primary-dark) !important;
    box-shadow: 0 2px 8px rgba(59,130,246,.3) !important;
}
.stButton > button[kind="primary"]:hover {
    box-shadow: 0 4px 14px rgba(59,130,246,.4) !important;
}

/* ════════════════════════════════════════════════════
   输入框 / 选择框
════════════════════════════════════════════════════ */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div {
    border-radius: var(--radius-sm) !important;
    border: 1.5px solid var(--border) !important;
    font-size: 0.875rem !important;
    transition: border-color .15s, box-shadow .15s !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: var(--primary) !important;
    box-shadow: 0 0 0 3px rgba(59,130,246,.12) !important;
}

/* ════════════════════════════════════════════════════
   Metric 组件（Streamlit 原生）
════════════════════════════════════════════════════ */
[data-testid="metric-container"] {
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 14px 18px !important;
    box-shadow: var(--shadow-sm);
}
[data-testid="stMetricLabel"] {
    font-size: 0.78rem !important;
    color: var(--text-3) !important;
    text-transform: uppercase;
    letter-spacing: .05em;
    font-weight: 600 !important;
}
[data-testid="stMetricValue"] {
    font-size: 1.8rem !important;
    font-weight: 800 !important;
    color: var(--text-1) !important;
}

/* ════════════════════════════════════════════════════
   Expander
════════════════════════════════════════════════════ */
[data-testid="stExpander"] {
    border: 1.5px solid var(--border) !important;
    border-radius: var(--radius) !important;
    box-shadow: var(--shadow-sm) !important;
    overflow: hidden;
    margin-bottom: 8px;
}
[data-testid="stExpander"] > details > summary {
    background: var(--card-bg) !important;
    padding: 12px 16px !important;
    font-weight: 600 !important;
    font-size: 0.875rem !important;
    color: var(--text-1) !important;
    transition: background .15s;
}
[data-testid="stExpander"] > details > summary:hover {
    background: #F8FAFC !important;
}
[data-testid="stExpander"] > details[open] > summary {
    border-bottom: 1.5px solid var(--border);
}

/* ════════════════════════════════════════════════════
   Tabs
════════════════════════════════════════════════════ */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    background: var(--card-bg);
    border-radius: var(--radius) var(--radius) 0 0;
    padding: 4px 4px 0 4px;
    border-bottom: 2px solid var(--border);
}
.stTabs [data-baseweb="tab"] {
    border-radius: var(--radius-sm) var(--radius-sm) 0 0 !important;
    padding: 8px 16px !important;
    font-size: 0.875rem !important;
    font-weight: 600 !important;
    color: var(--text-2) !important;
    transition: all .15s !important;
}
.stTabs [aria-selected="true"] {
    color: var(--primary) !important;
    background: transparent !important;
    border-bottom: 2px solid var(--primary) !important;
}

/* ════════════════════════════════════════════════════
   Dataframe / 表格
════════════════════════════════════════════════════ */
.stDataFrame {
    border-radius: var(--radius) !important;
    overflow: hidden;
    border: 1.5px solid var(--border) !important;
    box-shadow: var(--shadow-sm) !important;
}

/* ════════════════════════════════════════════════════
   Alert / info / warning / error
════════════════════════════════════════════════════ */
.stAlert {
    border-radius: var(--radius-sm) !important;
    border-width: 1.5px !important;
    font-size: 0.875rem !important;
}
[data-testid="stNotification"] {
    border-radius: var(--radius-sm) !important;
}

/* ════════════════════════════════════════════════════
   Progress bar
════════════════════════════════════════════════════ */
.stProgress > div > div > div > div {
    background: linear-gradient(90deg, var(--primary) 0%, #60A5FA 100%) !important;
    border-radius: 4px !important;
}

/* ════════════════════════════════════════════════════
   分隔线
════════════════════════════════════════════════════ */
hr {
    border-color: var(--border) !important;
    margin: 16px 0 !important;
}

/* ════════════════════════════════════════════════════
   标题层级
════════════════════════════════════════════════════ */
h1 { font-weight: 800 !important; color: var(--text-1) !important; letter-spacing: -.5px; }
h2 { font-weight: 700 !important; color: var(--text-1) !important; font-size: 1.3rem !important; }
h3 { font-weight: 600 !important; color: var(--text-1) !important; font-size: 1.05rem !important; }

/* ════════════════════════════════════════════════════
   Checkbox / Radio
════════════════════════════════════════════════════ */
.stCheckbox label, .stRadio label {
    font-size: 0.875rem !important;
    color: var(--text-1) !important;
}
</style>
"""


def apply_styles():
    """应用自定义 CSS 样式"""
    import streamlit as st
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
