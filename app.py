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
      h1 { font-size: 34px !important; margin-bottom: 0.5rem !important; }
      h2 { font-size: 26px !important; margin-bottom: 0.5rem !important; }
      h3 { font-size: 22px !important; margin-bottom: 0.25rem !important; }
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

# KPI cards (top): All in one row
col_kpi_1, col_kpi_2, col_kpi_3, col_kpi_4, col_kpi_5, col_kpi_6, col_kpi_7, col_kpi_8 = st.columns(8)
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

with col_kpi_7:
    try:
        now_ts_walkin = pd.Timestamp.now(tz="UTC")
        month_start_walkin = pd.Timestamp(date.today().replace(day=1)).tz_localize("UTC")
        prev_month_start_walkin = month_start_walkin - pd.offsets.MonthBegin(1)

        walkin_resp = (
            supabase
            .table("walkin_table")
            .select("id", count="exact")
            .gte("created_at", month_start_walkin.isoformat())
            .lte("created_at", now_ts_walkin.isoformat())
            .execute()
        )
        walkin_count = int(walkin_resp.count or 0)

        prev_walkin_resp = (
            supabase
            .table("walkin_table")
            .select("id", count="exact")
            .gte("created_at", prev_month_start_walkin.isoformat())
            .lt("created_at", month_start_walkin.isoformat())
            .execute()
        )
        prev_walkin_count = int(prev_walkin_resp.count or 0)

        if prev_walkin_count == 0:
            delta_walkin = "+∞%" if walkin_count > 0 else "0%"
        else:
            pct_change_walkin = (walkin_count - prev_walkin_count) / prev_walkin_count * 100.0
            delta_walkin = f"{pct_change_walkin:+.1f}%"

        st.metric(label="Walkin Leads (MTD)", value=walkin_count, delta=delta_walkin)
    except Exception as err:
        st.warning(f"Could not load KPI (Walkin Leads): {err}")

with col_kpi_8:
    try:
        now_ts_walkin_won = pd.Timestamp.now(tz="UTC")
        month_start_walkin_won = pd.Timestamp(date.today().replace(day=1)).tz_localize("UTC")
        prev_month_start_walkin_won = month_start_walkin_won - pd.offsets.MonthBegin(1)

        walkin_won_resp = (
            supabase
            .table("walkin_table")
            .select("id", count="exact")
            .eq("status", "Won")
            .gte("created_at", month_start_walkin_won.isoformat())
            .lte("created_at", now_ts_walkin_won.isoformat())
            .execute()
        )
        walkin_won_count = int(walkin_won_resp.count or 0)

        prev_walkin_won_resp = (
            supabase
            .table("walkin_table")
            .select("id", count="exact")
            .eq("status", "Won")
            .gte("created_at", prev_month_start_walkin_won.isoformat())
            .lt("created_at", month_start_walkin_won.isoformat())
            .execute()
        )
        prev_walkin_won_count = int(prev_walkin_won_resp.count or 0)

        if prev_walkin_won_count == 0:
            delta_walkin_won = "+∞%" if walkin_won_count > 0 else "0%"
        else:
            pct_change_walkin_won = (walkin_won_count - prev_walkin_won_count) / prev_walkin_won_count * 100.0
            delta_walkin_won = f"{pct_change_walkin_won:+.1f}%"

        st.metric(label="Walkin Won (MTD)", value=walkin_won_count, delta=delta_walkin_won)
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

    # Date filter controls for Admin dashboard - compact size
    col_filter_admin, col_empty_filter_admin = st.columns([0.2, 0.8])
    with col_filter_admin:
        filter_option_admin = st.selectbox(
            "Date filter (based on created_at)", ["MTD", "Today", "Custom Range", "All time"], index=0, key="admin_filter"
        )

    # Determine start/end datetimes for admin filter (all in UTC)
    now_ts_admin = pd.Timestamp.now(tz="UTC")
    today_start_admin = pd.Timestamp(date.today()).tz_localize("UTC")
    today_end_admin = today_start_admin + pd.Timedelta(days=1) - pd.Timedelta(milliseconds=1)
    month_start_admin = pd.Timestamp(date.today().replace(day=1)).tz_localize("UTC")

    if filter_option_admin == "Today":
        start_dt_admin, end_dt_admin = today_start_admin, today_end_admin
    elif filter_option_admin == "MTD":
        start_dt_admin, end_dt_admin = month_start_admin, now_ts_admin
    elif filter_option_admin == "Custom Range":
        # Custom date inputs also in compact size
        col_custom_admin, col_empty_custom_admin = st.columns([0.2, 0.8])
        with col_custom_admin:
            col_start_admin, col_end_admin = st.columns(2)
            with col_start_admin:
                custom_start_admin = st.date_input("Start date", value=date.today().replace(day=1), key="admin_start")
            with col_end_admin:
                custom_end_admin = st.date_input("End date", value=date.today(), key="admin_end")
        # Normalize to full-day range
        start_dt_admin = pd.Timestamp(custom_start_admin).tz_localize("UTC")
        end_dt_admin = pd.Timestamp(custom_end_admin).tz_localize("UTC") + pd.Timedelta(days=1) - pd.Timedelta(milliseconds=1)
    else:
        start_dt_admin, end_dt_admin = None, None

    # Apply created_at filter to admin data
    df_leads_filtered = df_leads.copy()
    if filter_option_admin != "All time" and start_dt_admin is not None and end_dt_admin is not None:
        if not df_leads.empty and "created_at" in df_leads.columns:
            created_ts_admin = pd.to_datetime(df_leads["created_at"], errors="coerce", utc=True)
            mask_admin = created_ts_admin.between(start_dt_admin, end_dt_admin)
            df_leads_filtered = df_leads.loc[mask_admin].copy()
        else:
            st.warning("created_at column missing; date filter not applied to admin data.")

    # Create four columns for Admin dashboard (shift mid left, widen Walkin panel)
    left_col, spacer_col, mid_col, right_col = st.columns([0.28, 0.02, 0.22, 0.48])
    
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
        st.subheader("Source-wise Conversion (%)")
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

                walkin_row = pd.DataFrame([
                    {"Source": "Walkin", "Count": walkin_total, "Won": walkin_won}
                ])
                sources_df = pd.concat([sources_df, walkin_row], ignore_index=True)
            except Exception as err:
                st.warning(f"Could not append Walkin row: {err}")

            # Calculate conversion percentage (Won/Count * 100)
            sources_df["Conversion %"] = (sources_df["Won"] / sources_df["Count"] * 100).round(2)
            
            # Sort by conversion percentage descending, then by count descending, then by source name
            sources_df = sources_df.sort_values(["Conversion %", "Count", "Source"], ascending=[False, False, True])
            
            # Make Source the index, append TOTAL row, and show it in the table
            sources_df_display = sources_df.set_index("Source")
            total_count_src = int(sources_df["Count"].sum())
            total_won_src = int(sources_df["Won"].sum())
            total_conv_src = (total_won_src / total_count_src * 100.0) if total_count_src else 0.0
            total_row_src = pd.DataFrame({
                "Count": [total_count_src],
                "Won": [total_won_src],
                "Conversion %": [round(total_conv_src, 2)],
            }, index=["TOTAL"])
            sources_df_display = pd.concat([sources_df_display, total_row_src])
            st.dataframe(sources_df_display, use_container_width=True, hide_index=False)
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
    st.info("Walkin (branch-wise) has been moved to the Admin tab next to Source-wise Conversion (%).")

with tab3:
    pass