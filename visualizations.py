"""
Chart generation and visualization logic for the Business Analytics Platform.
"""

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from config import CHART_COLORS, CHART_HEIGHT, PLOTLY_LAYOUT_DEFAULTS
from utils import deep_merge


# ─── Layout Helper ────────────────────────────────────────────────────────────


def _apply_layout(fig: go.Figure, title: str = "", height: int = CHART_HEIGHT, extra: Optional[Dict] = None) -> go.Figure:
    """Apply the standard dark layout to a Plotly figure."""
    layout = deep_merge(PLOTLY_LAYOUT_DEFAULTS, {"title": {"text": title, "font": {"size": 16}}, "height": height})
    if extra:
        layout = deep_merge(layout, extra)
    fig.update_layout(**layout)
    return fig


# ─── KPI Indicator ────────────────────────────────────────────────────────────


def kpi_gauge(
    value: float,
    reference: Optional[float],
    title: str,
    prefix: str = "$",
    suffix: str = "",
    height: int = 200,
) -> go.Figure:
    """Create a compact Plotly indicator (number + delta)."""
    delta = {"reference": reference, "relative": True, "valueformat": ".1%"} if reference else None
    fig = go.Figure(
        go.Indicator(
            mode="number+delta" if delta else "number",
            value=value,
            delta=delta,
            number={"prefix": prefix, "suffix": suffix, "valueformat": ",.0f"},
            title={"text": title, "font": {"size": 14}},
        )
    )
    _apply_layout(fig, height=height, extra={"margin": {"t": 60, "b": 0, "l": 20, "r": 20}})
    return fig


# ─── P&L Chart ────────────────────────────────────────────────────────────────


def pl_chart(pl_df: pd.DataFrame, height: int = CHART_HEIGHT) -> go.Figure:
    """Grouped bar chart for P&L: Revenue, Expenses, Profit."""
    if pl_df.empty:
        return _empty_fig("No P&L data available")

    period_col = pl_df.columns[0]
    fig = go.Figure()

    if "revenue" in pl_df.columns:
        fig.add_trace(go.Bar(
            name="Revenue",
            x=pl_df[period_col],
            y=pl_df["revenue"],
            marker_color=CHART_COLORS[0],
            hovertemplate="Revenue: $%{y:,.0f}<extra></extra>",
        ))
    if "expenses" in pl_df.columns:
        fig.add_trace(go.Bar(
            name="Expenses",
            x=pl_df[period_col],
            y=pl_df["expenses"],
            marker_color=CHART_COLORS[2],
            hovertemplate="Expenses: $%{y:,.0f}<extra></extra>",
        ))
    if "profit" in pl_df.columns:
        fig.add_trace(go.Scatter(
            name="Net Profit",
            x=pl_df[period_col],
            y=pl_df["profit"],
            mode="lines+markers",
            line={"color": CHART_COLORS[1], "width": 3},
            marker={"size": 6},
            hovertemplate="Profit: $%{y:,.0f}<extra></extra>",
            yaxis="y2",
        ))

    _apply_layout(fig, "Revenue vs Expenses vs Profit", height, {
        "barmode": "group",
        "yaxis2": {
            "title": "Net Profit ($)",
            "overlaying": "y",
            "side": "right",
            "showgrid": False,
        },
    })
    return fig


# ─── Area Trend Chart ────────────────────────────────────────────────────────


def area_trend_chart(
    df: pd.DataFrame,
    x_col: str,
    y_cols: List[str],
    title: str = "Trend",
    height: int = CHART_HEIGHT,
) -> go.Figure:
    """Stacked area chart for multiple metrics over time."""
    if df.empty or not y_cols:
        return _empty_fig("No data available")

    fig = go.Figure()
    for i, col in enumerate(y_cols):
        if col not in df.columns:
            continue
        fig.add_trace(go.Scatter(
            name=col,
            x=df[x_col],
            y=df[col],
            mode="lines",
            fill="tonexty" if i > 0 else "tozeroy",
            line={"color": CHART_COLORS[i % len(CHART_COLORS)], "width": 2},
            hovertemplate=f"{col}: %{{y:,.0f}}<extra></extra>",
        ))
    _apply_layout(fig, title, height)
    return fig


# ─── Line Chart ───────────────────────────────────────────────────────────────


def line_chart(
    df: pd.DataFrame,
    x_col: str,
    y_cols: List[str],
    title: str = "",
    height: int = CHART_HEIGHT,
    add_trend: bool = False,
) -> go.Figure:
    """Multi-series line chart with optional linear trend lines."""
    if df.empty:
        return _empty_fig("No data available")

    fig = go.Figure()
    for i, col in enumerate(y_cols):
        if col not in df.columns:
            continue
        color = CHART_COLORS[i % len(CHART_COLORS)]
        fig.add_trace(go.Scatter(
            name=col,
            x=df[x_col],
            y=df[col],
            mode="lines+markers",
            line={"color": color, "width": 2},
            marker={"size": 5},
            hovertemplate=f"{col}: %{{y:,.2f}}<extra></extra>",
        ))
        if add_trend:
            y_vals = df[col].dropna().values
            if len(y_vals) >= 2:
                x_vals = np.arange(len(y_vals))
                slope, intercept = np.polyfit(x_vals, y_vals, 1)
                trend = slope * x_vals + intercept
                fig.add_trace(go.Scatter(
                    name=f"{col} trend",
                    x=df[x_col].iloc[:len(y_vals)],
                    y=trend,
                    mode="lines",
                    line={"color": color, "width": 1, "dash": "dash"},
                    showlegend=False,
                ))
    _apply_layout(fig, title, height)
    return fig


# ─── Bar Chart ────────────────────────────────────────────────────────────────


def bar_chart(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: str = "",
    color_col: Optional[str] = None,
    orientation: str = "v",
    height: int = CHART_HEIGHT,
) -> go.Figure:
    """Simple bar chart."""
    if df.empty:
        return _empty_fig("No data available")

    fig = px.bar(
        df, x=x_col if orientation == "v" else y_col,
        y=y_col if orientation == "v" else x_col,
        color=color_col,
        color_discrete_sequence=CHART_COLORS,
        orientation=orientation,
        title=title,
    )
    _apply_layout(fig, title, height)
    return fig


# ─── Pie / Donut Chart ────────────────────────────────────────────────────────


def pie_chart(
    df: pd.DataFrame,
    names_col: str,
    values_col: str,
    title: str = "",
    donut: bool = True,
    height: int = CHART_HEIGHT,
) -> go.Figure:
    """Pie or donut chart."""
    if df.empty:
        return _empty_fig("No data available")

    fig = go.Figure(go.Pie(
        labels=df[names_col],
        values=df[values_col],
        hole=0.5 if donut else 0,
        marker={"colors": CHART_COLORS},
        hovertemplate="%{label}: %{value:,.0f} (%{percent})<extra></extra>",
    ))
    _apply_layout(fig, title, height, {"showlegend": True})
    return fig


# ─── Scatter Chart ────────────────────────────────────────────────────────────


def scatter_chart(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    color_col: Optional[str] = None,
    size_col: Optional[str] = None,
    title: str = "",
    trendline: bool = True,
    height: int = CHART_HEIGHT,
) -> go.Figure:
    """Scatter plot with optional trend line."""
    if df.empty:
        return _empty_fig("No data available")

    fig = px.scatter(
        df, x=x_col, y=y_col,
        color=color_col,
        size=size_col,
        trendline="ols" if trendline else None,
        color_discrete_sequence=CHART_COLORS,
        title=title,
    )
    _apply_layout(fig, title, height)
    return fig


# ─── Heatmap ──────────────────────────────────────────────────────────────────


def heatmap_chart(
    pivot_df: pd.DataFrame,
    title: str = "Heatmap",
    height: int = CHART_HEIGHT,
    color_scale: str = "Viridis",
) -> go.Figure:
    """Heatmap from a pivot DataFrame."""
    if pivot_df.empty:
        return _empty_fig("No data available")

    fig = go.Figure(go.Heatmap(
        z=pivot_df.values,
        x=list(pivot_df.columns),
        y=[str(i) for i in pivot_df.index],
        colorscale=color_scale,
        hovertemplate="%{y} — %{x}: %{z:,.0f}<extra></extra>",
    ))
    _apply_layout(fig, title, height)
    return fig


# ─── Waterfall ────────────────────────────────────────────────────────────────


def waterfall_chart(
    categories: List[str],
    values: List[float],
    title: str = "Waterfall",
    height: int = CHART_HEIGHT,
) -> go.Figure:
    """Waterfall chart for P&L or bridge analysis."""
    measures = ["relative"] * (len(categories) - 1) + ["total"]
    fig = go.Figure(go.Waterfall(
        name="",
        orientation="v",
        measure=measures,
        x=categories,
        y=values,
        connector={"line": {"color": CHART_COLORS[4]}},
        increasing={"marker": {"color": CHART_COLORS[3]}},
        decreasing={"marker": {"color": CHART_COLORS[2]}},
        totals={"marker": {"color": CHART_COLORS[0]}},
        hovertemplate="%{x}: %{y:,.0f}<extra></extra>",
    ))
    _apply_layout(fig, title, height)
    return fig


# ─── YoY Comparison ───────────────────────────────────────────────────────────


def yoy_comparison_chart(
    yoy_df: pd.DataFrame,
    metric: str,
    title: str = "Year-over-Year Comparison",
    height: int = CHART_HEIGHT,
) -> go.Figure:
    """Side-by-side bar chart for YoY comparison."""
    if yoy_df.empty:
        return _empty_fig("No comparison data available")

    period_col = yoy_df.columns[0]
    fig = go.Figure()

    if f"{metric}_previous" in yoy_df.columns:
        fig.add_trace(go.Bar(
            name="Previous Period",
            x=yoy_df[period_col],
            y=yoy_df[f"{metric}_previous"],
            marker_color=CHART_COLORS[4],
            hovertemplate="Previous: %{y:,.0f}<extra></extra>",
        ))
    if f"{metric}_current" in yoy_df.columns:
        fig.add_trace(go.Bar(
            name="Current Period",
            x=yoy_df[period_col],
            y=yoy_df[f"{metric}_current"],
            marker_color=CHART_COLORS[0],
            hovertemplate="Current: %{y:,.0f}<extra></extra>",
        ))

    _apply_layout(fig, title, height, {"barmode": "group"})
    return fig


# ─── Depreciation Chart ───────────────────────────────────────────────────────


def depreciation_chart(
    dep_df: pd.DataFrame,
    title: str = "Depreciation Schedule",
    height: int = CHART_HEIGHT,
) -> go.Figure:
    """Combo chart for depreciation schedule."""
    if dep_df.empty:
        return _empty_fig("No depreciation data")

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(
            name="Annual Depreciation",
            x=dep_df["year"],
            y=dep_df["depreciation"],
            marker_color=CHART_COLORS[2],
            hovertemplate="Depreciation: $%{y:,.0f}<extra></extra>",
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            name="Book Value",
            x=dep_df["year"],
            y=dep_df["book_value"],
            mode="lines+markers",
            line={"color": CHART_COLORS[1], "width": 3},
            marker={"size": 7},
            hovertemplate="Book Value: $%{y:,.0f}<extra></extra>",
        ),
        secondary_y=True,
    )
    _apply_layout(fig, title, height)
    return fig


# ─── Correlation Heatmap ──────────────────────────────────────────────────────


def correlation_heatmap(
    corr_df: pd.DataFrame,
    title: str = "Correlation Matrix",
    height: int = CHART_HEIGHT,
) -> go.Figure:
    """Annotated correlation heatmap."""
    if corr_df.empty:
        return _empty_fig("No data for correlation")

    fig = go.Figure(go.Heatmap(
        z=corr_df.values,
        x=corr_df.columns.tolist(),
        y=corr_df.index.tolist(),
        colorscale="RdBu",
        zmid=0,
        zmin=-1,
        zmax=1,
        text=[[f"{v:.2f}" for v in row] for row in corr_df.values],
        texttemplate="%{text}",
        hovertemplate="%{y} × %{x}: %{z:.3f}<extra></extra>",
    ))
    _apply_layout(fig, title, height)
    return fig


# ─── Anomaly Chart ────────────────────────────────────────────────────────────


def anomaly_chart(
    df: pd.DataFrame,
    x_col: str,
    value_col: str,
    anomalies_df: pd.DataFrame,
    title: str = "Anomaly Detection",
    height: int = CHART_HEIGHT,
) -> go.Figure:
    """Line chart highlighting anomalous data points."""
    if df.empty:
        return _empty_fig("No data available")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        name="Values",
        x=df[x_col],
        y=df[value_col],
        mode="lines+markers",
        line={"color": CHART_COLORS[0], "width": 2},
        marker={"size": 4},
    ))
    if not anomalies_df.empty and x_col in anomalies_df.columns:
        fig.add_trace(go.Scatter(
            name="Anomaly",
            x=anomalies_df[x_col],
            y=anomalies_df[value_col],
            mode="markers",
            marker={"color": CHART_COLORS[2], "size": 12, "symbol": "x"},
        ))
    _apply_layout(fig, title, height)
    return fig


# ─── Forecast Chart ───────────────────────────────────────────────────────────


def forecast_chart(
    historical: pd.Series,
    forecast: pd.Series,
    title: str = "Forecast",
    height: int = CHART_HEIGHT,
) -> go.Figure:
    """Historical + forecast line chart."""
    fig = go.Figure()
    x_hist = list(range(len(historical)))
    x_fore = list(range(len(historical), len(historical) + len(forecast)))

    fig.add_trace(go.Scatter(
        name="Historical",
        x=x_hist,
        y=historical.values,
        mode="lines+markers",
        line={"color": CHART_COLORS[0], "width": 2},
    ))
    fig.add_trace(go.Scatter(
        name="Forecast",
        x=x_fore,
        y=forecast.values,
        mode="lines+markers",
        line={"color": CHART_COLORS[1], "width": 2, "dash": "dot"},
        marker={"symbol": "diamond"},
    ))
    # Shade forecast region
    fig.add_vrect(
        x0=len(historical) - 0.5,
        x1=len(historical) + len(forecast) - 0.5,
        fillcolor=CHART_COLORS[1],
        opacity=0.07,
        layer="below",
        line_width=0,
    )
    _apply_layout(fig, title, height)
    return fig


# ─── Helper ───────────────────────────────────────────────────────────────────


def _empty_fig(message: str = "No data") -> go.Figure:
    """Return an empty figure with a centered annotation."""
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        x=0.5, y=0.5,
        xref="paper", yref="paper",
        showarrow=False,
        font={"size": 14, "color": "#A0A0C0"},
    )
    _apply_layout(fig, height=300)
    return fig
