"""
Analytics calculations and metrics for the Business Analytics Platform.
"""

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

from config import ANOMALY_IQR_MULTIPLIER, ANOMALY_THRESHOLD_ZSCORE
from utils import calculate_growth, safe_divide


# ─── KPI Calculations ────────────────────────────────────────────────────────


def calculate_kpis(
    df: pd.DataFrame,
    revenue_col: Optional[str],
    expense_col: Optional[str],
    profit_col: Optional[str],
    date_col: Optional[str] = None,
    prev_df: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """
    Compute the core KPI set from a DataFrame.

    Returns a dict with keys such as 'total_revenue', 'total_expenses',
    'net_profit', 'profit_margin', plus optional YoY growth values.
    """
    kpis: Dict[str, Any] = {}

    # Revenue
    if revenue_col and revenue_col in df.columns:
        kpis["total_revenue"] = float(df[revenue_col].sum())
        kpis["avg_revenue"] = float(df[revenue_col].mean())
        kpis["max_revenue"] = float(df[revenue_col].max())
        kpis["min_revenue"] = float(df[revenue_col].min())
    else:
        kpis["total_revenue"] = None

    # Expenses
    if expense_col and expense_col in df.columns:
        kpis["total_expenses"] = float(df[expense_col].sum())
        kpis["avg_expenses"] = float(df[expense_col].mean())
    else:
        kpis["total_expenses"] = None

    # Profit
    if profit_col and profit_col in df.columns:
        kpis["net_profit"] = float(df[profit_col].sum())
    elif kpis["total_revenue"] is not None and kpis["total_expenses"] is not None:
        kpis["net_profit"] = kpis["total_revenue"] - kpis["total_expenses"]
    else:
        kpis["net_profit"] = None

    # Profit margin
    kpis["profit_margin"] = (
        safe_divide(kpis["net_profit"], kpis["total_revenue"]) * 100
        if kpis["net_profit"] is not None and kpis["total_revenue"]
        else None
    )

    # Expense ratio
    kpis["expense_ratio"] = (
        safe_divide(kpis["total_expenses"], kpis["total_revenue"]) * 100
        if kpis["total_expenses"] is not None and kpis["total_revenue"]
        else None
    )

    # Record count
    kpis["record_count"] = len(df)

    # YoY growth (vs previous dataset)
    if prev_df is not None:
        prev_revenue = float(prev_df[revenue_col].sum()) if revenue_col and revenue_col in prev_df.columns else None
        prev_expenses = float(prev_df[expense_col].sum()) if expense_col and expense_col in prev_df.columns else None
        prev_profit = (
            float(prev_df[profit_col].sum())
            if profit_col and profit_col in prev_df.columns
            else (prev_revenue - prev_expenses if prev_revenue and prev_expenses else None)
        )
        kpis["revenue_growth"] = calculate_growth(kpis["total_revenue"], prev_revenue)
        kpis["expense_growth"] = calculate_growth(kpis["total_expenses"], prev_expenses)
        kpis["profit_growth"] = calculate_growth(kpis["net_profit"], prev_profit)
        kpis["prev_total_revenue"] = prev_revenue
        kpis["prev_total_expenses"] = prev_expenses
        kpis["prev_net_profit"] = prev_profit
    else:
        kpis["revenue_growth"] = None
        kpis["expense_growth"] = None
        kpis["profit_growth"] = None

    return kpis


# ─── P&L Analysis ─────────────────────────────────────────────────────────────


def compute_pl_analysis(
    df: pd.DataFrame,
    date_col: str,
    revenue_col: Optional[str],
    expense_col: Optional[str],
    freq: str = "ME",
) -> pd.DataFrame:
    """
    Return a time-indexed P&L DataFrame with revenue, expenses, and profit.
    """
    if not date_col or date_col not in df.columns:
        return pd.DataFrame()

    tmp = df.set_index(date_col)
    if not isinstance(tmp.index, pd.DatetimeIndex):
        tmp.index = pd.to_datetime(tmp.index, errors="coerce")
    tmp = tmp.loc[tmp.index.notna()]

    result = pd.DataFrame(index=tmp.resample(freq).sum().index)
    result.index.name = "period"

    if revenue_col and revenue_col in tmp.columns:
        result["revenue"] = tmp[revenue_col].resample(freq).sum()
    if expense_col and expense_col in tmp.columns:
        result["expenses"] = tmp[expense_col].resample(freq).sum()

    if "revenue" in result.columns and "expenses" in result.columns:
        result["profit"] = result["revenue"] - result["expenses"]
        result["profit_margin"] = (
            result["profit"] / result["revenue"].replace(0, np.nan) * 100
        )

    return result.reset_index().dropna(how="all")


# ─── Trend Analysis ───────────────────────────────────────────────────────────


def compute_trend(series: pd.Series) -> Dict[str, Any]:
    """
    Compute linear trend statistics for a numeric time series.

    Returns slope, intercept, r_squared, direction, and strength.
    """
    y = series.dropna().values
    if len(y) < 3:
        return {"slope": None, "r_squared": None, "direction": "unknown", "strength": "insufficient data"}

    x = np.arange(len(y))
    slope, intercept, r_value, p_value, std_err = scipy_stats.linregress(x, y)

    direction = "upward" if slope > 0 else "downward" if slope < 0 else "flat"
    r2 = r_value ** 2
    if r2 >= 0.75:
        strength = "strong"
    elif r2 >= 0.5:
        strength = "moderate"
    elif r2 >= 0.25:
        strength = "weak"
    else:
        strength = "no clear trend"

    return {
        "slope": round(slope, 6),
        "intercept": round(float(intercept), 4),
        "r_squared": round(r2, 4),
        "p_value": round(float(p_value), 6),
        "direction": direction,
        "strength": strength,
        "trend_values": (intercept + slope * x).tolist(),
    }


# ─── Anomaly Detection ────────────────────────────────────────────────────────


def detect_anomalies(
    df: pd.DataFrame,
    value_col: str,
    method: str = "iqr",
) -> pd.DataFrame:
    """
    Detect anomalous rows in a DataFrame column.

    Parameters
    ----------
    method : str
        'iqr' (interquartile range) or 'zscore'
    """
    if value_col not in df.columns:
        return pd.DataFrame()

    result = df.copy()
    values = result[value_col]

    if method == "zscore":
        z_scores = np.abs(scipy_stats.zscore(values.dropna()))
        idx = values.dropna().index
        result["_anomaly_score"] = np.nan
        result.loc[idx, "_anomaly_score"] = z_scores
        result["_is_anomaly"] = result["_anomaly_score"] > ANOMALY_THRESHOLD_ZSCORE
    else:  # IQR
        q1 = values.quantile(0.25)
        q3 = values.quantile(0.75)
        iqr = q3 - q1
        lower = q1 - ANOMALY_IQR_MULTIPLIER * iqr
        upper = q3 + ANOMALY_IQR_MULTIPLIER * iqr
        result["_is_anomaly"] = (values < lower) | (values > upper)
        result["_anomaly_score"] = np.where(
            result["_is_anomaly"],
            np.abs(values - values.median()) / (iqr + 1e-10),
            0,
        )

    anomalies = result[result["_is_anomaly"]].copy()
    anomalies.drop(columns=["_is_anomaly"], inplace=True)
    return anomalies.sort_values("_anomaly_score", ascending=False)


# ─── Year-over-Year Comparison ────────────────────────────────────────────────


def yoy_comparison(
    current_df: pd.DataFrame,
    prev_df: pd.DataFrame,
    date_col: str,
    metrics: List[str],
    freq: str = "ME",
) -> pd.DataFrame:
    """
    Build a side-by-side year-over-year DataFrame for given metrics.
    """

    def _resample(df: pd.DataFrame) -> pd.DataFrame:
        tmp = df.set_index(date_col).select_dtypes(include="number")
        if not isinstance(tmp.index, pd.DatetimeIndex):
            tmp.index = pd.to_datetime(tmp.index, errors="coerce")
        return tmp[metrics].resample(freq).sum()

    curr_agg = _resample(current_df)
    prev_agg = _resample(prev_df)

    result = pd.DataFrame(index=curr_agg.index)
    for m in metrics:
        if m in curr_agg.columns:
            result[f"{m}_current"] = curr_agg[m]
        if m in prev_agg.columns:
            result[f"{m}_previous"] = prev_agg[m]
        if f"{m}_current" in result and f"{m}_previous" in result:
            result[f"{m}_growth"] = (
                (result[f"{m}_current"] - result[f"{m}_previous"])
                / result[f"{m}_previous"].replace(0, np.nan) * 100
            )
    return result.reset_index()


# ─── Depreciation ─────────────────────────────────────────────────────────────


def compute_depreciation(
    initial_value: float,
    useful_life_years: int,
    method: str = "straight_line",
    salvage_value: float = 0.0,
) -> pd.DataFrame:
    """
    Compute asset depreciation schedule.

    Parameters
    ----------
    method : str
        'straight_line', 'declining_balance', 'sum_of_years'
    """
    years = list(range(1, useful_life_years + 1))
    records = []

    if method == "straight_line":
        annual_dep = (initial_value - salvage_value) / useful_life_years
        book_value = initial_value
        for yr in years:
            book_value -= annual_dep
            records.append({"year": yr, "depreciation": annual_dep, "book_value": max(book_value, salvage_value)})

    elif method == "declining_balance":
        rate = 2 / useful_life_years  # double-declining
        book_value = initial_value
        for yr in years:
            dep = book_value * rate
            dep = min(dep, book_value - salvage_value)
            book_value -= dep
            records.append({"year": yr, "depreciation": dep, "book_value": book_value})

    elif method == "sum_of_years":
        syd = sum(range(1, useful_life_years + 1))
        book_value = initial_value
        for yr in years:
            fraction = (useful_life_years - yr + 1) / syd
            dep = (initial_value - salvage_value) * fraction
            book_value -= dep
            records.append({"year": yr, "depreciation": dep, "book_value": max(book_value, salvage_value)})

    return pd.DataFrame(records)


# ─── Growth Rates ─────────────────────────────────────────────────────────────


def compute_period_growth_rates(
    df: pd.DataFrame,
    value_col: str,
    period_col: Optional[str] = None,
) -> pd.DataFrame:
    """
    Compute period-over-period growth rates for a sorted series.
    """
    result = df.copy()
    if period_col:
        result = result.sort_values(period_col)
    result[f"{value_col}_pct_change"] = result[value_col].pct_change() * 100
    result[f"{value_col}_rolling_avg"] = result[value_col].rolling(window=3, min_periods=1).mean()
    return result


# ─── Forecasting ──────────────────────────────────────────────────────────────


def simple_forecast(
    series: pd.Series,
    periods: int = 6,
) -> pd.Series:
    """
    Generate a simple linear-regression forecast for *periods* future steps.
    """
    y = series.dropna().values
    if len(y) < 3:
        return pd.Series(dtype=float)

    x = np.arange(len(y))
    slope, intercept, *_ = scipy_stats.linregress(x, y)
    future_x = np.arange(len(y), len(y) + periods)
    forecast = slope * future_x + intercept
    return pd.Series(forecast, name="forecast")


# ─── Correlation Matrix ───────────────────────────────────────────────────────


def correlation_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Return the Pearson correlation matrix for numeric columns."""
    return df.select_dtypes(include="number").corr()


# ─── Compound Summary ─────────────────────────────────────────────────────────


def build_analytics_summary(
    df: pd.DataFrame,
    schema: Dict,
    prev_df: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """
    Run all analytics and return a comprehensive summary dict.
    """
    date_col = schema.get("date_column")
    revenue_col = schema.get("revenue_column")
    expense_col = schema.get("expense_column")
    profit_col = schema.get("profit_column")

    summary: Dict[str, Any] = {}

    # KPIs
    summary["kpis"] = calculate_kpis(
        df, revenue_col, expense_col, profit_col, date_col, prev_df
    )

    # P&L
    if date_col and (revenue_col or expense_col):
        summary["pl_data"] = compute_pl_analysis(df, date_col, revenue_col, expense_col)
    else:
        summary["pl_data"] = pd.DataFrame()

    # Anomalies
    if revenue_col and revenue_col in df.columns:
        summary["anomalies"] = detect_anomalies(df, revenue_col)
    else:
        summary["anomalies"] = pd.DataFrame()

    # Trend
    if revenue_col and revenue_col in df.columns:
        summary["revenue_trend"] = compute_trend(df[revenue_col])
    else:
        summary["revenue_trend"] = {}

    # Correlation
    summary["correlation"] = correlation_matrix(df)

    # YoY
    if prev_df is not None and date_col:
        metrics = [c for c in [revenue_col, expense_col] if c]
        if metrics:
            summary["yoy"] = yoy_comparison(df, prev_df, date_col, metrics)
        else:
            summary["yoy"] = pd.DataFrame()
    else:
        summary["yoy"] = pd.DataFrame()

    return summary
