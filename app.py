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
from auth import init_session_state, login_form, admin_user_management, require_auth, require_admin, show_sidebar_navigation

# Load environment variables
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

@st.cache_resource
def init_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

supabase = init_supabase()

# Initialize authentication
init_session_state(supabase)

# Fetch data
res = supabase.table("walkin_table").select("*").execute()
df = pd.DataFrame(res.data)

# Page layout and CSS to left-align content and use full width
st.set_page_config(page_title="Analytics Dashboard", layout="wide", initial_sidebar_state="collapsed")
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

# Check authentication
if not require_auth():
    st.stop()

# Show sidebar navigation
show_sidebar_navigation()

# Check if user wants to manage users (admin only)
if "show_user_management" in st.session_state and st.session_state.show_user_management:
    if require_admin():
        admin_user_management()
    else:
        st.error("You don't have permission to access user management.")
        st.session_state.show_user_management = False
        st.rerun()
    st.stop()

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
            q = q.gte("ps_assigned_at", start_dt_global.isoformat()).lte("ps_assigned_at", end_dt_global.isoformat())
        curr_resp = q.execute()
        ps_count = int(curr_resp.count or 0)

        if prev_start_global is not None and prev_end_global is not None:
            prev_q = (
                supabase
                .table("lead_master")
                .select("id", count="exact")
                .not_.is_("ps_name", "null")
                .gte("ps_assigned_at", prev_start_global.isoformat())
                .lte("ps_assigned_at", prev_end_global.isoformat())
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

        # Compute total leads for percentage (use same base as Leads KPI → created_at)
        q_total_leads_ps = supabase.table("lead_master").select("id", count="exact")
        if filter_option_global != "All time" and start_dt_global is not None and end_dt_global is not None:
            q_total_leads_ps = q_total_leads_ps.gte("created_at", start_dt_global.isoformat()).lte("created_at", end_dt_global.isoformat())
        total_leads_resp_ps = q_total_leads_ps.execute()
        total_leads_count_ps = int(total_leads_resp_ps.count or 0)
        ps_assigned_pct = (ps_count / total_leads_count_ps * 100.0) if total_leads_count_ps else 0.0
        pct_text_ps = f"{ps_assigned_pct:.2f}%"

        # Render custom metric card similar to Won/Walkin Won
        delta_text_ps = str(delta3)
        if delta_text_ps.startswith("+"):
            delta_class_ps = "up"
            arrow_ps = "▲"
        elif delta_text_ps.startswith("-"):
            delta_class_ps = "down"
            arrow_ps = "▼"
        else:
            delta_class_ps = "neutral"
            arrow_ps = "—"

        custom_html_ps = f"""
        <div class=\"won-metric-card\">
            <div class=\"label\">Assigned to PS</div>
            <div class=\"value-row\">
                <span class=\"big\">{ps_count}</span>
                <span class=\"small\">{pct_text_ps}</span>
            </div>
            <div class=\"delta {delta_class_ps}\">{arrow_ps}&nbsp;{delta_text_ps}</div>
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
        st.markdown(custom_html_ps, unsafe_allow_html=True)
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

        # Compute total leads for percentage
        q_total_leads_for_lost = supabase.table("lead_master").select("id", count="exact")
        if filter_option_global != "All time" and start_dt_global is not None and end_dt_global is not None:
            q_total_leads_for_lost = q_total_leads_for_lost.gte("created_at", start_dt_global.isoformat()).lte("created_at", end_dt_global.isoformat())
        total_leads_resp_for_lost = q_total_leads_for_lost.execute()
        total_leads_count_for_lost = int(total_leads_resp_for_lost.count or 0)
        lost_pct = (lost_count / total_leads_count_for_lost * 100.0) if total_leads_count_for_lost else 0.0
        pct_text_lost = f"{lost_pct:.2f}%"

        # Render custom metric card similar to Won/Walkin Won
        delta_text_lost = str(delta_lost)
        if delta_text_lost.startswith("+"):
            delta_class_lost = "up"
            arrow_lost = "▲"
        elif delta_text_lost.startswith("-"):
            delta_class_lost = "down"
            arrow_lost = "▼"
        else:
            delta_class_lost = "neutral"
            arrow_lost = "—"

        custom_html_lost = f"""
        <div class=\"lost-metric-card\">
            <div class=\"label\">Lost Leads</div>
            <div class=\"value-row\">
                <span class=\"big\">{lost_count}</span>
                <span class=\"small\">{pct_text_lost}</span>
            </div>
            <div class=\"delta {delta_class_lost}\">{arrow_lost}&nbsp;{delta_text_lost}</div>
        </div>
        <style>
        .lost-metric-card {{ display:inline-flex; flex-direction:column; gap:6px; }}
        .lost-metric-card .label {{ font-size:14px; opacity:0.85; }}
        .lost-metric-card .value-row {{ display:flex; align-items:baseline; gap:8px; }}
        .lost-metric-card .value-row .big {{ font-size:32px; font-weight:700; line-height:1; }}
        .lost-metric-card .value-row .small {{ font-size:13px; font-weight:600; color:#ef4444; line-height:1; }}
        .lost-metric-card .delta {{ width:max-content; font-size:13px; padding:4px 10px; border-radius:999px; }}
        .lost-metric-card .delta.up {{ background:rgba(34,197,94,0.15); color:#16a34a; }}
        .lost-metric-card .delta.down {{ background:rgba(239,68,68,0.15); color:#ef4444; }}
        .lost-metric-card .delta.neutral {{ background:rgba(156,163,175,0.15); color:#9aa0a6; }}
        </style>
        """
        st.markdown(custom_html_lost, unsafe_allow_html=True)
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
        # Build Walkin Won count with robust date-column fallback: won_timestamp → updated_at → created_at
        filter_cols_priority = ["won_timestamp", "updated_at", "created_at"]
        walkin_won_count = 0
        last_err = None
        if filter_option_global != "All time" and start_dt_global is not None and end_dt_global is not None:
            for col_name in filter_cols_priority:
                try:
                    q = (
                        supabase
                        .table("walkin_table")
                        .select("id", count="exact")
                        .eq("status", "Won")
                        .gte(col_name, start_dt_global.isoformat())
                        .lte(col_name, end_dt_global.isoformat())
                    )
                    curr_resp = q.execute()
                    walkin_won_count = int(curr_resp.count or 0)
                    last_err = None
                    break
                except Exception as _err:
                    last_err = _err
        else:
            try:
                curr_resp = (
                    supabase
                    .table("walkin_table")
                    .select("id", count="exact")
                    .eq("status", "Won")
                    .execute()
                )
                walkin_won_count = int(curr_resp.count or 0)
            except Exception as _err:
                last_err = _err

        # Compute conversion percentage: (Walkin Won / Total Walkins) * 100
        # Total walkins with the same fallback
        total_walkin_count = 0
        if filter_option_global != "All time" and start_dt_global is not None and end_dt_global is not None:
            for col_name in filter_cols_priority:
                try:
                    q_total_walkin = (
                        supabase
                        .table("walkin_table")
                        .select("id", count="exact")
                        .gte(col_name, start_dt_global.isoformat())
                        .lte(col_name, end_dt_global.isoformat())
                    )
                    total_walkin_resp = q_total_walkin.execute()
                    total_walkin_count = int(total_walkin_resp.count or 0)
                    break
                except Exception:
                    continue
        else:
            try:
                total_walkin_resp = supabase.table("walkin_table").select("id", count="exact").execute()
                total_walkin_count = int(total_walkin_resp.count or 0)
            except Exception:
                total_walkin_count = 0
        walkin_won_pct = (walkin_won_count / total_walkin_count * 100.0) if total_walkin_count else 0.0

        if prev_start_global is not None and prev_end_global is not None:
            prev_walkin_won_count = 0
            for col_name in filter_cols_priority:
                try:
                    prev_q = (
                        supabase
                        .table("walkin_table")
                        .select("id", count="exact")
                        .eq("status", "Won")
                        .gte(col_name, prev_start_global.isoformat())
                        .lte(col_name, prev_end_global.isoformat())
                        .execute()
                    )
                    prev_walkin_won_count = int(prev_q.count or 0)
                    break
                except Exception:
                    continue
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
tab1, tab2, tab3 = st.tabs(["Overall", "Branch Performance", "👥 CRE Performance"])

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
                # Walkin Won using updated_at filter instead of created_at
                walkin_won = 0
                if (
                    filter_option_admin != "All time"
                    and start_dt_admin is not None
                    and end_dt_admin is not None
                    and not df.empty
                    and "updated_at" in df.columns
                    and "status" in df.columns
                ):
                    updated_ts_walkin_won = pd.to_datetime(df["updated_at"], errors="coerce", utc=True)
                    mask_walkin_won = updated_ts_walkin_won.between(start_dt_admin, end_dt_admin)
                    df_walkin_won_admin = df.loc[mask_walkin_won].copy()
                    walkin_won = int(
                        (df_walkin_won_admin["status"].astype(str).str.strip().str.lower() == "won").sum()
                    )
                else:
                    # Fallback to created_at filtering if updated_at is not available or "All time" is selected
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
                        q_conv = q_conv.gte("ps_assigned_at", start_dt_admin.isoformat()).lte("ps_assigned_at", end_dt_admin.isoformat())
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
                # Won counts using updated_at filter instead of created_at
                won_counts_admin = pd.DataFrame({"branch": [], "won": []})
                if (
                    filter_option_admin != "All time"
                    and start_dt_admin is not None
                    and end_dt_admin is not None
                    and not df.empty
                    and "updated_at" in df.columns
                ):
                    updated_ts_won = pd.to_datetime(df["updated_at"], errors="coerce", utc=True)
                    mask_won = updated_ts_won.between(start_dt_admin, end_dt_admin)
                    df_won_admin = df.loc[mask_won].copy()
                    won_counts_admin = (
                        df_won_admin[df_won_admin["status"].astype(str).str.strip().str.lower() == "won"]
                        .groupby("branch").size().rename_axis("branch").reset_index(name="won")
                    )
                else:
                    # Fallback to created_at filtering if updated_at is not available or "All time" is selected
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

    # Additional table: Unique branches from lead_master with global date filter (50% width)
    dl_left, _dl_right = st.columns([0.75, 0.25])
    with dl_left:
        st.subheader("Digital Leads Summary (branch-wise)")
        try:
            lm_res = (
                supabase
                .table("lead_master")
                .select("branch", "ps_assigned_at", "ps_name", "source", "final_status")
                .execute()
            )
            df_lm = pd.DataFrame(lm_res.data)

            # Apply global/Overall date filter on created_at
            df_lm_filtered = df_lm.copy()
            if filter_option_admin != "All time" and start_dt_admin is not None and end_dt_admin is not None:
                if not df_lm.empty and "ps_assigned_at" in df_lm.columns:
                    assigned_ts_lm = pd.to_datetime(df_lm["ps_assigned_at"], errors="coerce", utc=True)
                    mask_lm = assigned_ts_lm.between(start_dt_admin, end_dt_admin)
                    df_lm_filtered = df_lm.loc[mask_lm].copy()

            # Build table with unique branch values and Leads Assigned count (ps_name not null)
            if not df_lm_filtered.empty and "branch" in df_lm_filtered.columns:
                branch_clean = df_lm_filtered["branch"].fillna("").astype(str).str.strip().replace("", "Unknown")
                branches_unique_df = (
                    pd.Series(sorted(branch_clean.unique()))
                    .rename("Branch")
                    .to_frame()
                )

                # Count rows per branch where ps_name exists (not null/empty)
                if "ps_name" in df_lm_filtered.columns:
                    ps_exists = df_lm_filtered["ps_name"].notna() & (df_lm_filtered["ps_name"].astype(str).str.strip() != "")
                    assigned_counts = (
                        branch_clean[ps_exists]
                        .value_counts()
                        .rename_axis("Branch")
                        .reset_index(name="Leads Assigned")
                    )
                    branches_unique_df = (
                        branches_unique_df
                        .merge(assigned_counts, on="Branch", how="left")
                        .fillna({"Leads Assigned": 0})
                    )
                    branches_unique_df["Leads Assigned"] = branches_unique_df["Leads Assigned"].astype(int)

                    # Dynamic source columns (Assigned): ps_name exists AND source == value (per branch)
                    if "source" in df_lm_filtered.columns:
                        source_clean_upper_assigned = df_lm_filtered["source"].fillna("").astype(str).str.strip().str.upper()
                        unique_sources_assigned = sorted(source_clean_upper_assigned[source_clean_upper_assigned != ""].unique().tolist())
                        for src in unique_sources_assigned:
                            src_mask_assigned = source_clean_upper_assigned == src
                            src_counts_assigned = (
                                branch_clean[ps_exists & src_mask_assigned]
                                .value_counts()
                                .rename_axis("Branch")
                                .reset_index(name=src)
                            )
                            branches_unique_df = (
                                branches_unique_df
                                .merge(src_counts_assigned, on="Branch", how="left")
                                .fillna({src: 0})
                            )
                            branches_unique_df[src] = branches_unique_df[src].astype(int)

                # Dynamic source columns: for each unique source value, count rows where
                # source == that value AND final_status == "Won" (per branch)
                if "source" in df_lm_filtered.columns:
                    source_clean_upper = df_lm_filtered["source"].fillna("").astype(str).str.strip().str.upper()
                    final_status_clean = df_lm_filtered.get("final_status", pd.Series(dtype=object)).fillna("").astype(str).str.strip().str.lower()
                    unique_sources = sorted(source_clean_upper[source_clean_upper != ""].unique().tolist())
                    for src in unique_sources:
                        src_mask = source_clean_upper == src
                        retailed_mask = src_mask & (final_status_clean == "won")
                        src_counts = (
                            branch_clean[retailed_mask]
                            .value_counts()
                            .rename_axis("Branch")
                            .reset_index(name=f"{src}(R)")
                        )
                        branches_unique_df = (
                            branches_unique_df
                            .merge(src_counts, on="Branch", how="left")
                            .fillna({f"{src}(R)": 0})
                        )
                        branches_unique_df[f"{src}(R)"] = branches_unique_df[f"{src}(R)"].astype(int)

                # Create percentage columns per source: {SRC}(%) = {SRC}(R) / {SRC} * 100
                try:
                    src_list_for_pct = (
                        df_lm_filtered["source"].fillna("").astype(str).str.strip().str.upper()
                    )
                    src_list_for_pct = sorted([s for s in src_list_for_pct.unique().tolist() if s != ""])
                    for src in src_list_for_pct:
                        base_col = src
                        retailed_col = f"{src}(R)"
                        pct_col = f"{src}(%)"
                        if base_col in branches_unique_df.columns and retailed_col in branches_unique_df.columns:
                            branches_unique_df[pct_col] = branches_unique_df.apply(
                                lambda r: (r[retailed_col] / r[base_col] * 100.0) if r[base_col] else 0.0,
                                axis=1,
                            )
                            branches_unique_df[pct_col] = branches_unique_df[pct_col].round(2)
                except Exception:
                    pass

                # Reorder columns so each source is followed by its (R) and (%) columns,
                # and sort source groups by total base counts descending
                try:
                    src_candidates_series = (
                        df_lm_filtered["source"].fillna("").astype(str).str.strip().str.upper()
                    )
                    src_candidates = [s for s in src_candidates_series.unique().tolist() if s != ""]
                    # Sort by total counts in base columns (descending)
                    reorder_sources = sorted(
                        src_candidates,
                        key=lambda s: (int(branches_unique_df[s].sum()) if s in branches_unique_df.columns else 0),
                        reverse=True,
                    )
                    ordered_cols = []
                    if "Leads Assigned" in branches_unique_df.columns:
                        ordered_cols.append("Leads Assigned")
                    for src in reorder_sources:
                        if src in branches_unique_df.columns:
                            ordered_cols.append(src)
                        retailed_col = f"{src}(R)"
                        if retailed_col in branches_unique_df.columns:
                            ordered_cols.append(retailed_col)
                        pct_col = f"{src}(%)"
                        if pct_col in branches_unique_df.columns:
                            ordered_cols.append(pct_col)
                    other_cols = [c for c in branches_unique_df.columns if c not in (["Branch"] + ordered_cols)]
                    branches_unique_df = branches_unique_df[["Branch"] + ordered_cols + other_cols]
                except Exception:
                    pass

                # Append TOTAL row summing numeric columns
                count_cols_lb = [
                    c for c in branches_unique_df.columns
                    if c != "Branch" and not c.endswith("(%") and not c.endswith("(%)")
                ]
                if count_cols_lb:
                    totals_map_lb = {c: int(branches_unique_df[c].sum()) for c in count_cols_lb}
                    total_row_lb = pd.DataFrame([{**{"Branch": "TOTAL"}, **totals_map_lb}])
                    branches_unique_df = pd.concat([branches_unique_df, total_row_lb], ignore_index=True)
                    # Compute TOTAL row percentages after counts are summed
                    try:
                        for src in reorder_sources:
                            base_col = src
                            retailed_col = f"{src}(R)"
                            pct_col = f"{src}(%)"
                            if base_col in branches_unique_df.columns and retailed_col in branches_unique_df.columns:
                                base_total = branches_unique_df.loc[branches_unique_df["Branch"] == "TOTAL", base_col].values
                                retailed_total = branches_unique_df.loc[branches_unique_df["Branch"] == "TOTAL", retailed_col].values
                                if len(base_total) and len(retailed_total):
                                    pct_val = (float(retailed_total[0]) / float(base_total[0]) * 100.0) if float(base_total[0]) else 0.0
                                    branches_unique_df.loc[branches_unique_df["Branch"] == "TOTAL", pct_col] = round(pct_val, 2)
                    except Exception:
                        pass

                display_lb = branches_unique_df.set_index("Branch")
                # Style: faintly color groups of columns per source (SRC, SRC(R), SRC(%))
                try:
                    source_names_for_style = (
                        df_lm_filtered["source"].fillna("").astype(str).str.strip().str.upper()
                    )
                    source_names_for_style = [s for s in sorted(source_names_for_style.unique().tolist()) if s != ""]
                    palette = [
                        "rgba(65,157,120,0.08)",   # green
                        "rgba(59,130,246,0.08)",   # blue
                        "rgba(234,179,8,0.10)",    # amber
                        "rgba(251,146,60,0.10)",   # orange
                        "rgba(168,85,247,0.08)",   # purple
                        "rgba(244,114,182,0.10)",  # pink
                        "rgba(107,114,128,0.08)",  # gray
                    ]
                    col_to_color = {}
                    for idx, src in enumerate(source_names_for_style):
                        group_cols = [src, f"{src}(R)", f"{src}(%)"]
                        existing_cols = [c for c in group_cols if c in display_lb.columns]
                        if existing_cols:
                            color = palette[idx % len(palette)]
                            for c in existing_cols:
                                col_to_color[c] = color

                    def _highlight_column(col_series):
                        color = col_to_color.get(col_series.name, "")
                        if color:
                            return [f"background-color: {color}"] * len(col_series)
                        return [""] * len(col_series)

                    styled_dl = display_lb.style.apply(_highlight_column, axis=0)
                    # Ensure percentage columns display with 2 decimals when styled
                    pct_cols = [c for c in display_lb.columns if c.endswith("(%)")]
                    if pct_cols:
                        styled_dl = styled_dl.format({c: "{:.2f}" for c in pct_cols})
                    st.dataframe(styled_dl, use_container_width=True, hide_index=False)
                except Exception:
                    st.dataframe(display_lb, use_container_width=True, hide_index=False)

                # Compute PS Untouched per branch (from ps_followup_master) using global Admin date filter
                try:
                    ps_overall_res = (
                        supabase
                        .table("ps_followup_master")
                        .select("ps_branch", "ps_assigned_at", "final_status", "lead_status", "first_call_date", "ps_name")
                        .execute()
                    )
                    df_ps_overall = pd.DataFrame(ps_overall_res.data)
                    if not df_ps_overall.empty:
                        # Apply admin/global date filter on ps_assigned_at
                        if (
                            filter_option_admin != "All time"
                            and start_dt_admin is not None
                            and end_dt_admin is not None
                            and "ps_assigned_at" in df_ps_overall.columns
                        ):
                            ts_ps_all = pd.to_datetime(df_ps_overall["ps_assigned_at"], errors="coerce", utc=True)
                            mask_ps_all = ts_ps_all.between(start_dt_admin, end_dt_admin)
                            df_ps_overall = df_ps_overall.loc[mask_ps_all].copy()

                        # Clean branch names to align with branches_unique_df
                        branch_clean_ps = (
                            df_ps_overall.get("ps_branch", pd.Series(dtype=object))
                            .fillna("")
                            .astype(str)
                            .str.strip()
                            .replace("", "Unknown")
                        )

                        # Untouched mask per PS logic
                        lead_status_ps = df_ps_overall.get("lead_status", pd.Series(dtype=object))
                        final_status_ps = df_ps_overall.get("final_status", pd.Series(dtype=object))
                        first_call_ps = df_ps_overall.get("first_call_date", pd.Series(dtype=object))

                        exclude_statuses = [
                            'Lost to Codealer', 'Lost to Competition', 'Dropped', 'Booked', 'Retailed',
                            'Call me Back', 'RNR', 'Busy on another Call', 'Call Disconnected', 'Call not Connected'
                        ]
                        untouched_mask_ps = (
                            (final_status_ps.fillna("Pending").astype(str).str.strip().str.lower().isin(["pending"]))
                            | (final_status_ps.isna())
                        ) & (first_call_ps.isna()) & (
                            lead_status_ps.isna() | (~lead_status_ps.astype(str).isin(exclude_statuses))
                        )

                        df_untouched_ps = (
                            branch_clean_ps[untouched_mask_ps]
                            .value_counts()
                            .rename_axis("Branch")
                            .reset_index(name="Untouched")
                        )

                        # Merge into branches summary table
                        branches_unique_df = (
                            branches_unique_df
                            .merge(df_untouched_ps, on="Branch", how="left")
                            .fillna({"Untouched": 0})
                        )
                        branches_unique_df["Untouched"] = branches_unique_df["Untouched"].astype(int)

                        # Compute Open Leads per branch by summing PS-level open leads logic
                        # Build mapping Branch -> PS list
                        branch_to_ps_df = pd.DataFrame({
                            "Branch": branch_clean_ps,
                            "PS": df_ps_overall.get("ps_name", pd.Series(dtype=object)).astype(str)
                        })
                        unique_branches_list = branches_unique_df["Branch"].tolist()
                        open_leads_values = []
                        won_values = []
                        lost_values = []
                        for br in unique_branches_list:
                            try:
                                ps_list = (
                                    branch_to_ps_df[branch_to_ps_df["Branch"].fillna("").astype(str).str.strip().replace("", "Unknown") == br]["PS"]
                                    .dropna()
                                    .astype(str)
                                    .str.strip()
                                    .tolist()
                                )
                                ps_list = [p for p in ps_list if p and p.lower() != "unassigned ps"]
                                total_open = 0
                                total_won = 0
                                if ps_list:
                                    # walkin_table Pending by ps_assigned in ps_list
                                    try:
                                        q_w = (
                                            supabase
                                            .table("walkin_table")
                                            .select("id", count="exact")
                                            .eq("status", "Pending")
                                        )
                                        try:
                                            r_w = q_w.in_("ps_assigned", ps_list).execute()
                                            total_open += int(r_w.count or 0)
                                        except Exception:
                                            subtotal = 0
                                            for psn in ps_list:
                                                r_wl = q_w.eq("ps_assigned", psn).execute()
                                                subtotal += int(r_wl.count or 0)
                                                q_w = (
                                                    supabase
                                                    .table("walkin_table")
                                                    .select("id", count="exact")
                                                    .eq("status", "Pending")
                                                )
                                            total_open += subtotal
                                    except Exception:
                                        pass

                                    # ps_followup_master Pending with first_call_date not null
                                    try:
                                        q_p = (
                                            supabase
                                            .table("ps_followup_master")
                                            .select("id", count="exact")
                                            .eq("final_status", "Pending")
                                            .not_.is_("first_call_date", "null")
                                        )
                                        try:
                                            r_p = q_p.in_("ps_name", ps_list).execute()
                                            total_open += int(r_p.count or 0)
                                        except Exception:
                                            subtotal = 0
                                            for psn in ps_list:
                                                r_pl = q_p.eq("ps_name", psn).execute()
                                                subtotal += int(r_pl.count or 0)
                                                q_p = (
                                                    supabase
                                                    .table("ps_followup_master")
                                                    .select("id", count="exact")
                                                    .eq("final_status", "Pending")
                                                    .not_.is_("first_call_date", "null")
                                                )
                                            total_open += subtotal
                                    except Exception:
                                        pass

                                    # activity_leads Pending with ps_first_call_date not null
                                    try:
                                        q_a = (
                                            supabase
                                            .table("activity_leads")
                                            .select("id", count="exact")
                                            .eq("final_status", "Pending")
                                            .not_.is_("ps_first_call_date", "null")
                                        )
                                        try:
                                            r_a = q_a.in_("ps_name", ps_list).execute()
                                            total_open += int(r_a.count or 0)
                                        except Exception:
                                            subtotal = 0
                                            for psn in ps_list:
                                                r_al = q_a.eq("ps_name", psn).execute()
                                                subtotal += int(r_al.count or 0)
                                                q_a = (
                                                    supabase
                                                    .table("activity_leads")
                                                    .select("id", count="exact")
                                                    .eq("final_status", "Pending")
                                                    .not_.is_("ps_first_call_date", "null")
                                                )
                                            total_open += subtotal
                                    except Exception:
                                        pass

                                    # Won across three sources for PS list
                                    # walkin_table Won
                                    try:
                                        q_ww = (
                                            supabase
                                            .table("walkin_table")
                                            .select("id", count="exact")
                                            .eq("status", "Won")
                                        )
                                        # Apply date filter for non-"All time" using updated_at
                                        if filter_option_ps != "All time" and start_dt_ps is not None and end_dt_ps is not None:
                                            q_ww = q_ww.gte("updated_at", start_dt_ps.isoformat()).lte("updated_at", end_dt_ps.isoformat())
                                        try:
                                            r_ww = q_ww.in_("ps_assigned", ps_list).execute()
                                            total_won += int(r_ww.count or 0)
                                        except Exception:
                                            subtotal = 0
                                            for psn in ps_list:
                                                q_ww_each = q_ww.eq("ps_assigned", psn)
                                                r_wwl = q_ww_each.execute()
                                                subtotal += int(r_wwl.count or 0)
                                                q_ww = (
                                                    supabase
                                                    .table("walkin_table")
                                                    .select("id", count="exact")
                                                    .eq("status", "Won")
                                                )
                                                if filter_option_ps != "All time" and start_dt_ps is not None and end_dt_ps is not None:
                                                    q_ww = q_ww.gte("updated_at", start_dt_ps.isoformat()).lte("updated_at", end_dt_ps.isoformat())
                                            total_won += subtotal
                                    except Exception:
                                        pass

                                    # ps_followup_master Won
                                    try:
                                        q_pw = (
                                            supabase
                                            .table("ps_followup_master")
                                            .select("id", count="exact")
                                            .eq("final_status", "Won")
                                        )
                                        # Apply date filter for non-"All time" using won_timestamp
                                        if filter_option_ps != "All time" and start_dt_ps is not None and end_dt_ps is not None:
                                            q_pw = q_pw.gte("won_timestamp", start_dt_ps.isoformat()).lte("won_timestamp", end_dt_ps.isoformat())
                                        try:
                                            r_pw = q_pw.in_("ps_name", ps_list).execute()
                                            total_won += int(r_pw.count or 0)
                                        except Exception:
                                            subtotal = 0
                                            for psn in ps_list:
                                                q_pw_each = q_pw.eq("ps_name", psn)
                                                r_pwl = q_pw_each.execute()
                                                subtotal += int(r_pwl.count or 0)
                                                q_pw = (
                                                    supabase
                                                    .table("ps_followup_master")
                                                    .select("id", count="exact")
                                                    .eq("final_status", "Won")
                                                )
                                                if filter_option_ps != "All time" and start_dt_ps is not None and end_dt_ps is not None:
                                                    q_pw = q_pw.gte("won_timestamp", start_dt_ps.isoformat()).lte("won_timestamp", end_dt_ps.isoformat())
                                            total_won += subtotal
                                    except Exception:
                                        pass

                                    # activity_leads Won
                                    try:
                                        q_aw = (
                                            supabase
                                            .table("activity_leads")
                                            .select("id", count="exact")
                                            .eq("final_status", "Won")
                                        )
                                        # Apply date filter for non-"All time" using created_at
                                        if filter_option_ps != "All time" and start_dt_ps is not None and end_dt_ps is not None:
                                            q_aw = q_aw.gte("created_at", start_dt_ps.isoformat()).lte("created_at", end_dt_ps.isoformat())
                                        try:
                                            r_aw = q_aw.in_("ps_name", ps_list).execute()
                                            total_won += int(r_aw.count or 0)
                                        except Exception:
                                            subtotal = 0
                                            for psn in ps_list:
                                                q_aw_each = q_aw.eq("ps_name", psn)
                                                r_awl = q_aw_each.execute()
                                                subtotal += int(r_awl.count or 0)
                                                q_aw = (
                                                    supabase
                                                    .table("activity_leads")
                                                    .select("id", count="exact")
                                                    .eq("final_status", "Won")
                                                )
                                                if filter_option_ps != "All time" and start_dt_ps is not None and end_dt_ps is not None:
                                                    q_aw = q_aw.gte("created_at", start_dt_ps.isoformat()).lte("created_at", end_dt_ps.isoformat())
                                            total_won += subtotal
                                    except Exception:
                                        pass

                                    # Lost across three sources for PS list
                                    # walkin_table Lost
                                    try:
                                        q_wl = (
                                            supabase
                                            .table("walkin_table")
                                            .select("id", count="exact")
                                            .eq("status", "Lost")
                                        )
                                        # Apply date filter for non-"All time" using updated_at
                                        if filter_option_ps != "All time" and start_dt_ps is not None and end_dt_ps is not None:
                                            q_wl = q_wl.gte("updated_at", start_dt_ps.isoformat()).lte("updated_at", end_dt_ps.isoformat())
                                        try:
                                            r_wl_many = q_wl.in_("ps_assigned", ps_list).execute()
                                            lost_branch = int(r_wl_many.count or 0)
                                        except Exception:
                                            lost_branch = 0
                                            for psn in ps_list:
                                                q_wl_each = q_wl.eq("ps_assigned", psn)
                                                r_wll = q_wl_each.execute()
                                                lost_branch += int(r_wll.count or 0)
                                                q_wl = (
                                                    supabase
                                                    .table("walkin_table")
                                                    .select("id", count="exact")
                                                    .eq("status", "Lost")
                                                )
                                                if filter_option_ps != "All time" and start_dt_ps is not None and end_dt_ps is not None:
                                                    q_wl = q_wl.gte("updated_at", start_dt_ps.isoformat()).lte("updated_at", end_dt_ps.isoformat())
                                    except Exception:
                                        lost_branch = 0

                                    # ps_followup_master Lost
                                    try:
                                        q_pl = (
                                            supabase
                                            .table("ps_followup_master")
                                            .select("id", count="exact")
                                            .eq("final_status", "Lost")
                                        )
                                        # Apply date filter for non-"All time" using won_timestamp (as requested)
                                        if filter_option_ps != "All time" and start_dt_ps is not None and end_dt_ps is not None:
                                            q_pl = q_pl.gte("won_timestamp", start_dt_ps.isoformat()).lte("won_timestamp", end_dt_ps.isoformat())
                                        try:
                                            r_pl_many = q_pl.in_("ps_name", ps_list).execute()
                                            lost_branch += int(r_pl_many.count or 0)
                                        except Exception:
                                            for psn in ps_list:
                                                q_pl_each = q_pl.eq("ps_name", psn)
                                                r_pll = q_pl_each.execute()
                                                lost_branch += int(r_pll.count or 0)
                                                q_pl = (
                                                    supabase
                                                    .table("ps_followup_master")
                                                    .select("id", count="exact")
                                                    .eq("final_status", "Lost")
                                                )
                                                if filter_option_ps != "All time" and start_dt_ps is not None and end_dt_ps is not None:
                                                    q_pl = q_pl.gte("won_timestamp", start_dt_ps.isoformat()).lte("won_timestamp", end_dt_ps.isoformat())
                                    except Exception:
                                        pass

                                    # activity_leads Lost
                                    try:
                                        q_al = (
                                            supabase
                                            .table("activity_leads")
                                            .select("id", count="exact")
                                            .eq("final_status", "Lost")
                                        )
                                        # Apply date filter for non-"All time" using created_at
                                        if filter_option_ps != "All time" and start_dt_ps is not None and end_dt_ps is not None:
                                            q_al = q_al.gte("created_at", start_dt_ps.isoformat()).lte("created_at", end_dt_ps.isoformat())
                                        try:
                                            r_al_many = q_al.in_("ps_name", ps_list).execute()
                                            lost_branch += int(r_al_many.count or 0)
                                        except Exception:
                                            for psn in ps_list:
                                                q_al_each = q_al.eq("ps_name", psn)
                                                r_all = q_al_each.execute()
                                                lost_branch += int(r_all.count or 0)
                                                q_al = (
                                                    supabase
                                                    .table("activity_leads")
                                                    .select("id", count="exact")
                                                    .eq("final_status", "Lost")
                                                )
                                                if filter_option_ps != "All time" and start_dt_ps is not None and end_dt_ps is not None:
                                                    q_al = q_al.gte("created_at", start_dt_ps.isoformat()).lte("created_at", end_dt_ps.isoformat())
                                    except Exception:
                                        pass
                                else:
                                    lost_branch = 0
                                open_leads_values.append(int(total_open))
                                won_values.append(int(total_won))
                                lost_values.append(int(lost_branch))
                            except Exception:
                                open_leads_values.append(0)
                                won_values.append(0)
                                lost_values.append(0)

                        branches_unique_df = branches_unique_df.merge(
                            pd.DataFrame({"Branch": unique_branches_list, "Open Leads": open_leads_values, "Won": won_values, "Lost": lost_values}),
                            on="Branch",
                            how="left",
                        )
                        branches_unique_df["Open Leads"] = branches_unique_df["Open Leads"].fillna(0).astype(int)
                        branches_unique_df["Won"] = branches_unique_df["Won"].fillna(0).astype(int)
                        branches_unique_df["Lost"] = branches_unique_df["Lost"].fillna(0).astype(int)
                except Exception:
                    pass

                # Right column: Branch-only table
                with _dl_right:
                    st.subheader("Branches")
                    st.caption("Note: values in Won and Lost columns may differ as it is under development.")
                    try:
                        cols_to_show = [c for c in ["Branch", "Leads Assigned", "Untouched", "Open Leads", "Won", "Lost"] if c in branches_unique_df.columns]
                        if cols_to_show:
                            st.dataframe(branches_unique_df[cols_to_show], use_container_width=True, hide_index=True)
                        else:
                            st.dataframe(branches_unique_df[["Branch"]], use_container_width=True, hide_index=True)
                    except Exception:
                        st.dataframe(pd.DataFrame({"Branch": []}), use_container_width=True, hide_index=True)
            else:
                st.info("No branch data available for the selected range.")
        except Exception as err:
            st.warning(f"Could not load branches from lead_master: {err}")

    # (PS Performance moved to the PS Performance tab)

with tab2:
    # PS Performance (standalone tab), date filter based on ps_assigned_at
    try:
        ps_res = (
            supabase
            .table("ps_followup_master")
            .select("ps_name", "ps_branch", "ps_assigned_at")
            .execute()
        )
        df_ps = pd.DataFrame(ps_res.data)

        # Use global date filter values; apply on ps_assigned_at
        filter_option_ps = filter_option_global
        start_dt_ps, end_dt_ps = start_dt_global, end_dt_global

        df_ps_filtered = df_ps.copy()
        if filter_option_ps != "All time" and start_dt_ps is not None and end_dt_ps is not None:
            if not df_ps.empty and "ps_assigned_at" in df_ps.columns:
                ps_assigned_ts = pd.to_datetime(df_ps["ps_assigned_at"], errors="coerce", utc=True)
                mask_ps = ps_assigned_ts.between(start_dt_ps, end_dt_ps)
                df_ps_filtered = df_ps.loc[mask_ps].copy()

        # Branch filter dropdown (from filtered data) in header
        if not df_ps_filtered.empty and "ps_branch" in df_ps_filtered.columns:
            branches = (
                pd.Series(sorted(df_ps_filtered["ps_branch"].fillna("").astype(str).str.strip().replace("", "Unknown").unique()))
                .tolist()
            )
        else:
            branches = []

        branch_options = ["All"] + branches if branches else ["All"]
        ps_left_col, _ps_right_col = st.columns([0.5, 0.5])
        with ps_left_col:
            title_col, filter_col = st.columns([0.5, 0.5])
            with title_col:
                st.subheader("PS Performance")
                st.caption("Note: values in Won and Lost columns may differ as it is under development.")
            with filter_col:
                selected_branch = st.selectbox("Branch", options=branch_options, index=0, key="ps_branch_filter", label_visibility="collapsed")

        # Apply branch selection
        df_ps_branch = df_ps_filtered.copy()
        if selected_branch != "All":
            df_ps_branch = df_ps_branch[df_ps_branch["ps_branch"].fillna("").astype(str).str.strip().replace("", "Unknown") == selected_branch]

        # Build PS table: PS, Assigned, Untouched, and Pending counts
        if not df_ps_branch.empty and "ps_name" in df_ps_branch.columns:
            ps_series = df_ps_branch["ps_name"].fillna("").astype(str).str.strip().replace("", "Unassigned PS")
            assigned_df = (
                ps_series.value_counts().rename_axis("PS").reset_index(name="Assigned")
            )
            
            # Calculate untouched leads for each PS
            untouched_counts = []
            pending_counts = []
            won_counts = []
            lost_counts = []
            for ps_name in assigned_df["PS"]:
                if ps_name == "Unassigned PS":
                    untouched_counts.append(0)
                    pending_counts.append(0)
                    won_counts.append(0)
                    lost_counts.append(0)
                    continue
                
                try:
                    # Query untouched leads for this PS from ps_followup_master
                    untouched_query = (
                        supabase
                        .table("ps_followup_master")
                        .select("lead_uid", "final_status", "lead_status", "first_call_date")
                        .eq("ps_name", ps_name)
                    )
                    
                    # Apply date filter if not "All time"
                    if filter_option_ps != "All time" and start_dt_ps is not None and end_dt_ps is not None:
                        untouched_query = untouched_query.gte("ps_assigned_at", start_dt_ps.isoformat()).lte("ps_assigned_at", end_dt_ps.isoformat())
                    
                    untouched_res = untouched_query.execute()
                    untouched_data = pd.DataFrame(untouched_res.data)
                    
                    if not untouched_data.empty:
                        # Filter for untouched leads
                        untouched_mask = (
                            (untouched_data["final_status"] == "Pending") | 
                            (untouched_data["final_status"].isna())
                        ) & (
                            untouched_data["first_call_date"].isna()
                        ) & (
                            (untouched_data["lead_status"].isna()) | 
                            (~untouched_data["lead_status"].isin([
                                'Lost to Codealer', 'Lost to Competition', 'Dropped', 'Booked', 'Retailed',
                                'Call me Back', 'RNR', 'Busy on another Call', 'Call Disconnected', 'Call not Connected'
                            ]))
                        )
                        untouched_count = int(untouched_mask.sum())
                    else:
                        untouched_count = 0
                    
                    # Compute Pending count across three sources for this PS
                    pending_total = 0
                    # 1) walkin_table: status Pending AND ps_assigned = ps_name
                    try:
                        r_walkin_pending = (
                            supabase
                            .table("walkin_table")
                            .select("id", count="exact")
                            .eq("status", "Pending")
                            .eq("ps_assigned", ps_name)
                            .execute()
                        )
                        pending_total += int(r_walkin_pending.count or 0)
                    except Exception:
                        pass

                    # 2) ps_followup_master: final_status Pending AND first_call_date IS NOT NULL AND ps_name = ps_name
                    try:
                        r_ps_pending = (
                            supabase
                            .table("ps_followup_master")
                            .select("id", count="exact")
                            .eq("final_status", "Pending")
                            .eq("ps_name", ps_name)
                            .not_.is_("first_call_date", "null")
                            .execute()
                        )
                        pending_total += int(r_ps_pending.count or 0)
                    except Exception:
                        pass

                    # 3) activity_leads: final_status Pending AND ps_first_call_date IS NOT NULL AND ps_name = ps_name
                    try:
                        r_act_pending = (
                            supabase
                            .table("activity_leads")
                            .select("id", count="exact")
                            .eq("ps_name", ps_name)
                            .eq("final_status", "Pending")
                            .not_.is_("ps_first_call_date", "null")
                            .execute()
                        )
                        pending_total += int(r_act_pending.count or 0)
                    except Exception:
                        pass

                    # Compute Won count across three sources for this PS
                    won_total = 0
                    # 1) walkin_table: status Won AND ps_assigned = ps_name
                    try:
                        r_walkin_won = (
                            supabase
                            .table("walkin_table")
                            .select("id", count="exact")
                            .eq("status", "Won")
                            .eq("ps_assigned", ps_name)
                            .execute()
                        )
                        won_total += int(r_walkin_won.count or 0)
                    except Exception:
                        pass

                    # 2) ps_followup_master: final_status Won AND ps_name = ps_name
                    try:
                        r_ps_won = (
                            supabase
                            .table("ps_followup_master")
                            .select("id", count="exact")
                            .eq("final_status", "Won")
                            .eq("ps_name", ps_name)
                            .execute()
                        )
                        won_total += int(r_ps_won.count or 0)
                    except Exception:
                        pass

                    # 3) activity_leads: final_status Won AND ps_name = ps_name
                    try:
                        r_act_won = (
                            supabase
                            .table("activity_leads")
                            .select("id", count="exact")
                            .eq("ps_name", ps_name)
                            .eq("final_status", "Won")
                            .execute()
                        )
                        won_total += int(r_act_won.count or 0)
                    except Exception:
                        pass

                    # Compute Lost count across three sources for this PS
                    lost_total = 0
                    # 1) walkin_table: status Lost AND ps_assigned = ps_name
                    try:
                        r_walkin_lost = (
                            supabase
                            .table("walkin_table")
                            .select("id", count="exact")
                            .eq("status", "Lost")
                            .eq("ps_assigned", ps_name)
                            .execute()
                        )
                        lost_total += int(r_walkin_lost.count or 0)
                    except Exception:
                        pass

                    # 2) ps_followup_master: final_status Lost AND ps_name = ps_name
                    try:
                        r_ps_lost = (
                            supabase
                            .table("ps_followup_master")
                            .select("id", count="exact")
                            .eq("final_status", "Lost")
                            .eq("ps_name", ps_name)
                            .execute()
                        )
                        lost_total += int(r_ps_lost.count or 0)
                    except Exception:
                        pass

                    # 3) activity_leads: final_status Lost AND ps_name = ps_name
                    try:
                        r_act_lost = (
                            supabase
                            .table("activity_leads")
                            .select("id", count="exact")
                            .eq("ps_name", ps_name)
                            .eq("final_status", "Lost")
                            .execute()
                        )
                        lost_total += int(r_act_lost.count or 0)
                    except Exception:
                        pass
                    
                except Exception as e:
                    st.write(f"Error calculating untouched for {ps_name}: {e}")
                    untouched_count = 0
                    pending_total = 0
                    won_total = 0
                    lost_total = 0
                
                untouched_counts.append(untouched_count)
                pending_counts.append(pending_total)
                won_counts.append(won_total)
                lost_counts.append(lost_total)
            
            assigned_df["Untouched"] = untouched_counts
            assigned_df["Open Leads"] = pending_counts
            assigned_df["Won"] = won_counts
            assigned_df["Lost"] = lost_counts
            assigned_df = assigned_df.sort_values(["Assigned", "PS"], ascending=[False, True])

            total_assigned = int(assigned_df["Assigned"].sum()) if not assigned_df.empty else 0
            total_untouched = int(assigned_df["Untouched"].sum()) if not assigned_df.empty else 0
            total_pending = int(assigned_df["Open Leads"].sum()) if not assigned_df.empty else 0
            total_won = int(assigned_df["Won"].sum()) if not assigned_df.empty else 0
            total_lost = int(assigned_df["Lost"].sum()) if not assigned_df.empty else 0
            total_row_ps = pd.DataFrame({"PS": ["TOTAL"], "Assigned": [total_assigned], "Untouched": [total_untouched], "Open Leads": [total_pending], "Won": [total_won], "Lost": [total_lost]})
            assigned_df_display = pd.concat([assigned_df, total_row_ps], ignore_index=True)

            total_rows_ps = int(len(assigned_df_display)) + 1
            row_px_ps = 34
            header_px_ps = 38
            padding_px_ps = 12
            height_ps = header_px_ps + row_px_ps * total_rows_ps + padding_px_ps
            with ps_left_col:
                st.dataframe(assigned_df_display, use_container_width=True, height=height_ps, hide_index=True)
        else:
            st.info("No PS records available for the selected range/branch.")
    except Exception as err:
        st.warning(f"Could not load PS Performance data: {err}")

with tab3:
    st.subheader("CRE Performance")
    cre_tab_left, _cre_tab_right = st.columns([0.5, 0.5])
    try:
        cre_res = (
            supabase
            .table("lead_master")
            .select("cre_name", "created_at", "lead_status", "first_call_date", "final_status", "tat", "ps_name")
            .execute()
        )
        df_cre = pd.DataFrame(cre_res.data)

        # Apply global date filter (same as KPIs)
        df_cre_filtered = df_cre.copy()
        if filter_option_global != "All time" and start_dt_global is not None and end_dt_global is not None:
            if not df_cre.empty and "created_at" in df_cre.columns:
                created_ts_cre = pd.to_datetime(df_cre["created_at"], errors="coerce", utc=True)
                mask_cre = created_ts_cre.between(start_dt_global, end_dt_global)
                df_cre_filtered = df_cre.loc[mask_cre].copy()

        if not df_cre_filtered.empty and "cre_name" in df_cre_filtered.columns:
            cre_series = (
                df_cre_filtered["cre_name"].fillna("").astype(str).str.strip().replace("", "Unassigned Leads")
            )
            lead_status_series = df_cre_filtered.get("lead_status", pd.Series(dtype=object)).fillna("").astype(str).str.strip().str.lower()
            final_status_series = df_cre_filtered.get("final_status", pd.Series(dtype=object)).fillna("").astype(str).str.strip().str.lower()
            first_call_clean = df_cre_filtered.get("first_call_date", pd.Series(dtype=object)).fillna("").astype(str).str.strip()
            final_status_is_null = df_cre_filtered["final_status"].isna() if "final_status" in df_cre_filtered.columns else pd.Series(False, index=df_cre_filtered.index)

            touched_statuses = {"rnr", "busy on another call", "call disconnected", "call not connected"}
            touched_mask = (
                lead_status_series.isin(touched_statuses)
                & (first_call_clean == "")
                & (final_status_series == "pending")
            )
            ut_mask = (
                (first_call_clean == "")
                & (lead_status_series == "pending")
                & ((final_status_series == "pending") | (final_status_is_null))
            )
            followup_mask = (
                (first_call_clean == "")
                & (lead_status_series == "call me back")
                & ((final_status_series == "pending") | (final_status_is_null))
            )
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
            df_tmp_valid = df_tmp[df_tmp["CRE"] != "Unassigned Leads"].copy()
            agg_counts = (
                df_tmp_valid
                .groupby("CRE")[ ["touched_flag", "ut_flag", "followup_flag", "open_flag"] ]
                .sum()
                .astype(int)
                .reset_index()
                .rename(columns={"touched_flag": "Touched", "ut_flag": "Untouched", "followup_flag": "Followup", "open_flag": "Open leads"})
            )
            assigned_counts = (
                df_tmp_valid
                .groupby("CRE")
                .size()
                .reset_index(name="Assigned")
            )

            # QL: count of rows where ps_name exists for each CRE (within filtered range)
            # Build a mask aligned with df_cre_filtered index for rows where ps_name exists
            if "ps_name" in df_cre_filtered.columns:
                ps_series_raw = df_cre_filtered["ps_name"]
            else:
                ps_series_raw = pd.Series([""] * len(df_cre_filtered), index=df_cre_filtered.index)
            ps_exists_mask = ps_series_raw.notna() & (ps_series_raw.astype(str).str.strip() != "")
            cre_norm_for_ql = (
                df_cre_filtered["cre_name"].fillna("").astype(str).str.strip().replace("", "Unassigned Leads")
            )
            ql_counts = (
                cre_norm_for_ql[ps_exists_mask]
                .value_counts()
                .rename_axis("CRE")
                .reset_index(name="Quality Leads")
            )

            df_status = pd.DataFrame({
                "CRE": cre_series,
                "final_status_clean": final_status_series,
            })
            df_status_valid = df_status[df_status["CRE"] != "Unassigned Leads"].copy()
            won_counts_status = (
                df_status_valid[df_status_valid["final_status_clean"] == "won"].groupby("CRE").size().reset_index(name="Retailed")
            )
            lost_counts_status = (
                df_status_valid[df_status_valid["final_status_clean"] == "lost"].groupby("CRE").size().reset_index(name="Lost")
            )

            tat_series_raw = pd.to_numeric(df_cre_filtered.get("tat", pd.Series(dtype=float)), errors="coerce")
            df_tat = pd.DataFrame({"CRE": cre_series, "tat_sec": tat_series_raw})
            df_tat_valid = df_tat[(df_tat["CRE"] != "Unassigned Leads") & (df_tat["tat_sec"].notna())].copy()
            tat_avg_map = df_tat_valid.groupby("CRE")["tat_sec"].mean() if not df_tat_valid.empty else pd.Series(dtype=float)

            cre_names = pd.Series(sorted(df_tmp_valid["CRE"].unique())).rename("CRE").to_frame()
            cre_table = (
                cre_names
                .merge(agg_counts, on="CRE", how="left")
                .merge(assigned_counts, on="CRE", how="left")
                .merge(ql_counts, on="CRE", how="left")
                .merge(won_counts_status, on="CRE", how="left")
                .merge(lost_counts_status, on="CRE", how="left")
                .fillna({"Touched": 0, "UT": 0, "Followup": 0, "Open leads": 0, "Assigned": 0})
            )
            cre_table["Touched"] = cre_table["Touched"].astype(int)
            if "Untouched" in cre_table.columns:
                cre_table["Untouched"] = cre_table["Untouched"].astype(int)
            cre_table["Followup"] = cre_table["Followup"].astype(int)
            cre_table["Assigned"] = cre_table["Assigned"].astype(int)
            if "Quality Leads" in cre_table.columns:
                cre_table["Quality Leads"] = cre_table["Quality Leads"].fillna(0).astype(int)
            if "Open leads" in cre_table.columns:
                cre_table["Open leads"] = cre_table["Open leads"].astype(int)
            if "Retailed" in cre_table.columns:
                cre_table["Retailed"] = cre_table["Retailed"].fillna(0).astype(int)
            if "Lost" in cre_table.columns:
                cre_table["Lost"] = cre_table["Lost"].fillna(0).astype(int)

            tat_avg_df = tat_avg_map.rename("tat_avg_sec").reset_index() if not tat_avg_map.empty else pd.DataFrame({"CRE": [], "tat_avg_sec": []})
            cre_table = cre_table.merge(tat_avg_df, on="CRE", how="left")
            cre_table["tat_avg_sec"] = cre_table["tat_avg_sec"].fillna(0.0)

            def _format_tat(seconds: float) -> str:
                try:
                    s = float(seconds)
                except Exception:
                    return "0m"
                if s <= 0:
                    return "0m"
                if s < 3600:
                    return f"{s/60:.1f}m"
                if s < 86400:
                    return f"{s/3600:.1f}h"
                return f"{s/86400:.1f}d"

            cre_table["TAT(Avg)"] = cre_table["tat_avg_sec"].apply(_format_tat)

            desired_order_cols = [c for c in ["CRE", "Assigned", "Quality Leads", "Untouched", "Open leads", "Retailed", "Lost", "TAT(Avg)"] if c in cre_table.columns]
            cre_table = cre_table[desired_order_cols]
            if "Assigned" in cre_table.columns:
                cre_table = cre_table.sort_values("Assigned", ascending=False)

            numeric_cols = [c for c in ["Assigned", "Open leads", "Retailed", "Untouched", "Lost"] if c in cre_table.columns]
            total_values = {c: int(cre_table[c].sum()) for c in numeric_cols}
            total_row_dict = {**{"CRE": "TOTAL"}, **total_values}
            # Include Quality Leads in totals if present
            if "Quality Leads" in cre_table.columns:
                total_row_dict["Quality Leads"] = int(cre_table["Quality Leads"].sum())
            total_avg_tat_sec = float(df_tat_valid["tat_sec"].mean()) if not df_tat_valid.empty else 0.0
            total_row_dict["TAT(Avg)"] = _format_tat(total_avg_tat_sec)

            try:
                max_cre_len = int(cre_table["CRE"].astype(str).str.len().max()) if not cre_table.empty else 10
            except Exception:
                max_cre_len = 10
            per_char_px = 9
            index_padding_px = 80
            other_columns_px = 280
            desired_width = max(420, min(1200, per_char_px * max_cre_len + index_padding_px + other_columns_px))
            cre_table_with_total = pd.concat([cre_table, pd.DataFrame([total_row_dict])], ignore_index=True)
            total_rows = int(len(cre_table_with_total))
            row_px = 34
            header_px = 38
            padding_px = 12
            computed_height = header_px + row_px * total_rows + padding_px
            df_display = cre_table_with_total.set_index("CRE")
            try:
                highlight_css = "background-color: #419D78; color: #ffffff; font-weight: 600;"
                styled = df_display.style.apply(
                    lambda row: [highlight_css] * len(row) if str(row.name) == "TOTAL" else [""] * len(row),
                    axis=1,
                )
                with cre_tab_left:
                    st.dataframe(
                        styled,
                        use_container_width=True,
                        height=computed_height,
                        hide_index=False,
                    )
            except Exception:
                with cre_tab_left:
                    st.dataframe(
                        df_display,
                        use_container_width=True,
                        height=computed_height,
                        hide_index=False,
                    )
        else:
            st.info("No CRE data available to display.")
    except Exception as err:
        st.warning(f"Could not load CRE Performance data: {err}")