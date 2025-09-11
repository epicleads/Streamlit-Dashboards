import os
from dotenv import load_dotenv
from supabase import create_client, Client
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

st.title("🚶Analytics Dashboard")

# KPI cards (top): All in one row
col_kpi_1, col_kpi_2, col_kpi_3, col_kpi_4, col_kpi_5, col_kpi_6 = st.columns(6)
with col_kpi_1:
    try:
        # Define UTC time boundaries matching SQL semantics
        now_ts_kpi = pd.Timestamp.now(tz="UTC")
        month_start_kpi = pd.Timestamp(date.today().replace(day=1)).tz_localize("UTC")
        prev_month_start = month_start_kpi - pd.offsets.MonthBegin(1)

        # Query counts directly from DB to avoid client-side timezone differences
        mtd_resp = (
            supabase
            .table("lead_master")
            .select("id", count="exact")
            .gte("created_at", month_start_kpi.isoformat())
            .lt("created_at", now_ts_kpi.isoformat())
            .execute()
        )
        mtd_count = int(mtd_resp.count or 0)

        prev_resp = (
            supabase
            .table("lead_master")
            .select("id", count="exact")
            .gte("created_at", prev_month_start.isoformat())
            .lt("created_at", month_start_kpi.isoformat())
            .execute()
        )
        prev_count = int(prev_resp.count or 0)

        if prev_count == 0:
            delta_str = "+∞%" if mtd_count > 0 else "0%"
        else:
            pct_change = (mtd_count - prev_count) / prev_count * 100.0
            delta_str = f"{pct_change:+.1f}%"

        st.metric(label="Leads (MTD)", value=mtd_count, delta=delta_str)
    except Exception as err:
        st.warning(f"Could not load KPI (Leads MTD): {err}")

with col_kpi_2:
    try:
        now_ts_kpi2 = pd.Timestamp.now(tz="UTC")
        month_start_kpi2 = pd.Timestamp(date.today().replace(day=1)).tz_localize("UTC")
        prev_month_start2 = month_start_kpi2 - pd.offsets.MonthBegin(1)

        assigned_resp = (
            supabase
            .table("lead_master")
            .select("id", count="exact")
            .not_.is_("cre_name", "null")
            .gte("created_at", month_start_kpi2.isoformat())
            .lte("created_at", now_ts_kpi2.isoformat())
            .execute()
        )
        assigned_count = int(assigned_resp.count or 0)

        prev_assigned_resp = (
            supabase
            .table("lead_master")
            .select("id", count="exact")
            .not_.is_("cre_name", "null")
            .gte("created_at", prev_month_start2.isoformat())
            .lt("created_at", month_start_kpi2.isoformat())
            .execute()
        )
        prev_assigned_count = int(prev_assigned_resp.count or 0)

        if prev_assigned_count == 0:
            delta2 = "+∞%" if assigned_count > 0 else "0%"
        else:
            pct_change2 = (assigned_count - prev_assigned_count) / prev_assigned_count * 100.0
            delta2 = f"{pct_change2:+.1f}%"

        st.metric(label="Assigned to CRE (MTD)", value=assigned_count, delta=delta2)
    except Exception as err:
        st.warning(f"Could not load KPI (Assigned to CRE): {err}")

with col_kpi_3:
    try:
        now_ts_kpi3 = pd.Timestamp.now(tz="UTC")
        month_start_kpi3 = pd.Timestamp(date.today().replace(day=1)).tz_localize("UTC")
        prev_month_start3 = month_start_kpi3 - pd.offsets.MonthBegin(1)

        ps_resp = (
            supabase
            .table("lead_master")
            .select("id", count="exact")
            .not_.is_("ps_name", "null")
            .gte("created_at", month_start_kpi3.isoformat())
            .lte("created_at", now_ts_kpi3.isoformat())
            .execute()
        )
        ps_count = int(ps_resp.count or 0)

        prev_ps_resp = (
            supabase
            .table("lead_master")
            .select("id", count="exact")
            .not_.is_("ps_name", "null")
            .gte("created_at", prev_month_start3.isoformat())
            .lt("created_at", month_start_kpi3.isoformat())
            .execute()
        )
        prev_ps_count = int(prev_ps_resp.count or 0)

        if prev_ps_count == 0:
            delta3 = "+∞%" if ps_count > 0 else "0%"
        else:
            pct_change3 = (ps_count - prev_ps_count) / prev_ps_count * 100.0
            delta3 = f"{pct_change3:+.1f}%"

        st.metric(label="Assigned to PS (MTD)", value=ps_count, delta=delta3)
    except Exception as err:
        st.warning(f"Could not load KPI (Assigned to PS): {err}")

with col_kpi_4:
    try:
        now_ts_pend = pd.Timestamp.now(tz="UTC")
        month_start_pend = pd.Timestamp(date.today().replace(day=1)).tz_localize("UTC")
        prev_month_start_pend = month_start_pend - pd.offsets.MonthBegin(1)

        pending_resp = (
            supabase
            .table("lead_master")
            .select("id", count="exact")
            .eq("final_status", "Pending")
            .gte("created_at", month_start_pend.isoformat())
            .lte("created_at", now_ts_pend.isoformat())
            .execute()
        )
        pending_count = int(pending_resp.count or 0)

        prev_pending_resp = (
            supabase
            .table("lead_master")
            .select("id", count="exact")
            .eq("final_status", "Pending")
            .gte("created_at", prev_month_start_pend.isoformat())
            .lt("created_at", month_start_pend.isoformat())
            .execute()
        )
        prev_pending_count = int(prev_pending_resp.count or 0)

        if prev_pending_count == 0:
            delta_pend = "+∞%" if pending_count > 0 else "0%"
        else:
            pct_change_pend = (pending_count - prev_pending_count) / prev_pending_count * 100.0
            delta_pend = f"{pct_change_pend:+.1f}%"

        st.metric(label="Pending Leads (MTD)", value=pending_count, delta=delta_pend)
    except Exception as err:
        st.warning(f"Could not load KPI (Pending Leads): {err}")

with col_kpi_5:
    try:
        now_ts_lost = pd.Timestamp.now(tz="UTC")
        month_start_lost = pd.Timestamp(date.today().replace(day=1)).tz_localize("UTC")
        prev_month_start_lost = month_start_lost - pd.offsets.MonthBegin(1)

        lost_resp = (
            supabase
            .table("lead_master")
            .select("id", count="exact")
            .eq("final_status", "Lost")
            .gte("created_at", month_start_lost.isoformat())
            .lte("created_at", now_ts_lost.isoformat())
            .execute()
        )
        lost_count = int(lost_resp.count or 0)

        prev_lost_resp = (
            supabase
            .table("lead_master")
            .select("id", count="exact")
            .eq("final_status", "Lost")
            .gte("created_at", prev_month_start_lost.isoformat())
            .lt("created_at", month_start_lost.isoformat())
            .execute()
        )
        prev_lost_count = int(prev_lost_resp.count or 0)

        if prev_lost_count == 0:
            delta_lost = "+∞%" if lost_count > 0 else "0%"
        else:
            pct_change_lost = (lost_count - prev_lost_count) / prev_lost_count * 100.0
            delta_lost = f"{pct_change_lost:+.1f}%"

        st.metric(label="Lost Leads (MTD)", value=lost_count, delta=delta_lost)
    except Exception as err:
        st.warning(f"Could not load KPI (Lost Leads): {err}")

with col_kpi_6:
    try:
        now_ts_won = pd.Timestamp.now(tz="UTC")
        month_start_won = pd.Timestamp(date.today().replace(day=1)).tz_localize("UTC")
        prev_month_start_won = month_start_won - pd.offsets.MonthBegin(1)

        won_resp = (
            supabase
            .table("lead_master")
            .select("id", count="exact")
            .eq("final_status", "Won")
            .gte("created_at", month_start_won.isoformat())
            .lte("created_at", now_ts_won.isoformat())
            .execute()
        )
        won_count = int(won_resp.count or 0)

        prev_won_resp = (
            supabase
            .table("lead_master")
            .select("id", count="exact")
            .eq("final_status", "Won")
            .gte("created_at", prev_month_start_won.isoformat())
            .lt("created_at", month_start_won.isoformat())
            .execute()
        )
        prev_won_count = int(prev_won_resp.count or 0)

        if prev_won_count == 0:
            delta_won = "+∞%" if won_count > 0 else "0%"
        else:
            pct_change_won = (won_count - prev_won_count) / prev_won_count * 100.0
            delta_won = f"{pct_change_won:+.1f}%"

        st.metric(label="Won Leads (MTD)", value=won_count, delta=delta_won)
    except Exception as err:
        st.warning(f"Could not load KPI (Won Leads): {err}")

# Date filter controls (applies to aggregates below and preview)
filter_option = st.selectbox(
    "Date filter (based on created_at)", ["MTD", "Today", "Custom Range", "None"], index=0
)

# Determine start/end datetimes (all in UTC)
now_ts = pd.Timestamp.now(tz="UTC")
today_start = pd.Timestamp(date.today()).tz_localize("UTC")
today_end = today_start + pd.Timedelta(days=1) - pd.Timedelta(milliseconds=1)
month_start = pd.Timestamp(date.today().replace(day=1)).tz_localize("UTC")

if filter_option == "Today":
    start_dt, end_dt = today_start, today_end
elif filter_option == "MTD":
    start_dt, end_dt = month_start, now_ts
else:
    col_start, col_end = st.columns(2)
    with col_start:
        custom_start = st.date_input("Start date", value=date.today().replace(day=1))
    with col_end:
        custom_end = st.date_input("End date", value=date.today())
    # Normalize to full-day range
    start_dt = pd.Timestamp(custom_start).tz_localize("UTC")
    end_dt = pd.Timestamp(custom_end).tz_localize("UTC") + pd.Timedelta(days=1) - pd.Timedelta(milliseconds=1)

# Apply created_at filter
df_filtered = df.copy()
if filter_option != "None":
    if not df.empty and "created_at" in df.columns:
        created_ts = pd.to_datetime(df["created_at"], errors="coerce", utc=True)
        mask = created_ts.between(start_dt, end_dt)
        df_filtered = df.loc[mask].copy()
    else:
        st.warning("created_at column missing; date filter not applied.")

# Build summary table: unique branches and their row counts
if not df_filtered.empty and "branch" in df_filtered.columns:
    unique_branches = (
        pd.Series(sorted(df_filtered["branch"].dropna().astype(str).unique()))
        .rename("branch")
        .to_frame()
    )
    branch_counts = (
        df_filtered["branch"].astype(str).value_counts().rename_axis("branch").reset_index(name="rows")
    )
    
    # Count pending, won, and lost leads per branch
    if "status" in df_filtered.columns:
        pending_counts = (
            df_filtered[df_filtered["status"].astype(str).str.strip().str.lower() == "pending"]
            .groupby("branch")
            .size()
            .rename_axis("branch")
            .reset_index(name="pending")
        )
        won_counts = (
            df_filtered[df_filtered["status"].astype(str).str.strip().str.lower() == "won"]
            .groupby("branch")
            .size()
            .rename_axis("branch")
            .reset_index(name="won")
        )
        lost_counts = (
            df_filtered[df_filtered["status"].astype(str).str.strip().str.lower() == "lost"]
            .groupby("branch")
            .size()
            .rename_axis("branch")
            .reset_index(name="lost")
        )
    else:
        pending_counts = pd.DataFrame({"branch": [], "pending": []})
        won_counts = pd.DataFrame({"branch": [], "won": []})
        lost_counts = pd.DataFrame({"branch": [], "lost": []})

    # Count touched/untouched leads per branch among Pending status
    if "first_call_date" in df_filtered.columns and "status" in df_filtered.columns:
        status_pending_mask = df_filtered["status"].astype(str).str.strip().str.lower() == "pending"
        has_first_call_mask = df_filtered["first_call_date"].notna() & (df_filtered["first_call_date"].astype(str).str.strip() != "")
        touched_mask = status_pending_mask & has_first_call_mask
        untouched_mask = status_pending_mask & ~has_first_call_mask
        touched_counts = (
            df_filtered[touched_mask]
            .groupby("branch")
            .size()
            .rename_axis("branch")
            .reset_index(name="touched")
        )
        untouched_counts = (
            df_filtered[untouched_mask]
            .groupby("branch")
            .size()
            .rename_axis("branch")
            .reset_index(name="untouched")
        )
    else:
        touched_counts = pd.DataFrame({"branch": [], "touched": []})
        untouched_counts = pd.DataFrame({"branch": [], "untouched": []})
    
    branches_table = unique_branches.merge(branch_counts, on="branch", how="left").fillna({"rows": 0})
    branches_table = branches_table.merge(pending_counts, on="branch", how="left").fillna({"pending": 0})
    branches_table = branches_table.merge(touched_counts, on="branch", how="left").fillna({"touched": 0})
    branches_table = branches_table.merge(untouched_counts, on="branch", how="left").fillna({"untouched": 0})
    branches_table = branches_table.merge(won_counts, on="branch", how="left").fillna({"won": 0})
    branches_table = branches_table.merge(lost_counts, on="branch", how="left").fillna({"lost": 0})
    branches_table["rows"] = branches_table["rows"].astype(int)
    branches_table["pending"] = branches_table["pending"].astype(int)
    branches_table["touched"] = branches_table["touched"].astype(int)
    branches_table["untouched"] = branches_table["untouched"].astype(int)
    branches_table["won"] = branches_table["won"].astype(int)
    branches_table["lost"] = branches_table["lost"].astype(int)
else:
    branches_table = pd.DataFrame({"branch": [], "rows": [], "pending": [], "touched": [], "untouched": [], "won": [], "lost": []})

st.subheader("Branch wise lead Count")
# Order columns: branch, leads punched, pending, touched, untouched, won, lost (where available)
desired_order = ["branch", "rows", "pending", "touched", "untouched", "won", "lost"]
columns_in_order = [col for col in desired_order if col in branches_table.columns]
branches_table = branches_table[columns_in_order]
branches_table_display = branches_table.rename(
    columns={
        "rows": "leads punched",
        "pending": "pending leads",
        "touched": "Touched leads",
        "untouched": "untouched leads",
        "won": "Won Leads",
        "lost": "Lost Leads",
    }
)
st.dataframe(branches_table_display, use_container_width=True)

# Toggle to view/hide underlying raw data (respects selected date filter if applied)
show_underlying = st.toggle("View underlying data", value=False)
if show_underlying:
    st.subheader("Walk-in Table")
    st.dataframe(df_filtered, use_container_width=True)

# Leads by Source bar chart from lead_master at bottom, left 1/3 width
left_col, mid_col, right_col = st.columns([1, 1, 1])
with left_col:
    st.subheader("Leads by Source")
    try:
        leads_res = supabase.table("lead_master").select("source").execute()
        df_leads = pd.DataFrame(leads_res.data)
        if not df_leads.empty and "source" in df_leads.columns:
            source_counts = (
                df_leads["source"].astype(str).str.strip().replace("", "Unknown").value_counts()
                .rename_axis("source").reset_index(name="count")
                .sort_values("count", ascending=False)
            )
            chart = (
                alt.Chart(source_counts)
                .mark_bar()
                .encode(
                    x=alt.X("source:N", sort="-y", title="Source"),
                    y=alt.Y("count:Q", title="Count"),
                    color=alt.Color("source:N", legend=None),
                    tooltip=["source:N", "count:Q"],
                )
            )
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("No lead sources available to display.")
    except Exception as err:
        st.warning(f"Could not load lead sources: {err}")

with mid_col:
    st.subheader("Leads by Source (%)")
    try:
        # Reuse data if already fetched above; otherwise fetch
        if 'df_leads' not in locals():
            leads_res = supabase.table("lead_master").select("source").execute()
            df_leads = pd.DataFrame(leads_res.data)
        if not df_leads.empty and "source" in df_leads.columns:
            source_counts = (
                df_leads["source"].astype(str).str.strip().replace("", "Unknown").value_counts()
                .rename_axis("source").reset_index(name="count")
            )
            total_count = int(source_counts["count"].sum()) or 1
            source_counts["percent"] = source_counts["count"] / total_count
            pie = (
                alt.Chart(source_counts)
                .mark_arc()
                .encode(
                    theta=alt.Theta("count:Q", stack=True),
                    color=alt.Color("source:N", title="Source"),
                    tooltip=[
                        alt.Tooltip("source:N", title="Source"),
                        alt.Tooltip("count:Q", title="Count"),
                        alt.Tooltip("percent:Q", title="Percent", format=".1%"),
                    ],
                )
            )
            st.altair_chart(pie, use_container_width=True)
        else:
            st.info("No lead sources available to display.")
    except Exception as err:
        st.warning(f"Could not load lead sources: {err}")