"""
Configuration and constants for the Business Analytics Platform.
"""

import os
from dataclasses import dataclass, field
from typing import List, Dict


# ─── App Metadata ────────────────────────────────────────────────────────────

APP_TITLE = "BizInsight Pro"
APP_SUBTITLE = "Intelligent Business Analytics Platform"
APP_VERSION = "1.0.0"
APP_ICON = "📊"

# ─── Color Palette ───────────────────────────────────────────────────────────

COLORS = {
    "primary": "#6C63FF",
    "secondary": "#3ECFCF",
    "accent": "#FF6584",
    "success": "#2EC4B6",
    "warning": "#FFBF69",
    "danger": "#FF6B6B",
    "dark": "#0F0F1A",
    "card_bg": "#1A1A2E",
    "surface": "#16213E",
    "text_primary": "#FFFFFF",
    "text_secondary": "#A0A0C0",
    "border": "#2D2D4E",
    "gradient_start": "#6C63FF",
    "gradient_end": "#3ECFCF",
}

CHART_COLORS = [
    "#6C63FF", "#3ECFCF", "#FF6584", "#FFBF69",
    "#2EC4B6", "#FF6B6B", "#A78BFA", "#34D399",
    "#F472B6", "#60A5FA", "#FBBF24", "#A3E635",
]

# ─── Chart Defaults ───────────────────────────────────────────────────────────

CHART_TEMPLATE = "plotly_dark"
CHART_HEIGHT = 400
CHART_FONT_FAMILY = "Inter, sans-serif"

PLOTLY_LAYOUT_DEFAULTS: Dict = {
    "template": CHART_TEMPLATE,
    "font": {"family": CHART_FONT_FAMILY, "color": COLORS["text_primary"]},
    "paper_bgcolor": "rgba(0,0,0,0)",
    "plot_bgcolor": "rgba(0,0,0,0)",
    "margin": {"l": 40, "r": 40, "t": 60, "b": 40},
    "legend": {
        "bgcolor": "rgba(0,0,0,0.3)",
        "bordercolor": COLORS["border"],
        "borderwidth": 1,
    },
}

# ─── Supported File Types ────────────────────────────────────────────────────

SUPPORTED_EXTENSIONS = ["csv", "xlsx", "xls", "json"]
MAX_FILE_SIZE_MB = 100
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# ─── Analytics Defaults ──────────────────────────────────────────────────────

DEFAULT_DATE_COLUMNS = [
    "date", "Date", "DATE", "period", "Period", "month", "Month",
    "year", "Year", "quarter", "Quarter", "time", "Time", "timestamp",
    "Timestamp", "created_at", "updated_at",
]

DEFAULT_REVENUE_COLUMNS = [
    "revenue", "Revenue", "REVENUE", "sales", "Sales", "SALES",
    "income", "Income", "turnover", "Turnover", "gross_revenue",
    "total_revenue", "net_revenue",
]

DEFAULT_EXPENSE_COLUMNS = [
    "expense", "Expense", "EXPENSE", "expenses", "Expenses", "cost",
    "Cost", "costs", "Costs", "operating_expense", "total_expense",
    "expenditure",
]

DEFAULT_PROFIT_COLUMNS = [
    "profit", "Profit", "PROFIT", "net_profit", "net_income",
    "Net Income", "earnings", "Earnings", "EBIT", "EBITDA",
]

ANOMALY_THRESHOLD_ZSCORE = 3.0
ANOMALY_IQR_MULTIPLIER = 1.5

# ─── AI / Gemini ─────────────────────────────────────────────────────────────

GEMINI_MODEL = "gemini-1.5-flash"
GEMINI_MAX_TOKENS = 2048
GEMINI_TEMPERATURE = 0.3

AI_ANALYSIS_TYPES = [
    "trend_analysis",
    "anomaly_detection",
    "recommendations",
    "executive_summary",
    "forecasting",
    "comparative_analysis",
]

# ─── KPI Thresholds ──────────────────────────────────────────────────────────

KPI_GROWTH_THRESHOLDS = {
    "excellent": 20,    # > 20% growth → excellent
    "good": 10,         # 10–20% → good
    "neutral": 0,       # 0–10%  → neutral
    "warning": -10,     # -10–0% → warning
    # below -10% → danger
}

# ─── Report Defaults ─────────────────────────────────────────────────────────

REPORT_LOGO_PATH = "assets/logo.png"
REPORT_FONT = "Helvetica"
PDF_PAGE_SIZE = "A4"

# ─── Session State Keys ──────────────────────────────────────────────────────

SESSION_KEYS = [
    "current_df",
    "previous_df",
    "current_filename",
    "previous_filename",
    "ai_insights_cache",
    "selected_date_col",
    "selected_revenue_col",
    "selected_expense_col",
    "selected_profit_col",
    "date_range",
    "analysis_complete",
]

# ─── Sidebar Sections ────────────────────────────────────────────────────────

SIDEBAR_SECTIONS = [
    "📤 Data Upload",
    "⚙️ Column Mapping",
    "🔍 Filters",
    "🤖 AI Settings",
]

# ─── Navigation Pages ────────────────────────────────────────────────────────

PAGES = [
    "🏠 Overview",
    "📈 Analytics",
    "🤖 AI Insights",
    "📊 Visualizations",
    "📑 Reports",
]
