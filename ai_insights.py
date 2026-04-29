"""
Gemini API integration and AI-powered analysis for the Business Analytics Platform.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st

from config import GEMINI_MAX_TOKENS, GEMINI_MODEL, GEMINI_TEMPERATURE
from utils import truncate_text, logger

# ─── Lazy import so app loads even if google-generativeai isn't installed ─────

try:
    from google import genai  # type: ignore
    from google.genai import types as genai_types  # type: ignore

    _GENAI_AVAILABLE = True
except ImportError:
    _GENAI_AVAILABLE = False
    logger.warning("google-genai not installed – AI features disabled.")


# ─── Client Initialisation ───────────────────────────────────────────────────


@st.cache_resource(show_spinner=False)
def get_gemini_client(api_key: str):
    """Return a configured Gemini client (cached per API key)."""
    if not _GENAI_AVAILABLE:
        return None
    try:
        client = genai.Client(api_key=api_key)
        return client
    except Exception as exc:
        logger.error("Failed to initialise Gemini: %s", exc)
        return None


# ─── Low-level prompt helper ─────────────────────────────────────────────────


def _call_gemini(client, prompt: str) -> str:
    """Send a prompt to Gemini and return the text response."""
    if client is None:
        return "⚠️ AI features are unavailable. Please check your Gemini API key."
    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                max_output_tokens=GEMINI_MAX_TOKENS,
                temperature=GEMINI_TEMPERATURE,
            ),
        )
        return response.text.strip()
    except Exception as exc:
        logger.error("Gemini API error: %s", exc)
        return f"⚠️ AI analysis failed: {exc}"


# ─── Data Summary Builder ─────────────────────────────────────────────────────


def _build_data_context(
    df: pd.DataFrame,
    kpis: Dict[str, Any],
    schema: Dict,
    max_rows: int = 5,
) -> str:
    """Build a concise textual context string from a DataFrame and KPIs."""
    lines = []

    # Shape
    lines.append(f"Dataset: {len(df)} rows × {len(df.columns)} columns")
    lines.append(f"Columns: {', '.join(df.columns.tolist()[:20])}")

    # KPI summary
    kpi_parts = []
    if kpis.get("total_revenue") is not None:
        kpi_parts.append(f"Total Revenue: ${kpis['total_revenue']:,.0f}")
    if kpis.get("total_expenses") is not None:
        kpi_parts.append(f"Total Expenses: ${kpis['total_expenses']:,.0f}")
    if kpis.get("net_profit") is not None:
        kpi_parts.append(f"Net Profit: ${kpis['net_profit']:,.0f}")
    if kpis.get("profit_margin") is not None:
        kpi_parts.append(f"Profit Margin: {kpis['profit_margin']:.1f}%")
    if kpis.get("revenue_growth") is not None:
        kpi_parts.append(f"Revenue Growth: {kpis['revenue_growth']:+.1f}%")
    if kpi_parts:
        lines.append("Key Metrics: " + " | ".join(kpi_parts))

    # Schema info
    if schema.get("date_column"):
        lines.append(f"Date Column: {schema['date_column']}")

    # Numeric stats (truncated)
    numeric_df = df.select_dtypes(include="number")
    if not numeric_df.empty:
        stats = numeric_df.describe().round(2).to_string()
        lines.append("Numeric Statistics:\n" + truncate_text(stats, 800))

    # Sample rows
    sample = df.head(max_rows).to_string(index=False)
    lines.append("Sample Data:\n" + truncate_text(sample, 600))

    return "\n".join(lines)


# ─── Individual AI Analysis Functions ────────────────────────────────────────


def generate_executive_summary(
    client,
    df: pd.DataFrame,
    kpis: Dict[str, Any],
    schema: Dict,
) -> str:
    """Generate a concise executive summary of the business data."""
    context = _build_data_context(df, kpis, schema)
    prompt = f"""You are a senior business analyst. Based on the following business data, 
write a concise executive summary (3-5 paragraphs) suitable for C-suite leadership.
Focus on overall business performance, key highlights, and strategic implications.
Use clear, professional language. Include specific numbers where relevant.

{context}

Provide the executive summary:"""
    return _call_gemini(client, prompt)


def generate_trend_analysis(
    client,
    df: pd.DataFrame,
    kpis: Dict[str, Any],
    schema: Dict,
    trend_info: Optional[Dict] = None,
) -> str:
    """Generate AI-powered trend analysis."""
    context = _build_data_context(df, kpis, schema)
    trend_str = ""
    if trend_info:
        trend_str = (
            f"\nTrend Analysis: Direction={trend_info.get('direction', 'N/A')}, "
            f"Strength={trend_info.get('strength', 'N/A')}, "
            f"R²={trend_info.get('r_squared', 'N/A')}"
        )

    prompt = f"""You are a business data analyst specializing in trend identification.
Analyze the following business data and provide:
1. Key trends observed (with specific metrics)
2. Trend direction and strength assessment
3. Seasonal patterns if visible
4. Momentum analysis (accelerating/decelerating growth)
5. Forward-looking implications

{context}{trend_str}

Provide detailed trend analysis:"""
    return _call_gemini(client, prompt)


def generate_anomaly_explanation(
    client,
    df: pd.DataFrame,
    anomalies_df: pd.DataFrame,
    kpis: Dict[str, Any],
    schema: Dict,
) -> str:
    """Generate natural-language explanations for detected anomalies."""
    if anomalies_df.empty:
        return "✅ No significant anomalies detected in the dataset."

    context = _build_data_context(df, kpis, schema)
    anomaly_info = anomalies_df.head(10).to_string(index=False)

    prompt = f"""You are a data scientist specializing in anomaly detection for business data.
The following anomalous data points were detected in the dataset.
For each anomaly:
1. Describe what makes it unusual
2. Suggest possible business causes
3. Assess the potential business impact (High/Medium/Low)
4. Recommend investigation steps

Dataset Context:
{context}

Detected Anomalies:
{truncate_text(anomaly_info, 500)}

Provide anomaly explanations and recommendations:"""
    return _call_gemini(client, prompt)


def generate_recommendations(
    client,
    df: pd.DataFrame,
    kpis: Dict[str, Any],
    schema: Dict,
    trend_info: Optional[Dict] = None,
) -> str:
    """Generate strategic business recommendations."""
    context = _build_data_context(df, kpis, schema)

    prompt = f"""You are a strategic business consultant with expertise in financial analytics.
Based on the business data provided, generate actionable strategic recommendations.

Structure your response as:
## 🎯 Immediate Actions (0-3 months)
[3-4 specific, actionable items]

## 📈 Short-term Strategy (3-12 months)
[3-4 strategic initiatives]

## 🔭 Long-term Opportunities (1-3 years)
[2-3 growth opportunities]

## ⚠️ Risk Mitigation
[Key risks and mitigation strategies]

Be specific, use data from the context, and prioritize recommendations by impact.

{context}

Provide strategic recommendations:"""
    return _call_gemini(client, prompt)


def generate_forecast_insights(
    client,
    df: pd.DataFrame,
    kpis: Dict[str, Any],
    schema: Dict,
    forecast_values: Optional[List[float]] = None,
) -> str:
    """Generate AI insights about the business forecast."""
    context = _build_data_context(df, kpis, schema)
    forecast_str = ""
    if forecast_values:
        forecast_str = f"\nForecasted values (next {len(forecast_values)} periods): {[round(v, 2) for v in forecast_values]}"

    prompt = f"""You are a financial forecasting expert.
Based on the historical business data and forecast below, provide:
1. Forecast accuracy assessment
2. Key assumptions and risks
3. Best-case and worst-case scenarios
4. Recommended monitoring KPIs
5. Trigger points that would indicate a need to revise the forecast

{context}{forecast_str}

Provide forecasting insights:"""
    return _call_gemini(client, prompt)


def generate_comparative_analysis(
    client,
    current_df: pd.DataFrame,
    previous_df: pd.DataFrame,
    current_kpis: Dict[str, Any],
    schema: Dict,
) -> str:
    """Generate comparative analysis between two datasets."""
    current_context = _build_data_context(current_df, current_kpis, schema)

    prev_kpis = {
        "total_revenue": current_kpis.get("prev_total_revenue"),
        "total_expenses": current_kpis.get("prev_total_expenses"),
        "net_profit": current_kpis.get("prev_net_profit"),
    }
    prev_context = _build_data_context(previous_df, prev_kpis, schema)

    prompt = f"""You are a business performance analyst.
Compare the two periods below and provide:
1. Performance summary (what improved, what declined)
2. Key drivers of change (positive and negative)
3. Variance analysis for major metrics
4. Business health score comparison (1-10)
5. Areas of concern and areas of excellence

CURRENT PERIOD:
{truncate_text(current_context, 700)}

PREVIOUS PERIOD:
{truncate_text(prev_context, 700)}

Provide comprehensive comparative analysis:"""
    return _call_gemini(client, prompt)


def generate_custom_query(
    client,
    df: pd.DataFrame,
    kpis: Dict[str, Any],
    schema: Dict,
    user_question: str,
) -> str:
    """Answer a custom user question about the business data."""
    context = _build_data_context(df, kpis, schema)

    prompt = f"""You are an expert business analyst. Answer the following question about the business data.
Be specific, cite numbers where available, and provide actionable insights.

Business Data Context:
{context}

User Question: {user_question}

Provide a detailed, data-driven answer:"""
    return _call_gemini(client, prompt)


# ─── Cached Analysis Runner ───────────────────────────────────────────────────


def run_all_analyses(
    client,
    df: pd.DataFrame,
    kpis: Dict[str, Any],
    schema: Dict,
    anomalies_df: Optional[pd.DataFrame] = None,
    trend_info: Optional[Dict] = None,
    prev_df: Optional[pd.DataFrame] = None,
) -> Dict[str, str]:
    """
    Run all AI analyses and return results in a dict.
    Results are displayed progressively via Streamlit status updates.
    """
    results: Dict[str, str] = {}

    results["executive_summary"] = generate_executive_summary(client, df, kpis, schema)
    results["trend_analysis"] = generate_trend_analysis(client, df, kpis, schema, trend_info)

    if anomalies_df is not None:
        results["anomaly_explanation"] = generate_anomaly_explanation(client, df, anomalies_df, kpis, schema)

    results["recommendations"] = generate_recommendations(client, df, kpis, schema, trend_info)

    if prev_df is not None:
        results["comparative_analysis"] = generate_comparative_analysis(client, df, prev_df, kpis, schema)

    return results
