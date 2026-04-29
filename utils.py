"""
Helper functions and utilities for the Business Analytics Platform.
"""

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

# ─── Logging ─────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ─── Number Formatting ────────────────────────────────────────────────────────

def format_currency(value: float, symbol: str = "$", decimals: int = 2) -> str:
    """Format a numeric value as a currency string."""
    if pd.isna(value) or not np.isfinite(value):
        return "N/A"
    if abs(value) >= 1_000_000_000:
        return f"{symbol}{value / 1_000_000_000:.{decimals}f}B"
    if abs(value) >= 1_000_000:
        return f"{symbol}{value / 1_000_000:.{decimals}f}M"
    if abs(value) >= 1_000:
        return f"{symbol}{value / 1_000:.{decimals}f}K"
    return f"{symbol}{value:.{decimals}f}"


def format_percentage(value: float, decimals: int = 1) -> str:
    """Format a numeric value as a percentage string."""
    if pd.isna(value) or not np.isfinite(value):
        return "N/A"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.{decimals}f}%"


def format_number(value: float, decimals: int = 0) -> str:
    """Format a numeric value with thousands separators."""
    if pd.isna(value) or not np.isfinite(value):
        return "N/A"
    return f"{value:,.{decimals}f}"


# ─── Growth & Delta ───────────────────────────────────────────────────────────

def calculate_growth(current: float, previous: float) -> Optional[float]:
    """Calculate percentage growth between two values."""
    if previous is None or previous == 0 or pd.isna(previous):
        return None
    if pd.isna(current):
        return None
    return ((current - previous) / abs(previous)) * 100


def get_growth_status(growth: Optional[float]) -> str:
    """Return a status label based on the growth rate."""
    if growth is None:
        return "neutral"
    if growth > 20:
        return "excellent"
    if growth > 10:
        return "good"
    if growth >= 0:
        return "neutral"
    if growth >= -10:
        return "warning"
    return "danger"


def growth_arrow(growth: Optional[float]) -> str:
    """Return an arrow character indicating growth direction."""
    if growth is None:
        return "→"
    if growth > 0:
        return "↑"
    if growth < 0:
        return "↓"
    return "→"


# ─── Data Utilities ───────────────────────────────────────────────────────────

def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Divide safely, returning *default* when denominator is 0 or NaN."""
    if denominator is None or denominator == 0 or pd.isna(denominator):
        return default
    if pd.isna(numerator):
        return default
    return numerator / denominator


def detect_column_type(series: pd.Series) -> str:
    """Detect the semantic type of a DataFrame column."""
    name_lower = series.name.lower() if hasattr(series.name, "lower") else ""
    dtype = str(series.dtype)

    # Date/time
    if "datetime" in dtype:
        return "datetime"
    for kw in ["date", "time", "period", "month", "year", "quarter"]:
        if kw in name_lower:
            return "datetime"

    # Numeric
    if pd.api.types.is_numeric_dtype(series):
        for kw in ["revenue", "sales", "income", "turnover"]:
            if kw in name_lower:
                return "revenue"
        for kw in ["expense", "cost", "expenditure"]:
            if kw in name_lower:
                return "expense"
        for kw in ["profit", "margin", "ebit", "earning"]:
            if kw in name_lower:
                return "profit"
        for kw in ["qty", "quantity", "count", "volume", "units"]:
            if kw in name_lower:
                return "quantity"
        return "numeric"

    # Categorical
    if pd.api.types.is_categorical_dtype(series) or series.nunique() < 50:
        return "categorical"

    return "text"


def infer_date_column(df: pd.DataFrame) -> Optional[str]:
    """Return the most likely date column name from a DataFrame."""
    from config import DEFAULT_DATE_COLUMNS

    for col in DEFAULT_DATE_COLUMNS:
        if col in df.columns:
            return col
    for col in df.columns:
        if "datetime" in str(df[col].dtype).lower():
            return col
        if any(kw in col.lower() for kw in ["date", "time", "period", "month", "year"]):
            return col
    return None


def infer_numeric_column(df: pd.DataFrame, keywords: List[str]) -> Optional[str]:
    """Return the most likely numeric column matching given keywords."""
    for kw in keywords:
        for col in df.columns:
            if kw.lower() in col.lower() and pd.api.types.is_numeric_dtype(df[col]):
                return col
    # Fallback: first numeric column
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            return col
    return None


def parse_dates_flexible(series: pd.Series) -> pd.Series:
    """Try multiple date formats when parsing a string column."""
    formats = [
        "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y",
        "%Y/%m/%d", "%d-%m-%Y", "%m-%d-%Y",
        "%Y-%m", "%b %Y", "%B %Y", "%Y",
        "%d %b %Y", "%d %B %Y",
    ]
    for fmt in formats:
        try:
            parsed = pd.to_datetime(series, format=fmt, errors="coerce")
            if parsed.notna().sum() > len(series) * 0.5:
                return parsed
        except Exception:
            continue
    return pd.to_datetime(series, infer_datetime_format=True, errors="coerce")


# ─── Summary Statistics ───────────────────────────────────────────────────────

def compute_summary_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Return a DataFrame of descriptive statistics for numeric columns."""
    numeric_df = df.select_dtypes(include="number")
    if numeric_df.empty:
        return pd.DataFrame()
    stats = numeric_df.describe().T
    stats["missing"] = df[numeric_df.columns].isna().sum()
    stats["missing_pct"] = (stats["missing"] / len(df) * 100).round(2)
    return stats.round(4)


# ─── Sanitization ─────────────────────────────────────────────────────────────

def sanitize_column_name(name: str) -> str:
    """Convert a column name to a safe, clean identifier."""
    name = str(name).strip()
    name = re.sub(r"[^\w\s]", "", name)
    name = re.sub(r"\s+", "_", name)
    return name.lower()


def sanitize_dataframe_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of the DataFrame with sanitized column names."""
    df = df.copy()
    df.columns = [sanitize_column_name(c) for c in df.columns]
    return df


# ─── Date Utilities ───────────────────────────────────────────────────────────

def get_date_range_label(start: datetime, end: datetime) -> str:
    """Return a human-friendly date range label."""
    fmt = "%b %d, %Y"
    return f"{start.strftime(fmt)} – {end.strftime(fmt)}"


def extract_year_month(df: pd.DataFrame, date_col: str) -> pd.DataFrame:
    """Add 'year' and 'month' helper columns from a datetime column."""
    df = df.copy()
    df["_year"] = df[date_col].dt.year
    df["_month"] = df[date_col].dt.month
    df["_month_name"] = df[date_col].dt.strftime("%b")
    df["_year_month"] = df[date_col].dt.to_period("M").astype(str)
    return df


# ─── Validation ───────────────────────────────────────────────────────────────

def validate_file_size(size_bytes: int, max_mb: int = 100) -> Tuple[bool, str]:
    """Validate that the file size is within the allowed limit."""
    if size_bytes > max_mb * 1024 * 1024:
        return False, f"File exceeds the {max_mb} MB limit."
    return True, "OK"


def validate_dataframe(df: pd.DataFrame) -> Tuple[bool, str]:
    """Run basic sanity checks on a DataFrame."""
    if df is None or df.empty:
        return False, "Dataset is empty."
    if len(df.columns) < 2:
        return False, "Dataset must have at least 2 columns."
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    if not numeric_cols:
        return False, "Dataset must contain at least one numeric column."
    return True, "OK"


# ─── Misc ─────────────────────────────────────────────────────────────────────

def truncate_text(text: str, max_chars: int = 200) -> str:
    """Truncate text to a maximum length, adding ellipsis if needed."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0] + "…"


def get_file_extension(filename: str) -> str:
    """Return the lowercase file extension without the dot."""
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def color_for_value(value: float, thresholds: Optional[Dict] = None) -> str:
    """Return a CSS hex color based on a numeric value."""
    from config import COLORS, KPI_GROWTH_THRESHOLDS

    t = thresholds or KPI_GROWTH_THRESHOLDS
    if value > t["excellent"]:
        return COLORS["success"]
    if value > t["good"]:
        return COLORS["secondary"]
    if value >= t["neutral"]:
        return COLORS["text_secondary"]
    if value >= t["warning"]:
        return COLORS["warning"]
    return COLORS["danger"]


def deep_merge(base: Dict, override: Dict) -> Dict:
    """Recursively merge two dicts, with *override* taking precedence."""
    result = base.copy()
    for key, val in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(val, dict):
            result[key] = deep_merge(result[key], val)
        else:
            result[key] = val
    return result
