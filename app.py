"""
BizInsight Pro – Intelligent Business Analytics Platform
Main Streamlit application entry point.
"""

import os
from typing import Dict, Optional

import pandas as pd
import streamlit as st

# ── Must be the very first Streamlit call ─────────────────────────────────────
from ui_components import set_page_config

set_page_config()

# ── Other imports (after set_page_config) ─────────────────────────────────────
from ai_insights import (
    generate_comparative_analysis,
    generate_custom_query,
    generate_executive_summary,
    generate_forecast_insights,
    generate_recommendations,
    generate_trend_analysis,
    generate_anomaly_explanation,
    get_gemini_client,
    run_all_analyses,
)
from analytics import (
    build_analytics_summary,
    compute_depreciation,
    compute_period_growth_rates,
    simple_forecast,
)
from config import PAGES
from data_processor import (
    filter_by_category,
    filter_by_date,
    load_uploaded_file,
    preprocess,
)
from report_generator import (
    dataframe_to_csv,
    generate_excel_report,
    generate_pdf_report,
)
from ui_components import (
    ai_insight_card,
    anomaly_table,
    comparison_metric,
    data_preview,
    empty_state,
    info_card,
    inject_css,
    kpi_row,
    render_header,
    render_navigation,
    schema_info,
    section_header,
    sidebar_ai_settings,
    sidebar_column_mapping,
    sidebar_filters,
    sidebar_upload_section,
)
from utils import format_currency, format_percentage
from visualizations import (
    anomaly_chart,
    area_trend_chart,
    bar_chart,
    correlation_heatmap,
    depreciation_chart,
    forecast_chart,
    line_chart,
    pie_chart,
    pl_chart,
    scatter_chart,
    yoy_comparison_chart,
)

# ─── CSS ─────────────────────────────────────────────────────────────────────
inject_css()


# ─── Session State Init ───────────────────────────────────────────────────────

def _init_session() -> None:
    defaults = {
        "current_df": None,
        "previous_df": None,
        "current_schema": None,
        "previous_schema": None,
        "current_filename": "",
        "previous_filename": "",
        "ai_cache": {},
        "col_mapping": {},
        "analytics": None,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


_init_session()


# ─── Sidebar ─────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        f"""<div style='text-align:center; padding:1rem 0 0.5rem;'>
        <div style='font-size:2rem;'>📊</div>
        <div style='font-size:1.1rem; font-weight:800; color:#FFFFFF;'>BizInsight Pro</div>
        <div style='font-size:0.72rem; color:#A0A0C0;'>Business Analytics Platform</div>
        </div>""",
        unsafe_allow_html=True,
    )
    st.markdown("---")

    current_file, previous_file = sidebar_upload_section()

    # Load current file
    if current_file is not None:
        if current_file.name != st.session_state.get("current_filename"):
            with st.spinner("Processing dataset…"):
                df, err = load_uploaded_file(current_file)
                if err:
                    st.error(err)
                else:
                    df, schema = preprocess(df)
                    st.session_state.current_df = df
                    st.session_state.current_schema = schema
                    st.session_state.current_filename = current_file.name
                    st.session_state.analytics = None
                    st.session_state.ai_cache = {}
                    st.success(f"✅ Loaded: {current_file.name}")

    # Load previous file
    if previous_file is not None:
        if previous_file.name != st.session_state.get("previous_filename"):
            with st.spinner("Processing comparison dataset…"):
                prev_df, err = load_uploaded_file(previous_file)
                if err:
                    st.error(err)
                else:
                    prev_df, prev_schema = preprocess(prev_df)
                    st.session_state.previous_df = prev_df
                    st.session_state.previous_schema = prev_schema
                    st.session_state.previous_filename = previous_file.name
                    st.session_state.analytics = None
                    st.success(f"✅ Loaded: {previous_file.name}")

    # Column mapping (only when data is loaded)
    if st.session_state.current_df is not None:
        mapping = sidebar_column_mapping(
            st.session_state.current_df,
            st.session_state.current_schema,
        )
        if mapping != st.session_state.col_mapping:
            st.session_state.col_mapping = mapping
            st.session_state.analytics = None

    # Filters
    active_filters: Dict = {}
    if st.session_state.current_df is not None:
        date_col = st.session_state.col_mapping.get(
            "date_column", st.session_state.current_schema.get("date_column")
        )
        active_filters = sidebar_filters(st.session_state.current_df, date_col)

    # AI settings
    api_key, enable_ai = sidebar_ai_settings()

    st.sidebar.markdown("---")
    st.sidebar.markdown(
        '<p style="font-size:0.72rem; color:#555577; text-align:center;">© 2025 BizInsight Pro</p>',
        unsafe_allow_html=True,
    )


# ─── Resolve active dataframe with filters ───────────────────────────────────

def _get_filtered_df() -> Optional[pd.DataFrame]:
    df = st.session_state.current_df
    if df is None:
        return None

    schema = st.session_state.current_schema or {}
    mapping = st.session_state.col_mapping

    date_col = mapping.get("date_column", schema.get("date_column"))

    # Apply date filter
    if "date_range" in active_filters and date_col and date_col in df.columns:
        start, end = active_filters["date_range"]
        df = filter_by_date(df, date_col, start, end)

    # Apply category filters
    for col, vals in active_filters.items():
        if col != "date_range" and col in df.columns:
            df = filter_by_category(df, col, vals)

    return df


# ─── Build analytics (cached in session state) ───────────────────────────────

def _ensure_analytics(df: pd.DataFrame) -> Dict:
    if st.session_state.analytics is None:
        schema = st.session_state.current_schema or {}
        mapping = st.session_state.col_mapping
        merged_schema = {**schema, **mapping}
        st.session_state.analytics = build_analytics_summary(
            df, merged_schema, st.session_state.previous_df
        )
    return st.session_state.analytics


# ─── Gemini client ───────────────────────────────────────────────────────────

def _get_model():
    if enable_ai and api_key:
        return get_gemini_client(api_key)
    return None


# ─── Main content area ────────────────────────────────────────────────────────

render_header()

if st.session_state.current_df is None:
    # Landing / empty state
    empty_state(
        "Welcome to BizInsight Pro",
        "Upload a CSV, Excel, or JSON dataset using the left sidebar to begin.",
        "📊",
    )

    # Feature highlights
    st.markdown("<br>", unsafe_allow_html=True)
    cols = st.columns(3)
    features = [
        ("📈", "Advanced Analytics", "Revenue, P&L, depreciation trends, anomaly detection, and YoY comparisons."),
        ("🤖", "AI-Powered Insights", "Google Gemini generates executive summaries, trend explanations, and strategic recommendations."),
        ("📑", "Professional Reports", "Export polished PDF and Excel reports with a single click."),
    ]
    for col, (icon, title, desc) in zip(cols, features):
        with col:
            st.markdown(f"""
            <div class="insight-card" style="text-align:center; padding:1.8rem;">
                <div style="font-size:2.5rem; margin-bottom:0.8rem;">{icon}</div>
                <div style="font-weight:700; font-size:1.05rem; color:#FFFFFF; margin-bottom:0.5rem;">{title}</div>
                <div style="font-size:0.85rem; color:#A0A0C0; line-height:1.5;">{desc}</div>
            </div>
            """, unsafe_allow_html=True)

else:
    # Data is loaded – show navigation
    selected_page = render_navigation()

    df = _get_filtered_df()
    analytics = _ensure_analytics(df)
    kpis = analytics.get("kpis", {})
    schema = st.session_state.current_schema or {}
    mapping = st.session_state.col_mapping
    merged_schema = {**schema, **mapping}

    date_col = merged_schema.get("date_column")
    revenue_col = merged_schema.get("revenue_column")
    expense_col = merged_schema.get("expense_column")
    profit_col = merged_schema.get("profit_column")

    # ── PAGE: Overview ────────────────────────────────────────────────────────
    if selected_page == PAGES[0]:  # 🏠 Overview
        render_header("Overview")

        # Dataset badge
        st.markdown(
            f'<span class="badge badge-info">📂 {st.session_state.current_filename}</span>'
            + (f' <span class="badge badge-neutral">⬅️ vs {st.session_state.previous_filename}</span>'
               if st.session_state.previous_df is not None else ""),
            unsafe_allow_html=True,
        )
        st.markdown("<br>", unsafe_allow_html=True)

        # KPIs
        section_header("📊 Key Performance Indicators")
        kpi_row(kpis)

        # Extra KPIs row
        extra_cols = st.columns(3)
        with extra_cols[0]:
            st.metric("📦 Records", f"{kpis.get('record_count', 0):,}")
        with extra_cols[1]:
            margin = kpis.get("profit_margin")
            st.metric("🎯 Profit Margin", format_percentage(margin) if margin else "—")
        with extra_cols[2]:
            exp_ratio = kpis.get("expense_ratio")
            st.metric("💼 Expense Ratio", format_percentage(exp_ratio) if exp_ratio else "—")

        st.markdown("<br>", unsafe_allow_html=True)

        # P&L Chart
        pl_df = analytics.get("pl_data", pd.DataFrame())
        if not pl_df.empty:
            section_header("📉 Profit & Loss Overview")
            st.plotly_chart(pl_chart(pl_df), use_container_width=True)

        # Data Preview
        data_preview(df, title=f"Data Preview — {st.session_state.current_filename}")
        schema_info(merged_schema)

    # ── PAGE: Analytics ───────────────────────────────────────────────────────
    elif selected_page == PAGES[1]:  # 📈 Analytics
        render_header("Analytics")

        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📊 P&L Analysis",
            "📈 Trends",
            "⚠️ Anomalies",
            "📅 Year-over-Year",
            "🏚️ Depreciation",
        ])

        with tab1:
            section_header("Profit & Loss Analysis")
            pl_df = analytics.get("pl_data", pd.DataFrame())
            if not pl_df.empty:
                freq = st.selectbox("Aggregation", ["ME", "QE", "YE", "W"], index=0,
                                    format_func=lambda x: {"ME": "Monthly", "QE": "Quarterly", "YE": "Yearly", "W": "Weekly"}[x])
                if date_col and (revenue_col or expense_col):
                    from data_processor import resample_timeseries
                    from analytics import compute_pl_analysis
                    pl_df2 = compute_pl_analysis(df, date_col, revenue_col, expense_col, freq=freq)
                    st.plotly_chart(pl_chart(pl_df2), use_container_width=True)
                else:
                    st.plotly_chart(pl_chart(pl_df), use_container_width=True)
            else:
                info_card("Configure date and revenue/expense columns in the sidebar to see P&L analysis.", "warning")

            # Waterfall if we have revenue and expenses
            if revenue_col and expense_col and revenue_col in df.columns and expense_col in df.columns:
                from visualizations import waterfall_chart
                rev_total = float(df[revenue_col].sum())
                exp_total = float(df[expense_col].sum())
                profit = rev_total - exp_total
                st.plotly_chart(
                    waterfall_chart(
                        ["Revenue", "Expenses", "Net Profit"],
                        [rev_total, -exp_total, profit],
                        "P&L Bridge",
                    ),
                    use_container_width=True,
                )

        with tab2:
            section_header("Trend Analysis")
            numeric_cols = df.select_dtypes(include="number").columns.tolist()
            if not numeric_cols:
                info_card("No numeric columns found for trend analysis.", "warning")
            else:
                trend_cols = st.multiselect("Select metrics", numeric_cols,
                                            default=numeric_cols[:2] if len(numeric_cols) >= 2 else numeric_cols)
                if date_col and date_col in df.columns and trend_cols:
                    sorted_df = df.sort_values(date_col)
                    st.plotly_chart(
                        line_chart(sorted_df, date_col, trend_cols, "Metric Trends Over Time", add_trend=True),
                        use_container_width=True,
                    )
                    # Growth rates
                    if revenue_col and revenue_col in df.columns:
                        growth_df = compute_period_growth_rates(
                            df.sort_values(date_col), revenue_col, date_col
                        )
                        st.plotly_chart(
                            bar_chart(growth_df.dropna(), date_col, f"{revenue_col}_pct_change", "Period-over-Period Growth (%)"),
                            use_container_width=True,
                        )
                else:
                    if trend_cols:
                        st.plotly_chart(
                            area_trend_chart(df.reset_index(), "index", trend_cols, "Metric Overview"),
                            use_container_width=True,
                        )

        with tab3:
            section_header("Anomaly Detection")
            if revenue_col and revenue_col in df.columns:
                method = st.radio("Detection Method", ["IQR", "Z-Score"], horizontal=True)
                anomalies = analytics.get("anomalies", pd.DataFrame())
                if date_col and date_col in df.columns:
                    st.plotly_chart(
                        anomaly_chart(df.sort_values(date_col), date_col, revenue_col, anomalies),
                        use_container_width=True,
                    )
                anomaly_table(anomalies)
            else:
                info_card("Configure a revenue column in the sidebar to enable anomaly detection.", "warning")

        with tab4:
            section_header("Year-over-Year Comparison")
            prev_df = st.session_state.previous_df
            if prev_df is not None:
                yoy_df = analytics.get("yoy", pd.DataFrame())
                if not yoy_df.empty and revenue_col:
                    st.plotly_chart(
                        yoy_comparison_chart(yoy_df, revenue_col, "Revenue: YoY Comparison"),
                        use_container_width=True,
                    )
                    if expense_col:
                        st.plotly_chart(
                            yoy_comparison_chart(yoy_df, expense_col, "Expenses: YoY Comparison"),
                            use_container_width=True,
                        )
                # Side-by-side metrics
                section_header("Metric Comparison")
                m_cols = st.columns(3)
                prev_kpis_data = {
                    "Revenue": (kpis.get("total_revenue"), kpis.get("prev_total_revenue")),
                    "Expenses": (kpis.get("total_expenses"), kpis.get("prev_total_expenses")),
                    "Net Profit": (kpis.get("net_profit"), kpis.get("prev_net_profit")),
                }
                for col, (label, (curr, prev)) in zip(m_cols, prev_kpis_data.items()):
                    with col:
                        comparison_metric(label, curr, prev)
            else:
                info_card("Upload a previous period dataset via the sidebar to enable YoY comparison.", "info")

        with tab5:
            section_header("Depreciation Calculator")
            d_cols = st.columns(3)
            with d_cols[0]:
                asset_value = st.number_input("Asset Value ($)", min_value=0.0, value=100000.0, step=1000.0)
            with d_cols[1]:
                useful_life = st.number_input("Useful Life (Years)", min_value=1, max_value=50, value=10)
            with d_cols[2]:
                salvage = st.number_input("Salvage Value ($)", min_value=0.0, value=0.0, step=500.0)
            dep_method = st.selectbox("Method", ["straight_line", "declining_balance", "sum_of_years"],
                                      format_func=lambda x: x.replace("_", " ").title())
            dep_df = compute_depreciation(asset_value, useful_life, dep_method, salvage)
            st.plotly_chart(depreciation_chart(dep_df, f"{dep_method.replace('_', ' ').title()} Depreciation"), use_container_width=True)
            st.dataframe(dep_df.style.format({"depreciation": "${:,.2f}", "book_value": "${:,.2f}"}), use_container_width=True)

    # ── PAGE: AI Insights ─────────────────────────────────────────────────────
    elif selected_page == PAGES[2]:  # 🤖 AI Insights
        render_header("AI Insights")

        if not enable_ai or not api_key:
            info_card("Enable AI Insights and enter your Gemini API key in the sidebar.", "warning")
        else:
            model = _get_model()
            ai_tabs = st.tabs([
                "📋 Executive Summary",
                "📈 Trend Analysis",
                "⚠️ Anomalies",
                "💡 Recommendations",
                "🔮 Forecast",
                "📊 Comparison",
                "💬 Ask AI",
            ])

            anomalies = analytics.get("anomalies", pd.DataFrame())
            trend_info = analytics.get("revenue_trend", {})

            with ai_tabs[0]:
                section_header("Executive Summary")
                cache_key = "exec_summary"
                if cache_key not in st.session_state.ai_cache:
                    with st.spinner("Generating executive summary…"):
                        result = generate_executive_summary(model, df, kpis, merged_schema)
                        st.session_state.ai_cache[cache_key] = result
                ai_insight_card("Executive Summary", st.session_state.ai_cache[cache_key], "📋")

            with ai_tabs[1]:
                section_header("Trend Analysis")
                cache_key = "trend_analysis"
                if cache_key not in st.session_state.ai_cache:
                    with st.spinner("Analysing trends…"):
                        result = generate_trend_analysis(model, df, kpis, merged_schema, trend_info)
                        st.session_state.ai_cache[cache_key] = result
                ai_insight_card("Trend Analysis", st.session_state.ai_cache[cache_key], "📈")

            with ai_tabs[2]:
                section_header("Anomaly Explanation")
                cache_key = "anomaly_explanation"
                if cache_key not in st.session_state.ai_cache:
                    with st.spinner("Explaining anomalies…"):
                        result = generate_anomaly_explanation(model, df, anomalies, kpis, merged_schema)
                        st.session_state.ai_cache[cache_key] = result
                ai_insight_card("Anomaly Explanation", st.session_state.ai_cache[cache_key], "⚠️")

            with ai_tabs[3]:
                section_header("Strategic Recommendations")
                cache_key = "recommendations"
                if cache_key not in st.session_state.ai_cache:
                    with st.spinner("Generating recommendations…"):
                        result = generate_recommendations(model, df, kpis, merged_schema, trend_info)
                        st.session_state.ai_cache[cache_key] = result
                ai_insight_card("Recommendations", st.session_state.ai_cache[cache_key], "💡")

            with ai_tabs[4]:
                section_header("Revenue Forecast")
                if revenue_col and revenue_col in df.columns:
                    periods = st.slider("Forecast periods", 3, 24, 6)
                    historical = df[revenue_col].dropna()
                    forecast_series = simple_forecast(historical, periods)

                    st.plotly_chart(
                        forecast_chart(historical, forecast_series, f"Revenue Forecast ({periods} periods)"),
                        use_container_width=True,
                    )

                    cache_key = f"forecast_{periods}"
                    if cache_key not in st.session_state.ai_cache:
                        with st.spinner("Generating forecast insights…"):
                            result = generate_forecast_insights(model, df, kpis, merged_schema, forecast_series.tolist())
                            st.session_state.ai_cache[cache_key] = result
                    ai_insight_card("Forecast Insights", st.session_state.ai_cache[cache_key], "🔮")
                else:
                    info_card("Configure a revenue column to enable forecasting.", "warning")

            with ai_tabs[5]:
                section_header("Comparative Analysis")
                if st.session_state.previous_df is not None:
                    cache_key = "comparative"
                    if cache_key not in st.session_state.ai_cache:
                        with st.spinner("Comparing datasets…"):
                            result = generate_comparative_analysis(
                                model, df, st.session_state.previous_df, kpis, merged_schema
                            )
                            st.session_state.ai_cache[cache_key] = result
                    ai_insight_card("Comparative Analysis", st.session_state.ai_cache[cache_key], "📊")
                else:
                    info_card("Upload a previous period dataset to enable comparative analysis.", "info")

            with ai_tabs[6]:
                section_header("Ask AI")
                user_q = st.text_area(
                    "Ask a question about your data",
                    placeholder="e.g. What are the top 3 cost drivers? Which month had the highest profit?",
                    height=100,
                )
                if st.button("🤖 Get AI Answer") and user_q.strip():
                    with st.spinner("Thinking…"):
                        answer = generate_custom_query(model, df, kpis, merged_schema, user_q)
                    st.markdown("---")
                    ai_insight_card("AI Answer", answer, "💬")

    # ── PAGE: Visualizations ──────────────────────────────────────────────────
    elif selected_page == PAGES[3]:  # 📊 Visualizations
        render_header("Visualizations")

        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

        viz_tabs = st.tabs(["📈 Time Series", "📊 Distribution", "🔵 Scatter", "🍩 Composition", "🔥 Heatmap", "🔗 Correlation"])

        with viz_tabs[0]:
            section_header("Time Series Analysis")
            if date_col and date_col in df.columns and numeric_cols:
                y_cols = st.multiselect("Y-axis columns", numeric_cols, default=numeric_cols[:2])
                chart_type = st.radio("Chart type", ["Line", "Area"], horizontal=True)
                if y_cols:
                    sorted_df = df.sort_values(date_col)
                    if chart_type == "Area":
                        st.plotly_chart(area_trend_chart(sorted_df, date_col, y_cols, "Time Series"), use_container_width=True)
                    else:
                        st.plotly_chart(line_chart(sorted_df, date_col, y_cols, "Time Series", add_trend=True), use_container_width=True)
            else:
                info_card("Configure a date column and ensure numeric columns exist.", "warning")

        with viz_tabs[1]:
            section_header("Distribution Analysis")
            if numeric_cols:
                sel_col = st.selectbox("Select column", numeric_cols)
                if cat_cols:
                    group_col = st.selectbox("Group by (optional)", ["None"] + cat_cols)
                    g = group_col if group_col != "None" else None
                else:
                    g = None
                st.plotly_chart(
                    bar_chart(
                        df.groupby(g or df.index.name or df.columns[0])[sel_col].sum().reset_index() if g else df,
                        x_col=g or (df.columns[0] if g is None else sel_col),
                        y_col=sel_col if g else sel_col,
                        title=f"Distribution of {sel_col}",
                        color_col=g,
                    ),
                    use_container_width=True,
                )

        with viz_tabs[2]:
            section_header("Scatter Plot")
            if len(numeric_cols) >= 2:
                x_col = st.selectbox("X axis", numeric_cols, index=0)
                y_col = st.selectbox("Y axis", numeric_cols, index=min(1, len(numeric_cols) - 1))
                color_by = st.selectbox("Color by", ["None"] + cat_cols) if cat_cols else "None"
                c = color_by if color_by != "None" else None
                st.plotly_chart(scatter_chart(df, x_col, y_col, color_col=c, title=f"{x_col} vs {y_col}"), use_container_width=True)
            else:
                info_card("At least 2 numeric columns required for scatter plot.", "warning")

        with viz_tabs[3]:
            section_header("Composition")
            if cat_cols and numeric_cols:
                names = st.selectbox("Category column", cat_cols)
                values = st.selectbox("Value column", numeric_cols)
                pie_data = df.groupby(names)[values].sum().reset_index()
                donut = st.checkbox("Donut style", value=True)
                st.plotly_chart(pie_chart(pie_data, names, values, f"{values} by {names}", donut=donut), use_container_width=True)
            else:
                info_card("Requires at least one categorical and one numeric column.", "warning")

        with viz_tabs[4]:
            section_header("Heatmap")
            if date_col and date_col in df.columns and numeric_cols:
                heat_col = st.selectbox("Value column", numeric_cols)
                from data_processor import pivot_year_month
                pivot = pivot_year_month(df, date_col, heat_col)
                if not pivot.empty:
                    st.plotly_chart(
                        heatmap_chart(pivot, f"{heat_col} Heatmap (Year × Month)"),
                        use_container_width=True,
                    )
                else:
                    info_card("Not enough date range to build year × month heatmap.", "warning")
            else:
                info_card("Configure a date column to enable heatmap.", "warning")

        with viz_tabs[5]:
            section_header("Correlation Matrix")
            if len(numeric_cols) >= 2:
                corr = analytics.get("correlation", pd.DataFrame())
                if not corr.empty:
                    st.plotly_chart(correlation_heatmap(corr, "Feature Correlation Matrix"), use_container_width=True)
            else:
                info_card("At least 2 numeric columns required.", "warning")

    # ── PAGE: Reports ─────────────────────────────────────────────────────────
    elif selected_page == PAGES[4]:  # 📑 Reports
        render_header("Reports & Export")

        section_header("📥 Download Options")

        report_cols = st.columns(3)

        pl_df = analytics.get("pl_data", pd.DataFrame())
        yoy_df = analytics.get("yoy", pd.DataFrame())

        with report_cols[0]:
            st.markdown("### 📄 PDF Report")
            company_name = st.text_input("Company / Report name", value="Business Analytics Report")
            if st.button("Generate PDF Report"):
                ai_cache = st.session_state.ai_cache if enable_ai else None
                with st.spinner("Generating PDF…"):
                    pdf_bytes = generate_pdf_report(kpis, df, ai_cache, company_name)
                if pdf_bytes:
                    st.download_button(
                        "⬇️ Download PDF",
                        data=pdf_bytes,
                        file_name=f"bizinsight_report_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.pdf",
                        mime="application/pdf",
                    )
                else:
                    info_card("PDF generation requires the `reportlab` package. Install it with: `pip install reportlab`", "warning")

        with report_cols[1]:
            st.markdown("### 📊 Excel Export")
            if st.button("Generate Excel Report"):
                with st.spinner("Generating Excel workbook…"):
                    excel_bytes = generate_excel_report(df, kpis, pl_df, yoy_df, company_name if 'company_name' in dir() else "Report")
                if excel_bytes:
                    st.download_button(
                        "⬇️ Download Excel",
                        data=excel_bytes,
                        file_name=f"bizinsight_report_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                else:
                    info_card("Excel generation requires the `openpyxl` package. Install it with: `pip install openpyxl`", "warning")

        with report_cols[2]:
            st.markdown("### 📋 CSV Export")
            if st.button("Download Raw Data (CSV)"):
                csv_bytes = dataframe_to_csv(df)
                st.download_button(
                    "⬇️ Download CSV",
                    data=csv_bytes,
                    file_name=f"data_export_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv",
                )

        # Statistics Preview
        st.markdown("<br>", unsafe_allow_html=True)
        section_header("📊 Summary Statistics")
        from utils import compute_summary_stats
        stats_df = compute_summary_stats(df)
        if not stats_df.empty:
            st.dataframe(stats_df, use_container_width=True)
        else:
            info_card("No numeric columns found for statistics.", "warning")
