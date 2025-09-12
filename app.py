import os
from dotenv import load_dotenv
from supabase import create_client, Client
import importlib
AGGRID_AVAILABLE = False
AgGrid = None
GridOptionsBuilder = None
try:
    aggrid = importlib.import_module("st_aggrid")
    AgGrid = getattr(aggrid, "AgGrid", None)
    GridOptionsBuilder = getattr(aggrid, "GridOptionsBuilder", None)
    AGGRID_AVAILABLE = AgGrid is not None and GridOptionsBuilder is not None
except Exception:
    AGGRID_AVAILABLE = False
import streamlit as st
import altair as alt
import pandas as pd
from datetime import datetime, date, timedelta

# Load environment variables
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

@st.cache_resource
def init_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

supabase = init_supabase()

# Fetch data
res = supabase.table("walkin_table").select("*").execute()
df = pd.DataFrame(res.data)

# Page layout and CSS to left-align content and use full width
st.set_page_config(page_title="Analytics Dashboard", layout="wide")
st.markdown(
    """
    <style>
      .block-container { max-width: 100% !important; padding-top: 1rem; padding-bottom: 1rem; }
      h1 { font-size: 34px !important; margin-bottom: 0.5rem !important; }
      h2 { font-size: 26px !important; margin-bottom: 0.5rem !important; }
      h3 { font-size: 22px !important; margin-bottom: 0.25rem !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

# Consistent numeric font for all KPI numbers (native st.metric and custom cards)
st.markdown(
    """
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
      :root { --kpi-number-font: 'Inter', ui-sans-serif, system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Noto Sans', 'Apple Color Emoji', 'Segoe UI Emoji', 'Segoe UI Symbol', 'Noto Color Emoji'; }
      /* Streamlit metric value and delta */
      [data-testid="stMetricValue"], [data-testid="stMetricDelta"] {
        font-family: var(--kpi-number-font) !important;
        font-variant-numeric: tabular-nums lining-nums;
        font-feature-settings: "tnum" 1, "lnum" 1;
        -webkit-font-smoothing: antialiased;
      }
      /* Custom KPI cards */
      .won-metric-card .value-row .big,
      .won-metric-card .value-row .small,
      .won-metric-card .delta {
        font-family: var(--kpi-number-font) !important;
        font-variant-numeric: tabular-nums lining-nums;
        font-feature-settings: "tnum" 1, "lnum" 1;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

# Print working localhost link to terminal once per session
if "_printed_local_url" not in st.session_state:
    port = os.environ.get("PORT") or os.environ.get("STREAMLIT_SERVER_PORT") or "8501"
    host = os.environ.get("STREAMLIT_SERVER_ADDRESS", "localhost")
    print(f"Local URL: http://{host}:{port}")
    st.session_state["_printed_local_url"] = True

st.title("Analytics Dashboard")

# Global date filter (applies to KPIs and dashboards)
col_filter_global, col_empty_filter_global = st.columns([0.2, 0.8])
with col_filter_global:
    filter_option_global = st.selectbox(
        "Date filter (based on created_at)",
        ["MTD", "Today", "Custom Range", "All time"],
        index=0,
        key="global_filter"
    )

# Compute global start/end datetimes (UTC)
now_ts_global = pd.Timestamp.now(tz="UTC")
today_start_global = pd.Timestamp(date.today()).tz_localize("UTC")
today_end_global = today_start_global + pd.Timedelta(days=1) - pd.Timedelta(milliseconds=1)
month_start_global = pd.Timestamp(date.today().replace(day=1)).tz_localize("UTC")

if filter_option_global == "Today":
    start_dt_global, end_dt_global = today_start_global, today_end_global
elif filter_option_global == "MTD":
    start_dt_global, end_dt_global = month_start_global, now_ts_global
elif filter_option_global == "Custom Range":
    col_custom_global, col_empty_custom_global = st.columns([0.2, 0.8])
    with col_custom_global:
        col_start_global, col_end_global = st.columns(2)
        with col_start_global:
            custom_start_global = st.date_input("Start date", value=date.today().replace(day=1), key="global_start")
        with col_end_global:
            custom_end_global = st.date_input("End date", value=date.today(), key="global_end")
    start_dt_global = pd.Timestamp(custom_start_global).tz_localize("UTC")
    end_dt_global = pd.Timestamp(custom_end_global).tz_localize("UTC") + pd.Timedelta(days=1) - pd.Timedelta(milliseconds=1)
else:
    start_dt_global, end_dt_global = None, None

# Compute previous period for delta comparison
prev_start_global, prev_end_global = None, None
if filter_option_global == "MTD":
    prev_start_global = month_start_global - pd.offsets.MonthBegin(1)
    prev_end_global = month_start_global - pd.Timedelta(milliseconds=1)
elif filter_option_global == "Today":
    prev_start_global = today_start_global - pd.Timedelta(days=1)
    prev_end_global = today_end_global - pd.Timedelta(days=1)
elif filter_option_global == "Custom Range":
    if start_dt_global is not None and end_dt_global is not None:
        duration = end_dt_global - start_dt_global + pd.Timedelta(milliseconds=1)
        prev_end_global = start_dt_global - pd.Timedelta(milliseconds=1)
        prev_start_global = prev_end_global - duration + pd.Timedelta(milliseconds=1)

# KPI cards (top): All in one row
col_kpi_1, col_kpi_2, col_kpi_3, col_kpi_4, col_kpi_5, col_kpi_6, col_kpi_7, col_kpi_8 = st.columns(8)
with col_kpi_1:
    try:
        q = supabase.table("lead_master").select("id", count="exact")
        if filter_option_global != "All time" and start_dt_global is not None and end_dt_global is not None:
            q = q.gte("created_at", start_dt_global.isoformat()).lte("created_at", end_dt_global.isoformat())
        curr_resp = q.execute()
        curr_count = int(curr_resp.count or 0)

        if prev_start_global is not None and prev_end_global is not None:
            prev_q = (
                supabase
                .table("lead_master")
                .select("id", count="exact")
                .gte("created_at", prev_start_global.isoformat())
                .lte("created_at", prev_end_global.isoformat())
                .execute()
            )
            prev_count = int(prev_q.count or 0)
            if prev_count == 0:
                delta_str = "+∞%" if curr_count > 0 else "0%"
            else:
                pct_change = (curr_count - prev_count) / prev_count * 100.0
                delta_str = f"{pct_change:+.1f}%"
        else:
            delta_str = "—"

        st.metric(label="Leads", value=curr_count, delta=delta_str)
    except Exception as err:
        st.warning(f"Could not load KPI (Leads): {err}")

with col_kpi_2:
    try:
        q = (
            supabase
            .table("lead_master")
            .select("id", count="exact")
            .not_.is_("cre_name", "null")
        )
        if filter_option_global != "All time" and start_dt_global is not None and end_dt_global is not None:
            q = q.gte("created_at", start_dt_global.isoformat()).lte("created_at", end_dt_global.isoformat())
        curr_resp = q.execute()
        assigned_count = int(curr_resp.count or 0)

        if prev_start_global is not None and prev_end_global is not None:
            prev_q = (
                supabase
                .table("lead_master")
                .select("id", count="exact")
                .not_.is_("cre_name", "null")
                .gte("created_at", prev_start_global.isoformat())
                .lte("created_at", prev_end_global.isoformat())
                .execute()
            )
            prev_assigned_count = int(prev_q.count or 0)
            if prev_assigned_count == 0:
                delta2 = "+∞%" if assigned_count > 0 else "0%"
            else:
                pct_change2 = (assigned_count - prev_assigned_count) / prev_assigned_count * 100.0
                delta2 = f"{pct_change2:+.1f}%"
        else:
            delta2 = "—"

        st.metric(label="Assigned to CRE", value=assigned_count, delta=delta2)
    except Exception as err:
        st.warning(f"Could not load KPI (Assigned to CRE): {err}")

with col_kpi_3:
    try:
        q = (
            supabase
            .table("lead_master")
            .select("id", count="exact")
            .not_.is_("ps_name", "null")
        )
        if filter_option_global != "All time" and start_dt_global is not None and end_dt_global is not None:
            q = q.gte("created_at", start_dt_global.isoformat()).lte("created_at", end_dt_global.isoformat())
        curr_resp = q.execute()
        ps_count = int(curr_resp.count or 0)

        if prev_start_global is not None and prev_end_global is not None:
            prev_q = (
                supabase
                .table("lead_master")
                .select("id", count="exact")
                .not_.is_("ps_name", "null")
                .gte("created_at", prev_start_global.isoformat())
                .lte("created_at", prev_end_global.isoformat())
                .execute()
            )
            prev_ps_count = int(prev_q.count or 0)
            if prev_ps_count == 0:
                delta3 = "+∞%" if ps_count > 0 else "0%"
            else:
                pct_change3 = (ps_count - prev_ps_count) / prev_ps_count * 100.0
                delta3 = f"{pct_change3:+.1f}%"
        else:
            delta3 = "—"

        st.metric(label="Assigned to PS", value=ps_count, delta=delta3)
    except Exception as err:
        st.warning(f"Could not load KPI (Assigned to PS): {err}")

with col_kpi_4:
    try:
        q = (
            supabase
            .table("lead_master")
            .select("id", count="exact")
            .eq("final_status", "Pending")
        )
        if filter_option_global != "All time" and start_dt_global is not None and end_dt_global is not None:
            q = q.gte("created_at", start_dt_global.isoformat()).lte("created_at", end_dt_global.isoformat())
        curr_resp = q.execute()
        pending_count = int(curr_resp.count or 0)

        if prev_start_global is not None and prev_end_global is not None:
            prev_q = (
                supabase
                .table("lead_master")
                .select("id", count="exact")
                .eq("final_status", "Pending")
                .gte("created_at", prev_start_global.isoformat())
                .lte("created_at", prev_end_global.isoformat())
                .execute()
            )
            prev_pending_count = int(prev_q.count or 0)
            if prev_pending_count == 0:
                delta_pend = "+∞%" if pending_count > 0 else "0%"
            else:
                pct_change_pend = (pending_count - prev_pending_count) / prev_pending_count * 100.0
                delta_pend = f"{pct_change_pend:+.1f}%"
        else:
            delta_pend = "—"

        st.metric(label="Pending Leads", value=pending_count, delta=delta_pend)
    except Exception as err:
        st.warning(f"Could not load KPI (Pending Leads): {err}")

with col_kpi_5:
    try:
        q = (
            supabase
            .table("lead_master")
            .select("id", count="exact")
            .eq("final_status", "Lost")
        )
        if filter_option_global != "All time" and start_dt_global is not None and end_dt_global is not None:
            q = q.gte("created_at", start_dt_global.isoformat()).lte("created_at", end_dt_global.isoformat())
        curr_resp = q.execute()
        lost_count = int(curr_resp.count or 0)

        if prev_start_global is not None and prev_end_global is not None:
            prev_q = (
                supabase
                .table("lead_master")
                .select("id", count="exact")
                .eq("final_status", "Lost")
                .gte("created_at", prev_start_global.isoformat())
                .lte("created_at", prev_end_global.isoformat())
                .execute()
            )
            prev_lost_count = int(prev_q.count or 0)
            if prev_lost_count == 0:
                delta_lost = "+∞%" if lost_count > 0 else "0%"
            else:
                pct_change_lost = (lost_count - prev_lost_count) / prev_lost_count * 100.0
                delta_lost = f"{pct_change_lost:+.1f}%"
        else:
            delta_lost = "—"

        st.metric(label="Lost Leads", value=lost_count, delta=delta_lost)
    except Exception as err:
        st.warning(f"Could not load KPI (Lost Leads): {err}")

with col_kpi_6:
    try:
        q = (
            supabase
            .table("lead_master")
            .select("id", count="exact")
            .eq("final_status", "Won")
        )
        if filter_option_global != "All time" and start_dt_global is not None and end_dt_global is not None:
            q = q.gte("created_at", start_dt_global.isoformat()).lte("created_at", end_dt_global.isoformat())
        curr_resp = q.execute()
        won_count = int(curr_resp.count or 0)

        if prev_start_global is not None and prev_end_global is not None:
            prev_q = (
                supabase
                .table("lead_master")
                .select("id", count="exact")
                .eq("final_status", "Won")
                .gte("created_at", prev_start_global.isoformat())
                .lte("created_at", prev_end_global.isoformat())
                .execute()
            )
            prev_won_count = int(prev_q.count or 0)
            if prev_won_count == 0:
                delta_won = "+∞%" if won_count > 0 else "0%"
            else:
                pct_change_won = (won_count - prev_won_count) / prev_won_count * 100.0
                delta_won = f"{pct_change_won:+.1f}%"
        else:
            delta_won = "—"

        # Compute total leads for percentage
        q_total_leads = supabase.table("lead_master").select("id", count="exact")
        if filter_option_global != "All time" and start_dt_global is not None and end_dt_global is not None:
            q_total_leads = q_total_leads.gte("created_at", start_dt_global.isoformat()).lte("created_at", end_dt_global.isoformat())
        total_leads_resp = q_total_leads.execute()
        total_leads_count = int(total_leads_resp.count or 0)
        won_pct = (won_count / total_leads_count * 100.0) if total_leads_count else 0.0
        pct_text_won = f"{won_pct:.2f}%"

        # Render custom metric card matching Walkin Won style
        delta_text_won = str(delta_won)
        if delta_text_won.startswith("+"):
            delta_class_won = "up"
            arrow_won = "▲"
        elif delta_text_won.startswith("-"):
            delta_class_won = "down"
            arrow_won = "▼"
        else:
            delta_class_won = "neutral"
            arrow_won = "—"

        custom_html_won = f"""
        <div class=\"won-metric-card\">
            <div class=\"label\">Won Leads</div>
            <div class=\"value-row\">
                <span class=\"big\">{won_count}</span>
                <span class=\"small\">{pct_text_won}</span>
            </div>
            <div class=\"delta {delta_class_won}\">{arrow_won}&nbsp;{delta_text_won}</div>
        </div>
        <style>
        .won-metric-card {{ display:inline-flex; flex-direction:column; gap:6px; }}
        .won-metric-card .label {{ font-size:14px; opacity:0.85; }}
        .won-metric-card .value-row {{ display:flex; align-items:baseline; gap:8px; }}
        .won-metric-card .value-row .big {{ font-size:32px; font-weight:700; line-height:1; }}
        .won-metric-card .value-row .small {{ font-size:13px; font-weight:600; color:#16a34a; line-height:1; }}
        .won-metric-card .delta {{ width:max-content; font-size:13px; padding:4px 10px; border-radius:999px; }}
        .won-metric-card .delta.up {{ background:rgba(34,197,94,0.15); color:#16a34a; }}
        .won-metric-card .delta.down {{ background:rgba(239,68,68,0.15); color:#ef4444; }}
        .won-metric-card .delta.neutral {{ background:rgba(156,163,175,0.15); color:#9aa0a6; }}
        </style>
        """
        st.markdown(custom_html_won, unsafe_allow_html=True)
    except Exception as err:
        st.warning(f"Could not load KPI (Won Leads): {err}")

with col_kpi_7:
    try:
        q = supabase.table("walkin_table").select("id", count="exact")
        if filter_option_global != "All time" and start_dt_global is not None and end_dt_global is not None:
            q = q.gte("created_at", start_dt_global.isoformat()).lte("created_at", end_dt_global.isoformat())
        curr_resp = q.execute()
        walkin_count = int(curr_resp.count or 0)

        if prev_start_global is not None and prev_end_global is not None:
            prev_q = (
                supabase
                .table("walkin_table")
                .select("id", count="exact")
                .gte("created_at", prev_start_global.isoformat())
                .lte("created_at", prev_end_global.isoformat())
                .execute()
            )
            prev_walkin_count = int(prev_q.count or 0)
            if prev_walkin_count == 0:
                delta_walkin = "+∞%" if walkin_count > 0 else "0%"
            else:
                pct_change_walkin = (walkin_count - prev_walkin_count) / prev_walkin_count * 100.0
                delta_walkin = f"{pct_change_walkin:+.1f}%"
        else:
            delta_walkin = "—"

        st.metric(label="Walkin Leads", value=walkin_count, delta=delta_walkin)
    except Exception as err:
        st.warning(f"Could not load KPI (Walkin Leads): {err}")

with col_kpi_8:
    try:
        q = (
            supabase
            .table("walkin_table")
            .select("id", count="exact")
            .eq("status", "Won")
        )
        if filter_option_global != "All time" and start_dt_global is not None and end_dt_global is not None:
            q = q.gte("created_at", start_dt_global.isoformat()).lte("created_at", end_dt_global.isoformat())
        curr_resp = q.execute()
        walkin_won_count = int(curr_resp.count or 0)

        # Compute conversion percentage: (Walkin Won / Total Walkins) * 100
        q_total_walkin = supabase.table("walkin_table").select("id", count="exact")
        if filter_option_global != "All time" and start_dt_global is not None and end_dt_global is not None:
            q_total_walkin = q_total_walkin.gte("created_at", start_dt_global.isoformat()).lte("created_at", end_dt_global.isoformat())
        total_walkin_resp = q_total_walkin.execute()
        total_walkin_count = int(total_walkin_resp.count or 0)
        walkin_won_pct = (walkin_won_count / total_walkin_count * 100.0) if total_walkin_count else 0.0

        if prev_start_global is not None and prev_end_global is not None:
            prev_q = (
                supabase
                .table("walkin_table")
                .select("id", count="exact")
                .eq("status", "Won")
                .gte("created_at", prev_start_global.isoformat())
                .lte("created_at", prev_end_global.isoformat())
                .execute()
            )
            prev_walkin_won_count = int(prev_q.count or 0)
            if prev_walkin_won_count == 0:
                delta_walkin_won = "+∞%" if walkin_won_count > 0 else "0%"
            else:
                pct_change_walkin_won = (walkin_won_count - prev_walkin_won_count) / prev_walkin_won_count * 100.0
                delta_walkin_won = f"{pct_change_walkin_won:+.1f}%"
        else:
            delta_walkin_won = "—"

        # Render custom metric card so the small percent can sit inline beside the big number
        pct_text = f"{walkin_won_pct:.2f}%"
        delta_text = str(delta_walkin_won)
        if delta_text.startswith("+"):
            delta_class = "up"
            arrow = "▲"
        elif delta_text.startswith("-"):
            delta_class = "down"
            arrow = "▼"
        else:
            delta_class = "neutral"
            arrow = "—"

        custom_html = f"""
        <div class=\"won-metric-card\">
            <div class=\"label\">Walkin Won</div>
            <div class=\"value-row\">
                <span class=\"big\">{walkin_won_count}</span>
                <span class=\"small\">{pct_text}</span>
            </div>
            <div class=\"delta {delta_class}\">{arrow}&nbsp;{delta_text}</div>
        </div>
        <style>
        .won-metric-card {{ display:inline-flex; flex-direction:column; gap:6px; }}
        .won-metric-card .label {{ font-size:14px; opacity:0.85; }}
        .won-metric-card .value-row {{ display:flex; align-items:baseline; gap:8px; }}
        .won-metric-card .value-row .big {{ font-size:32px; font-weight:700; line-height:1; }}
        .won-metric-card .value-row .small {{ font-size:13px; font-weight:600; color:#16a34a; line-height:1; }}
        .won-metric-card .delta {{ width:max-content; font-size:13px; padding:4px 10px; border-radius:999px; }}
        .won-metric-card .delta.up {{ background:rgba(34,197,94,0.15); color:#16a34a; }}
        .won-metric-card .delta.down {{ background:rgba(239,68,68,0.15); color:#ef4444; }}
        .won-metric-card .delta.neutral {{ background:rgba(156,163,175,0.15); color:#9aa0a6; }}
        </style>
        """
        st.markdown(custom_html, unsafe_allow_html=True)
    except Exception as err:
        st.warning(f"Could not load KPI (Walkin Won): {err}")

# Horizontal navigation tabs for different dashboard sections
tab1, tab2, tab3 = st.tabs(["🔧 Admin", "📊 PS Performance", "👥 CRE Performance"])

with tab1:
    # Fetch lead sources data with final_status and created_at
    try:
        leads_res = supabase.table("lead_master").select("source", "final_status", "created_at").execute()
        df_leads = pd.DataFrame(leads_res.data)
    except Exception as err:
        st.warning(f"Could not load lead sources: {err}")
        df_leads = pd.DataFrame()

    # Use global date filter inside Admin dashboard
    filter_option_admin = filter_option_global
    start_dt_admin, end_dt_admin = start_dt_global, end_dt_global

    # Apply created_at filter to admin data
    df_leads_filtered = df_leads.copy()
    if filter_option_admin != "All time" and start_dt_admin is not None and end_dt_admin is not None:
        if not df_leads.empty and "created_at" in df_leads.columns:
            created_ts_admin = pd.to_datetime(df_leads["created_at"], errors="coerce", utc=True)
            mask_admin = created_ts_admin.between(start_dt_admin, end_dt_admin)
            df_leads_filtered = df_leads.loc[mask_admin].copy()
        else:
            st.warning("created_at column missing; date filter not applied to admin data.")

    # Create four columns for Admin dashboard (shrink Conversion a bit, widen Walkin panel)
    left_col, spacer_col, mid_col, right_col = st.columns([0.28, 0.02, 0.26, 0.44])
    
    with left_col:
        st.subheader("Source-wise Lead Count")
        if not df_leads_filtered.empty and "source" in df_leads_filtered.columns:
            source_counts = (
                df_leads_filtered["source"].astype(str).str.strip().replace("", "Unknown").value_counts()
                .rename_axis("source").reset_index(name="count")
                .sort_values("count", ascending=False)
            )
            total_count_admin_chart = int(source_counts["count"].sum()) or 1
            source_counts["percent"] = source_counts["count"] / total_count_admin_chart
            chart = (
                alt.Chart(source_counts)
                .mark_bar()
                .encode(
                    x=alt.X("source:N", sort="-y", title=None),
                    y=alt.Y("count:Q", title=None),
                    color=alt.Color("source:N", legend=None),
                    tooltip=[
                        alt.Tooltip("source:N", title="Source"),
                        alt.Tooltip("count:Q", title="Count"),
                        alt.Tooltip("percent:Q", title="Percent", format=".1%"),
                    ],
                )
            )
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("No lead sources available to display.")

    with mid_col:
        st.subheader("ETBR")
        if not df_leads_filtered.empty and "source" in df_leads_filtered.columns:
            # Clean the filtered data
            df_leads_clean = df_leads_filtered.copy()
            df_leads_clean["source"] = df_leads_clean["source"].astype(str).str.strip().replace("", "Unknown")
            df_leads_clean["final_status"] = df_leads_clean["final_status"].astype(str).str.strip()
            
            # Get unique sources and their counts
            source_counts = df_leads_clean["source"].value_counts()
            
            # Calculate won counts for each source
            won_counts = []
            for source in source_counts.index:
                won_count = len(df_leads_clean[
                    (df_leads_clean["source"] == source) & 
                    (df_leads_clean["final_status"].str.lower() == "won")
                ])
                won_counts.append(won_count)
            
            # Create a DataFrame with sources, counts, won counts
            sources_df = pd.DataFrame({
                "Source": source_counts.index,
                "Count": source_counts.values,
                "Won": won_counts
            })

            # Append special Walkin row from walkin_table using same admin filter
            try:
                df_walkin_admin = df.copy()
                if (
                    filter_option_admin != "All time"
                    and start_dt_admin is not None
                    and end_dt_admin is not None
                    and "created_at" in df.columns
                ):
                    created_ts_walkin = pd.to_datetime(df["created_at"], errors="coerce", utc=True)
                    mask_walkin = created_ts_walkin.between(start_dt_admin, end_dt_admin)
                    df_walkin_admin = df.loc[mask_walkin].copy()

                walkin_total = int(len(df_walkin_admin))
                if "status" in df_walkin_admin.columns:
                    walkin_won = int(
                        (df_walkin_admin["status"].astype(str).str.strip().str.lower() == "won").sum()
                    )
                else:
                    walkin_won = 0

                # Compute Walkin TD total consistent with Walkin (branch-wise)
                td_total_walkin = 0
                if "test_drive_done" in df_walkin_admin.columns:
                    tdd_series_mid = df_walkin_admin["test_drive_done"]
                    if pd.api.types.is_bool_dtype(tdd_series_mid):
                        td_mask_mid = tdd_series_mid.fillna(False)
                    else:
                        td_mask_mid = tdd_series_mid.astype(str).str.strip().str.lower().isin(["true", "yes", "1"])
                    td_total_walkin = int(td_mask_mid.sum())

                walkin_row = pd.DataFrame([
                    {"Source": "Walkin", "Count": walkin_total, "Won": walkin_won}
                ])
                sources_df = pd.concat([sources_df, walkin_row], ignore_index=True)
            except Exception as err:
                st.warning(f"Could not append Walkin row: {err}")

            # Enquiry per source for Conversion table (non-Walkin via lead_master ps_name not null; Walkin = total punched)
            try:
                enquiry_map_conv = {}
                for src in list(sources_df["Source"]):
                    if str(src).strip().lower() == "walkin":
                        enquiry_map_conv[src] = int(walkin_total)
                        continue
                    q_conv = (
                        supabase
                        .table("lead_master")
                        .select("id", count="exact")
                        .not_.is_("ps_name", "null")
                        .eq("source", src)
                    )
                    if filter_option_admin != "All time" and start_dt_admin is not None and end_dt_admin is not None:
                        q_conv = q_conv.gte("created_at", start_dt_admin.isoformat()).lte("created_at", end_dt_admin.isoformat())
                    r_conv = q_conv.execute()
                    enquiry_map_conv[src] = int(r_conv.count or 0)
                sources_df["Enquiry"] = sources_df["Source"].map(enquiry_map_conv).astype(int)
            except Exception as err:
                st.warning(f"Could not compute Enquiry for Conversion: {err}")

            # TD per source for Conversion table (non-Walkin via lead_master test_drive_status; Walkin = TD total from Walkin table)
            try:
                td_map_conv = {}
                for src in list(sources_df["Source"]):
                    if str(src).strip().lower() == "walkin":
                        td_map_conv[src] = int(td_total_walkin)
                        continue
                    q_td_conv = (
                        supabase
                        .table("lead_master")
                        .select("id", count="exact")
                        .eq("test_drive_status", True)
                        .eq("source", src)
                    )
                    if filter_option_admin != "All time" and start_dt_admin is not None and end_dt_admin is not None:
                        q_td_conv = q_td_conv.gte("created_at", start_dt_admin.isoformat()).lte("created_at", end_dt_admin.isoformat())
                    r_td_conv = q_td_conv.execute()
                    td_map_conv[src] = int(r_td_conv.count or 0)
                sources_df["TD"] = sources_df["Source"].map(td_map_conv).astype(int)
            except Exception as err:
                st.warning(f"Could not compute TD for Conversion: {err}")

            # Calculate conversion percentage (Won/Count * 100)
            sources_df["%"] = (sources_df["Won"] / sources_df["Count"] * 100).round(2)
            
            # Sort by conversion percentage descending, then by count descending, then by source name
            sources_df = sources_df.sort_values(["%", "Count", "Source"], ascending=[False, False, True])
            
            # Make Source the index, append TOTAL row, and show it in the table
            sources_df_display = sources_df.set_index("Source")
            total_count_src = int(sources_df["Count"].sum())
            total_won_src = int(sources_df["Won"].sum())
            total_enquiry_src = int(sources_df["Enquiry"].sum()) if "Enquiry" in sources_df.columns else 0
            total_td_src = int(sources_df["TD"].sum()) if "TD" in sources_df.columns else 0
            total_conv_src = (total_won_src / total_count_src * 100.0) if total_count_src else 0.0
            total_row_src = pd.DataFrame({
                "Count": [total_count_src],
                "Enquiry": [total_enquiry_src],
                "TD": [total_td_src],
                "Won": [total_won_src],
                "%": [round(total_conv_src, 2)],
            }, index=["TOTAL"])
            sources_df_display = pd.concat([sources_df_display, total_row_src])

            # Display with Enquiry and TD columns right after Count; rename Count to E for display only
            display_cols = [c for c in ["Count", "Enquiry", "TD", "Won", "%"] if c in sources_df_display.columns]
            display_df = sources_df_display[display_cols].rename(columns={"Count": "E", "Enquiry": "QL", "Won": "BR"})
            st.dataframe(display_df, use_container_width=True, hide_index=False)

            
        else:
            st.info("No lead sources available to display.")

    # Right column: Walkin (branch-wise) using the same Admin date filter
    with right_col:
        st.subheader("Walkin (branch-wise)")
        # Apply created_at filter to walkin data
        df_walkin_admin = df.copy()
        if (
            filter_option_admin != "All time"
            and start_dt_admin is not None
            and end_dt_admin is not None
            and not df.empty
            and "created_at" in df.columns
        ):
            created_ts_walkin_admin = pd.to_datetime(df["created_at"], errors="coerce", utc=True)
            mask_walkin_admin = created_ts_walkin_admin.between(start_dt_admin, end_dt_admin)
            df_walkin_admin = df.loc[mask_walkin_admin].copy()

        # Build summary table
        if not df_walkin_admin.empty and "branch" in df_walkin_admin.columns:
            unique_branches_admin = (
                pd.Series(sorted(df_walkin_admin["branch"].dropna().astype(str).unique()))
                .rename("branch")
                .to_frame()
            )
            branch_counts_admin = (
                df_walkin_admin["branch"].astype(str).value_counts().rename_axis("branch").reset_index(name="rows")
            )
            # Status-based counts
            if "status" in df_walkin_admin.columns:
                pending_counts_admin = (
                    df_walkin_admin[df_walkin_admin["status"].astype(str).str.strip().str.lower() == "pending"]
                    .groupby("branch").size().rename_axis("branch").reset_index(name="pending")
                )
                won_counts_admin = (
                    df_walkin_admin[df_walkin_admin["status"].astype(str).str.strip().str.lower() == "won"]
                    .groupby("branch").size().rename_axis("branch").reset_index(name="won")
                )
                lost_counts_admin = (
                    df_walkin_admin[df_walkin_admin["status"].astype(str).str.strip().str.lower() == "lost"]
                    .groupby("branch").size().rename_axis("branch").reset_index(name="lost")
                )
            else:
                pending_counts_admin = pd.DataFrame({"branch": [], "pending": []})
                won_counts_admin = pd.DataFrame({"branch": [], "won": []})
                lost_counts_admin = pd.DataFrame({"branch": [], "lost": []})

            # Test drive done (TD) counts per branch within filtered data
            if "test_drive_done" in df_walkin_admin.columns:
                tdd_series = df_walkin_admin["test_drive_done"]
                if pd.api.types.is_bool_dtype(tdd_series):
                    td_mask_admin = tdd_series.fillna(False)
                else:
                    td_mask_admin = tdd_series.astype(str).str.strip().str.lower().isin(["true", "yes", "1"])
                td_counts_admin = (
                    df_walkin_admin[td_mask_admin]
                    .groupby("branch")
                    .size()
                    .rename_axis("branch")
                    .reset_index(name="td")
                )
            else:
                td_counts_admin = pd.DataFrame({"branch": [], "td": []})

            # Touched/Untouched among pending
            if "first_call_date" in df_walkin_admin.columns and "status" in df_walkin_admin.columns:
                status_pending_mask_admin = df_walkin_admin["status"].astype(str).str.strip().str.lower() == "pending"
                has_first_call_mask_admin = df_walkin_admin["first_call_date"].notna() & (df_walkin_admin["first_call_date"].astype(str).str.strip() != "")
                touched_mask_admin = status_pending_mask_admin & has_first_call_mask_admin
                untouched_mask_admin = status_pending_mask_admin & ~has_first_call_mask_admin
                touched_counts_admin = (
                    df_walkin_admin[touched_mask_admin]
                    .groupby("branch").size().rename_axis("branch").reset_index(name="touched")
                )
                untouched_counts_admin = (
                    df_walkin_admin[untouched_mask_admin]
                    .groupby("branch").size().rename_axis("branch").reset_index(name="untouched")
                )
            else:
                touched_counts_admin = pd.DataFrame({"branch": [], "touched": []})
                untouched_counts_admin = pd.DataFrame({"branch": [], "untouched": []})

            branches_table_admin = unique_branches_admin.merge(branch_counts_admin, on="branch", how="left").fillna({"rows": 0})
            branches_table_admin = branches_table_admin.merge(pending_counts_admin, on="branch", how="left").fillna({"pending": 0})
            branches_table_admin = branches_table_admin.merge(touched_counts_admin, on="branch", how="left").fillna({"touched": 0})
            branches_table_admin = branches_table_admin.merge(untouched_counts_admin, on="branch", how="left").fillna({"untouched": 0})
            branches_table_admin = branches_table_admin.merge(won_counts_admin, on="branch", how="left").fillna({"won": 0})
            branches_table_admin = branches_table_admin.merge(lost_counts_admin, on="branch", how="left").fillna({"lost": 0})
            branches_table_admin = branches_table_admin.merge(td_counts_admin, on="branch", how="left").fillna({"td": 0})
            branches_table_admin["rows"] = branches_table_admin["rows"].astype(int)
            branches_table_admin["pending"] = branches_table_admin["pending"].astype(int)
            branches_table_admin["touched"] = branches_table_admin["touched"].astype(int)
            branches_table_admin["untouched"] = branches_table_admin["untouched"].astype(int)
            branches_table_admin["won"] = branches_table_admin["won"].astype(int)
            branches_table_admin["lost"] = branches_table_admin["lost"].astype(int)
            branches_table_admin["td"] = branches_table_admin["td"].astype(int)
        else:
            branches_table_admin = pd.DataFrame({"branch": [], "rows": [], "pending": [], "touched": [], "untouched": [], "won": [], "lost": [], "td": []})

        # Finalize display columns and conversion
        desired_order_admin = ["branch", "rows", "pending", "touched", "untouched", "won", "lost", "td"]
        columns_in_order_admin = [col for col in desired_order_admin if col in branches_table_admin.columns]
        branches_table_admin = branches_table_admin[columns_in_order_admin]

        branches_table_display_admin = branches_table_admin.set_index("branch").rename(
            columns={
                "rows": "Punched",
                "pending": "Pending",
                "touched": "Touched",
                "untouched": "Untouched",
                "won": "Won",
                "lost": "Lost",
                "td": "TD",
            }
        )

        if not branches_table_display_admin.empty:
            safe_div_admin = branches_table_display_admin.apply(
                lambda row: (row["Won"] / row["Punched"] * 100.0) if row["Punched"] else 0.0,
                axis=1
            )
            branches_table_display_admin["%"] = safe_div_admin.round(2)

            numeric_cols_admin = [c for c in ["Punched", "Pending", "Touched", "Untouched", "Won", "Lost", "TD"] if c in branches_table_display_admin.columns]
            total_row_admin = branches_table_display_admin[numeric_cols_admin].sum()
            total_row_admin["%"] = (total_row_admin["Won"] / total_row_admin["Punched"] * 100.0) if total_row_admin["Punched"] else 0.0
            total_row_admin = total_row_admin.round(2)
            total_row_admin.name = "TOTAL"
            branches_table_display_admin = pd.concat([branches_table_display_admin, total_row_admin.to_frame().T])

        st.dataframe(branches_table_display_admin, use_container_width=True, hide_index=False)

with tab2:
    st.info("Walkin (branch-wise) has been moved to the Admin tab next to ETBR.")

with tab3:
    st.subheader("CRE Performance")
    try:
        # Fetch CRE data (and created_at for filtering) from lead_master
        cre_res = (
            supabase
            .table("lead_master")
            .select("cre_name", "created_at", "lead_status", "first_call_date", "final_status")
            .execute()
        )
        df_cre = pd.DataFrame(cre_res.data)

        # Apply global date filter if available
        df_cre_filtered = df_cre.copy()
        if filter_option_global != "All time" and start_dt_global is not None and end_dt_global is not None:
            if not df_cre.empty and "created_at" in df_cre.columns:
                created_ts_cre = pd.to_datetime(df_cre["created_at"], errors="coerce", utc=True)
                mask_cre = created_ts_cre.between(start_dt_global, end_dt_global)
                df_cre_filtered = df_cre.loc[mask_cre].copy()

        # Build table with first column as CRE names and Touched/UT counts
        if not df_cre_filtered.empty and "cre_name" in df_cre_filtered.columns:
            # Normalize CRE names
            cre_series = (
                df_cre_filtered["cre_name"].fillna("").astype(str).str.strip().replace("", "Unassigned Leads")
            )

            # Derive Touched mask per provided criteria
            lead_status_series = df_cre_filtered.get("lead_status", pd.Series(dtype=object)).fillna("").astype(str).str.strip().str.lower()
            final_status_series = df_cre_filtered.get("final_status", pd.Series(dtype=object)).fillna("").astype(str).str.strip().str.lower()
            first_call_clean = df_cre_filtered.get("first_call_date", pd.Series(dtype=object)).fillna("").astype(str).str.strip()
            final_status_is_null = df_cre_filtered["final_status"].isna() if "final_status" in df_cre_filtered.columns else pd.Series(False, index=df_cre_filtered.index)

            touched_statuses = {
                "rnr",
                "busy on another call",
                "call disconnected",
                "call not connected",
            }

            touched_mask = (
                lead_status_series.isin(touched_statuses)
                & (first_call_clean == "")
                & (final_status_series == "pending")
            )

            # Derive UT mask per provided SQL:
            # first_call_date is null/empty AND lead_status == 'Pending' AND (final_status == 'Pending' OR final_status is null)
            ut_mask = (
                (first_call_clean == "")
                & (lead_status_series == "pending")
                & ((final_status_series == "pending") | (final_status_is_null))
            )

            # Derive Followup mask per provided SQL:
            # first_call_date is null/empty AND lead_status == 'Call me Back' AND (final_status == 'Pending' OR final_status is null)
            followup_mask = (
                (first_call_clean == "")
                & (lead_status_series == "call me back")
                & ((final_status_series == "pending") | (final_status_is_null))
            )

            # Open leads: final_status == 'Pending' AND first_call_date is NOT NULL/empty
            open_mask = (
                (first_call_clean != "")
                & (final_status_series == "pending")
            )

            df_tmp = pd.DataFrame({
                "CRE": cre_series,
                "touched_flag": touched_mask.astype(int),
                "ut_flag": ut_mask.astype(int),
                "followup_flag": followup_mask.astype(int),
                "open_flag": open_mask.astype(int),
            })
            # Exclude Unassigned Leads from table and totals
            df_tmp_valid = df_tmp[df_tmp["CRE"] != "Unassigned Leads"].copy()
            agg_counts = (
                df_tmp_valid
                .groupby("CRE")[ ["touched_flag", "ut_flag", "followup_flag", "open_flag"] ]
                .sum()
                .astype(int)
                .reset_index()
                .rename(columns={"touched_flag": "Touched", "ut_flag": "UT", "followup_flag": "Followup", "open_flag": "Open leads"})
            )

            # Total leads assigned per CRE (row count per CRE)
            assigned_counts = (
                df_tmp_valid
                .groupby("CRE")
                .size()
                .reset_index(name="Assigned")
            )

            # Final CRE table: all unique CREs with Touched counts (fill missing with 0)
            cre_names = pd.Series(sorted(df_tmp_valid["CRE"].unique())).rename("CRE").to_frame()
            cre_table = (
                cre_names
                .merge(agg_counts, on="CRE", how="left")
                .merge(assigned_counts, on="CRE", how="left")
                .fillna({"Touched": 0, "UT": 0, "Followup": 0, "Open leads": 0, "Assigned": 0})
            )
            cre_table["Touched"] = cre_table["Touched"].astype(int)
            cre_table["UT"] = cre_table["UT"].astype(int)
            cre_table["Followup"] = cre_table["Followup"].astype(int)
            cre_table["Assigned"] = cre_table["Assigned"].astype(int)
            if "Open leads" in cre_table.columns:
                cre_table["Open leads"] = cre_table["Open leads"].astype(int)

            # Reorder columns and sort by Assigned descending
            desired_order_cols = [c for c in ["CRE", "Assigned", "Open leads", "UT", "Touched", "Followup"] if c in cre_table.columns]
            cre_table = cre_table[desired_order_cols]
            if "Assigned" in cre_table.columns:
                cre_table = cre_table.sort_values("Assigned", ascending=False)

            # Prepare pinned TOTAL row (within the same grid)
            numeric_cols = [c for c in ["Assigned", "Open leads", "UT", "Touched", "Followup"] if c in cre_table.columns]
            total_values = {c: int(cre_table[c].sum()) for c in numeric_cols}
            total_row_dict = {**{"CRE": "TOTAL"}, **total_values}

            # Dynamically size the table so CRE names (index) are fully visible
            try:
                max_cre_len = int(cre_table["CRE"].astype(str).str.len().max()) if not cre_table.empty else 10
            except Exception:
                max_cre_len = 10
            per_char_px = 9  # approximate px per character in default font
            index_padding_px = 80
            other_columns_px = 280  # space for numeric columns
            desired_width = max(420, min(1200, per_char_px * max_cre_len + index_padding_px + other_columns_px))
            # Render a simple Streamlit table with TOTAL appended (classic view)
            cre_table_with_total = pd.concat([cre_table, pd.DataFrame([total_row_dict])], ignore_index=True)
            total_rows = int(len(cre_table_with_total))
            row_px = 34
            header_px = 38
            padding_px = 12
            computed_height = header_px + row_px * total_rows + padding_px
            df_display = cre_table_with_total.copy()
            try:
                highlight_css = "background-color: #419D78; color: #ffffff; font-weight: 600;"
                styled = df_display.style.apply(
                    lambda row: [highlight_css] * len(row) if str(row.get("CRE", "")) == "TOTAL" else [""] * len(row),
                    axis=1,
                )
                st.dataframe(
                    styled,
                    use_container_width=False,
                    width=desired_width,
                    height=computed_height,
                    hide_index=True,
                )
            except Exception:
                st.dataframe(
                    df_display,
                    use_container_width=False,
                    width=desired_width,
                    height=computed_height,
                    hide_index=True,
                )
        else:
            st.info("No CRE data available to display.")
    except Exception as err:
        st.warning(f"Could not load CRE Performance data: {err}")