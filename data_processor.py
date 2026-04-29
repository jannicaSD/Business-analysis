"""
Data loading, cleaning, and transformation for the Business Analytics Platform.
"""

import io
import logging
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import streamlit as st

from config import (
    DEFAULT_DATE_COLUMNS,
    DEFAULT_EXPENSE_COLUMNS,
    DEFAULT_PROFIT_COLUMNS,
    DEFAULT_REVENUE_COLUMNS,
    MAX_FILE_SIZE_BYTES,
    SUPPORTED_EXTENSIONS,
)
from utils import (
    infer_date_column,
    infer_numeric_column,
    parse_dates_flexible,
    validate_dataframe,
    validate_file_size,
    logger,
)

# ─── Loaders ─────────────────────────────────────────────────────────────────


@st.cache_data(show_spinner=False)
def load_csv(content: bytes, **kwargs) -> pd.DataFrame:
    """Load a CSV file from bytes."""
    return pd.read_csv(io.BytesIO(content), **kwargs)


@st.cache_data(show_spinner=False)
def load_excel(content: bytes, **kwargs) -> pd.DataFrame:
    """Load an Excel file from bytes."""
    return pd.read_excel(io.BytesIO(content), **kwargs)


@st.cache_data(show_spinner=False)
def load_json(content: bytes, **kwargs) -> pd.DataFrame:
    """Load a JSON file from bytes."""
    try:
        df = pd.read_json(io.BytesIO(content), **kwargs)
    except ValueError:
        # Try records orientation
        df = pd.read_json(io.BytesIO(content), orient="records", **kwargs)
    return df


def load_uploaded_file(uploaded_file) -> Tuple[Optional[pd.DataFrame], str]:
    """
    Load a Streamlit UploadedFile into a DataFrame.

    Returns (DataFrame, error_message). If successful, error_message is "".
    """
    if uploaded_file is None:
        return None, "No file provided."

    content = uploaded_file.read()
    size_ok, size_msg = validate_file_size(len(content), MAX_FILE_SIZE_BYTES // (1024 * 1024))
    if not size_ok:
        return None, size_msg

    ext = uploaded_file.name.rsplit(".", 1)[-1].lower() if "." in uploaded_file.name else ""
    if ext not in SUPPORTED_EXTENSIONS:
        return None, f"Unsupported file type '.{ext}'. Supported: {', '.join(SUPPORTED_EXTENSIONS)}"

    try:
        if ext == "csv":
            df = load_csv(content)
        elif ext in ("xlsx", "xls"):
            df = load_excel(content)
        elif ext == "json":
            df = load_json(content)
        else:
            return None, f"Unknown extension: {ext}"
    except Exception as exc:
        logger.exception("Failed to load file %s", uploaded_file.name)
        return None, f"Failed to read file: {exc}"

    ok, msg = validate_dataframe(df)
    if not ok:
        return None, msg

    return df, ""


# ─── Preprocessing ────────────────────────────────────────────────────────────

def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply basic cleaning steps:
    - Strip whitespace from string columns
    - Remove fully-duplicate rows
    - Drop columns that are entirely NaN
    - Strip whitespace from column names
    """
    df = df.copy()
    # Normalize column names
    df.columns = [str(c).strip() for c in df.columns]
    # Drop fully-empty columns
    df.dropna(axis=1, how="all", inplace=True)
    # Drop fully-duplicate rows
    df.drop_duplicates(inplace=True)
    # Strip strings
    str_cols = df.select_dtypes(include="object").columns
    for col in str_cols:
        df[col] = df[col].astype(str).str.strip()
        df[col] = df[col].replace("nan", np.nan)
    return df


def auto_parse_dates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Attempt to parse date-like columns into datetime dtype automatically.
    """
    df = df.copy()
    date_candidates = [c for c in df.columns if any(
        kw in c.lower() for kw in ["date", "time", "period", "month", "year", "quarter"]
    )]
    for col in date_candidates:
        if df[col].dtype == object:
            parsed = parse_dates_flexible(df[col])
            if parsed.notna().sum() > len(df) * 0.5:
                df[col] = parsed
    return df


def detect_schema(df: pd.DataFrame) -> Dict:
    """
    Return a schema dict describing column types and inferred roles.
    """
    from utils import detect_column_type

    schema: Dict = {
        "columns": {},
        "date_column": infer_date_column(df),
        "revenue_column": infer_numeric_column(df, DEFAULT_REVENUE_COLUMNS),
        "expense_column": infer_numeric_column(df, DEFAULT_EXPENSE_COLUMNS),
        "profit_column": infer_numeric_column(df, DEFAULT_PROFIT_COLUMNS),
        "numeric_columns": df.select_dtypes(include="number").columns.tolist(),
        "categorical_columns": df.select_dtypes(include=["object", "category"]).columns.tolist(),
        "datetime_columns": df.select_dtypes(include=["datetime64"]).columns.tolist(),
        "row_count": len(df),
        "column_count": len(df.columns),
    }
    for col in df.columns:
        schema["columns"][col] = {
            "dtype": str(df[col].dtype),
            "semantic_type": detect_column_type(df[col]),
            "missing_count": int(df[col].isna().sum()),
            "unique_count": int(df[col].nunique()),
        }
    return schema


def preprocess(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
    """
    Full preprocessing pipeline: clean → parse dates → detect schema.

    Returns (cleaned_df, schema).
    """
    df = clean_dataframe(df)
    df = auto_parse_dates(df)
    schema = detect_schema(df)
    logger.info(
        "Preprocessing complete: %d rows × %d cols | date=%s, revenue=%s",
        schema["row_count"], schema["column_count"],
        schema["date_column"], schema["revenue_column"],
    )
    return df, schema


# ─── Filtering ────────────────────────────────────────────────────────────────

def filter_by_date(
    df: pd.DataFrame,
    date_col: str,
    start_date,
    end_date,
) -> pd.DataFrame:
    """Filter a DataFrame to a date range (inclusive)."""
    if date_col not in df.columns:
        return df
    mask = (df[date_col] >= pd.Timestamp(start_date)) & (df[date_col] <= pd.Timestamp(end_date))
    return df.loc[mask].reset_index(drop=True)


def filter_by_category(
    df: pd.DataFrame,
    col: str,
    values: List[str],
) -> pd.DataFrame:
    """Filter a DataFrame to rows where *col* is in *values*."""
    if col not in df.columns or not values:
        return df
    return df.loc[df[col].isin(values)].reset_index(drop=True)


# ─── Aggregation helpers ──────────────────────────────────────────────────────

def resample_timeseries(
    df: pd.DataFrame,
    date_col: str,
    value_col: str,
    freq: str = "ME",
    agg: str = "sum",
) -> pd.DataFrame:
    """
    Resample a time series to the given frequency.

    Parameters
    ----------
    freq : str
        Pandas offset alias: 'D', 'W', 'ME', 'QE', 'YE'
    agg : str
        Aggregation function: 'sum', 'mean', 'median', 'count'
    """
    if date_col not in df.columns or value_col not in df.columns:
        return pd.DataFrame()
    ts = df.set_index(date_col)[value_col].dropna()
    if not isinstance(ts.index, pd.DatetimeIndex):
        ts.index = pd.to_datetime(ts.index, errors="coerce")
    ts = ts.dropna()
    return getattr(ts.resample(freq), agg)().reset_index()


def pivot_year_month(
    df: pd.DataFrame,
    date_col: str,
    value_col: str,
    agg: str = "sum",
) -> pd.DataFrame:
    """
    Pivot a DataFrame to a year × month matrix for heatmap visualizations.
    """
    tmp = df.copy()
    tmp["_year"] = tmp[date_col].dt.year
    tmp["_month"] = tmp[date_col].dt.month
    pivot = tmp.pivot_table(
        index="_year", columns="_month", values=value_col,
        aggfunc=agg, fill_value=0,
    )
    pivot.columns = [
        ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
         "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][m - 1]
        for m in pivot.columns
    ]
    return pivot


# ─── Column Mapping ───────────────────────────────────────────────────────────

def apply_column_mapping(
    df: pd.DataFrame,
    mapping: Dict[str, str],
) -> pd.DataFrame:
    """
    Rename DataFrame columns according to a mapping dict.
    E.g. mapping = {"old_col": "revenue"}
    """
    return df.rename(columns=mapping)
