"""
Reusable Streamlit UI components for the Business Analytics Platform.
"""

from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st

from config import APP_ICON, APP_SUBTITLE, APP_TITLE, COLORS, PAGES
from utils import format_currency, format_number, format_percentage, growth_arrow


# ─── Page Config ─────────────────────────────────────────────────────────────


def set_page_config() -> None:
    """Configure Streamlit page settings (must be first Streamlit call)."""
    st.set_page_config(
        page_title=f"{APP_TITLE} – Business Analytics",
        page_icon=APP_ICON,
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            "Get Help": None,
            "Report a bug": None,
            "About": f"**{APP_TITLE}** v1.0 – Intelligent Business Analytics Platform",
        },
    )


# ─── CSS Injection ────────────────────────────────────────────────────────────


def inject_css() -> None:
    """Inject custom CSS for the professional dark theme."""
    try:
        with open("assets/style.css", "r") as f:
            css = f.read()
    except FileNotFoundError:
        css = _fallback_css()

    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def _fallback_css() -> str:
    """Minimal inline fallback CSS if the external file is missing."""
    return """
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .main { background: #0F0F1A; }

    .kpi-card {
        background: linear-gradient(135deg, #1A1A2E 0%, #16213E 100%);
        border: 1px solid #2D2D4E;
        border-radius: 16px;
        padding: 1.4rem 1.8rem;
        text-align: center;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        margin-bottom: 1rem;
    }
    .kpi-card:hover { transform: translateY(-3px); box-shadow: 0 8px 24px rgba(108,99,255,0.2); }
    .kpi-label { font-size: 0.78rem; color: #A0A0C0; text-transform: uppercase; letter-spacing: 1.2px; margin-bottom: 0.3rem; }
    .kpi-value { font-size: 2rem; font-weight: 700; color: #FFFFFF; margin-bottom: 0.2rem; }
    .kpi-delta { font-size: 0.85rem; font-weight: 500; }
    .kpi-delta.positive { color: #2EC4B6; }
    .kpi-delta.negative { color: #FF6B6B; }
    .kpi-delta.neutral  { color: #A0A0C0; }

    .section-header {
        font-size: 1.4rem; font-weight: 700; color: #FFFFFF;
        border-left: 4px solid #6C63FF; padding-left: 0.8rem;
        margin: 1.5rem 0 1rem 0;
    }
    .insight-card {
        background: #1A1A2E; border: 1px solid #2D2D4E;
        border-radius: 12px; padding: 1.2rem; margin-bottom: 0.8rem;
    }
    .badge {
        display: inline-block; padding: 0.2rem 0.6rem;
        border-radius: 50px; font-size: 0.72rem; font-weight: 600;
        text-transform: uppercase; letter-spacing: 0.8px;
    }
    .badge-success { background: rgba(46,196,182,0.15); color: #2EC4B6; border: 1px solid #2EC4B6; }
    .badge-warning { background: rgba(255,191,105,0.15); color: #FFBF69; border: 1px solid #FFBF69; }
    .badge-danger  { background: rgba(255,107,107,0.15); color: #FF6B6B; border: 1px solid #FF6B6B; }
    .badge-info    { background: rgba(108,99,255,0.15);  color: #6C63FF; border: 1px solid #6C63FF; }

    .stMetric > div { background: #1A1A2E; border-radius: 12px; padding: 0.8rem; }
    """


# ─── Header ───────────────────────────────────────────────────────────────────


def render_header(current_page: str = "") -> None:
    """Render the application header."""
    st.markdown(f"""
    <div style="display:flex; align-items:center; gap:1rem; padding: 0.5rem 0 1.5rem 0; border-bottom: 1px solid #2D2D4E; margin-bottom: 1.5rem;">
        <div style="font-size:2.4rem;">{APP_ICON}</div>
        <div>
            <div style="font-size:1.7rem; font-weight:800; color:#FFFFFF; letter-spacing:-0.5px;">{APP_TITLE}</div>
            <div style="font-size:0.85rem; color:#A0A0C0;">{APP_SUBTITLE}</div>
        </div>
        {"<div style='margin-left:auto;'><span class='badge badge-info'>" + current_page + "</span></div>" if current_page else ""}
    </div>
    """, unsafe_allow_html=True)


# ─── KPI Cards ────────────────────────────────────────────────────────────────


def kpi_card(
    label: str,
    value: Any,
    delta: Optional[float] = None,
    prefix: str = "",
    suffix: str = "",
    is_currency: bool = False,
    is_percentage: bool = False,
) -> None:
    """Render a styled KPI card."""
    if value is None:
        formatted_val = "—"
    elif is_currency:
        formatted_val = format_currency(float(value))
    elif is_percentage:
        formatted_val = format_percentage(float(value))
    else:
        formatted_val = f"{prefix}{format_number(float(value))}{suffix}"

    delta_html = ""
    if delta is not None:
        arrow = growth_arrow(delta)
        cls = "positive" if delta > 0 else "negative" if delta < 0 else "neutral"
        delta_html = f'<div class="kpi-delta {cls}">{arrow} {format_percentage(delta)} vs prev</div>'

    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{formatted_val}</div>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)


def kpi_row(kpis: Dict[str, Any]) -> None:
    """Render a row of 4 KPI cards from a kpis dict."""
    cols = st.columns(4)
    card_defs = [
        ("💰 Revenue", kpis.get("total_revenue"), kpis.get("revenue_growth"), True, False),
        ("💸 Expenses", kpis.get("total_expenses"), kpis.get("expense_growth"), True, False),
        ("📈 Net Profit", kpis.get("net_profit"), kpis.get("profit_growth"), True, False),
        ("🎯 Profit Margin", kpis.get("profit_margin"), None, False, True),
    ]
    for col, (label, value, delta, is_curr, is_pct) in zip(cols, card_defs):
        with col:
            kpi_card(label, value, delta, is_currency=is_curr, is_percentage=is_pct)


# ─── Section Header ───────────────────────────────────────────────────────────


def section_header(title: str, subtitle: str = "") -> None:
    """Render a styled section header."""
    sub_html = f'<div style="font-size:0.85rem; color:#A0A0C0; margin-top:0.2rem;">{subtitle}</div>' if subtitle else ""
    st.markdown(f"""
    <div class="section-header">
        {title}
        {sub_html}
    </div>
    """, unsafe_allow_html=True)


# ─── Info / Alert Cards ───────────────────────────────────────────────────────


def info_card(content: str, level: str = "info") -> None:
    """Render a styled info card (info/success/warning/danger)."""
    icons = {"info": "ℹ️", "success": "✅", "warning": "⚠️", "danger": "🚨"}
    colors_map = {
        "info": ("rgba(108,99,255,0.1)", "#6C63FF"),
        "success": ("rgba(46,196,182,0.1)", "#2EC4B6"),
        "warning": ("rgba(255,191,105,0.1)", "#FFBF69"),
        "danger": ("rgba(255,107,107,0.1)", "#FF6B6B"),
    }
    bg, border = colors_map.get(level, colors_map["info"])
    icon = icons.get(level, "ℹ️")
    st.markdown(f"""
    <div style="background:{bg}; border-left:4px solid {border}; border-radius:8px;
                padding:0.9rem 1.2rem; margin:0.5rem 0; color:#FFFFFF; font-size:0.9rem;">
        {icon} {content}
    </div>
    """, unsafe_allow_html=True)


# ─── AI Insight Cards ─────────────────────────────────────────────────────────


def ai_insight_card(title: str, content: str, icon: str = "🤖") -> None:
    """Render a styled AI insight markdown card."""
    st.markdown(f"""
    <div class="insight-card">
        <div style="font-size:1rem; font-weight:600; color:#6C63FF; margin-bottom:0.6rem;">
            {icon} {title}
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown(content)


# ─── Data Preview ─────────────────────────────────────────────────────────────


def data_preview(df: pd.DataFrame, n_rows: int = 5, title: str = "Data Preview") -> None:
    """Render a collapsible data preview table."""
    with st.expander(f"🔍 {title} ({len(df):,} rows × {len(df.columns)} cols)", expanded=False):
        st.dataframe(df.head(n_rows), use_container_width=True)


def schema_info(schema: Dict) -> None:
    """Render a compact schema overview."""
    with st.expander("📋 Schema & Column Info", expanded=False):
        cols = st.columns(2)
        with cols[0]:
            st.write("**Detected Column Roles**")
            for role, col_key in [
                ("📅 Date", "date_column"),
                ("💰 Revenue", "revenue_column"),
                ("💸 Expenses", "expense_column"),
                ("📈 Profit", "profit_column"),
            ]:
                val = schema.get(col_key, "Not detected")
                st.write(f"{role}: `{val}`")

        with cols[1]:
            st.write("**Column Types**")
            col_info = schema.get("columns", {})
            type_summary: Dict[str, int] = {}
            for info in col_info.values():
                t = info.get("semantic_type", "unknown")
                type_summary[t] = type_summary.get(t, 0) + 1
            for t, count in type_summary.items():
                st.write(f"{t.capitalize()}: **{count}**")


# ─── Sidebar Upload Section ───────────────────────────────────────────────────


def sidebar_upload_section() -> tuple:
    """
    Render the sidebar file upload UI and return (current_file, previous_file).
    """
    st.sidebar.markdown("## 📤 Data Upload")
    st.sidebar.markdown('<p style="color:#A0A0C0; font-size:0.82rem;">Upload CSV, Excel, or JSON files</p>', unsafe_allow_html=True)

    current_file = st.sidebar.file_uploader(
        "Current Period Dataset",
        type=["csv", "xlsx", "xls", "json"],
        key="current_upload",
        help="Upload the primary dataset to analyze",
    )
    st.sidebar.markdown("---")
    previous_file = st.sidebar.file_uploader(
        "Previous Period Dataset (Optional)",
        type=["csv", "xlsx", "xls", "json"],
        key="previous_upload",
        help="Upload a comparison dataset for YoY analysis",
    )
    return current_file, previous_file


def sidebar_column_mapping(df: pd.DataFrame, schema: Dict) -> Dict[str, str]:
    """Render column mapping controls in the sidebar."""
    st.sidebar.markdown("## ⚙️ Column Mapping")
    cols = ["— Auto Detect —"] + df.columns.tolist()

    mapping: Dict[str, str] = {}
    for role, key in [
        ("Date Column", "date_column"),
        ("Revenue Column", "revenue_column"),
        ("Expense Column", "expense_column"),
        ("Profit Column", "profit_column"),
    ]:
        detected = schema.get(key, "")
        default_idx = cols.index(detected) if detected in cols else 0
        selected = st.sidebar.selectbox(role, cols, index=default_idx, key=f"col_map_{key}")
        if selected != "— Auto Detect —":
            mapping[key] = selected
        elif detected:
            mapping[key] = detected

    return mapping


def sidebar_filters(df: pd.DataFrame, date_col: Optional[str]) -> Dict:
    """Render dynamic filter controls in the sidebar."""
    st.sidebar.markdown("## 🔍 Filters")
    filters: Dict = {}

    if date_col and date_col in df.columns:
        min_date = df[date_col].min()
        max_date = df[date_col].max()
        if pd.notna(min_date) and pd.notna(max_date):
            date_range = st.sidebar.date_input(
                "Date Range",
                value=(min_date.date(), max_date.date()),
                min_value=min_date.date(),
                max_value=max_date.date(),
                key="date_filter",
            )
            if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
                filters["date_range"] = date_range

    cat_cols = df.select_dtypes(include=["object", "category"]).columns[:3]
    for col in cat_cols:
        unique_vals = sorted(df[col].dropna().unique().tolist())
        if 2 <= len(unique_vals) <= 50:
            selected = st.sidebar.multiselect(
                f"Filter by {col}",
                unique_vals,
                default=unique_vals,
                key=f"filter_{col}",
            )
            if selected and len(selected) < len(unique_vals):
                filters[col] = selected

    return filters


def sidebar_ai_settings() -> tuple:
    """Render AI settings in the sidebar and return (api_key, enable_ai)."""
    st.sidebar.markdown("## 🤖 AI Settings")
    import os
    default_key = os.environ.get("GEMINI_API_KEY", "")
    api_key = st.sidebar.text_input(
        "Gemini API Key",
        value=default_key,
        type="password",
        help="Enter your Google Gemini API key",
        key="gemini_api_key",
    )
    enable_ai = st.sidebar.toggle("Enable AI Insights", value=bool(api_key), key="enable_ai")
    return api_key, enable_ai


# ─── Navigation ───────────────────────────────────────────────────────────────


def render_navigation() -> str:
    """Render a horizontal tab navigation and return the selected page."""
    selected = st.radio(
        "Navigation",
        PAGES,
        horizontal=True,
        label_visibility="collapsed",
        key="nav_page",
    )
    st.markdown('<hr style="border-color:#2D2D4E; margin: 0.5rem 0 1.5rem 0;">', unsafe_allow_html=True)
    return selected


# ─── Progress / Loading ───────────────────────────────────────────────────────


def show_loading(message: str = "Processing…") -> Any:
    """Return a Streamlit spinner context."""
    return st.spinner(message)


# ─── Empty State ─────────────────────────────────────────────────────────────


def empty_state(
    title: str = "No Data Loaded",
    message: str = "Upload a dataset using the sidebar to get started.",
    icon: str = "📂",
) -> None:
    """Render a friendly empty state message."""
    st.markdown(f"""
    <div style="text-align:center; padding: 4rem 2rem; color: #A0A0C0;">
        <div style="font-size:4rem; margin-bottom:1rem;">{icon}</div>
        <div style="font-size:1.4rem; font-weight:600; color:#FFFFFF; margin-bottom:0.5rem;">{title}</div>
        <div style="font-size:0.9rem;">{message}</div>
    </div>
    """, unsafe_allow_html=True)


# ─── Anomaly Table ────────────────────────────────────────────────────────────


def anomaly_table(anomalies_df: pd.DataFrame) -> None:
    """Render the anomaly detection results."""
    if anomalies_df.empty:
        info_card("No anomalies detected in the current dataset.", level="success")
        return

    section_header("⚠️ Detected Anomalies", f"{len(anomalies_df)} anomalous records found")
    display_cols = [c for c in anomalies_df.columns if not c.startswith("_")]
    st.dataframe(
        anomalies_df[display_cols].head(50),
        use_container_width=True,
    )


# ─── Comparison Metric ────────────────────────────────────────────────────────


def comparison_metric(
    label: str,
    current_val: Optional[float],
    previous_val: Optional[float],
    is_currency: bool = True,
) -> None:
    """Render a st.metric with delta for comparison."""
    if current_val is None:
        st.metric(label, "—")
        return

    from utils import calculate_growth
    fmt = format_currency if is_currency else format_number
    delta = calculate_growth(current_val, previous_val)
    delta_str = f"{delta:+.1f}%" if delta is not None else None
    st.metric(
        label=label,
        value=fmt(current_val),
        delta=delta_str,
    )
