"""
Bluestock Mutual Fund Analytics Dashboard
A Streamlit + Plotly recreation of the Power BI spec:
  Page 1 - Industry Overview
  Page 2 - Fund Performance (with drill-through to NAV detail)
  Page 3 - Investor Analytics
  Page 4 - SIP & Market Trends

Run with:  streamlit run app.py
"""

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# --------------------------------------------------------------------------
# THEME  ("Bluestock" palette — swap these to match the real brand kit)
# --------------------------------------------------------------------------
BLUE_PRIMARY = "#0B3D91"
BLUE_ACCENT = "#1E88E5"
BLUE_LIGHT = "#90CAF9"
GOLD_ACCENT = "#F5A623"
GREY_BG = "#F4F6F9"
TEXT_DARK = "#0B1F3A"

PLOTLY_TEMPLATE = "plotly_white"
COLOR_SEQUENCE = [BLUE_PRIMARY, BLUE_ACCENT, GOLD_ACCENT, BLUE_LIGHT, "#4C6EF5", "#2CA58D", "#D64545", "#6C5CE7"]

st.set_page_config(page_title="Bluestock MF Dashboard", layout="wide", page_icon="📊")

st.markdown(
    f"""
    <style>
    .stApp {{ background-color: {GREY_BG}; }}
    div[data-testid="stMetric"] {{
        background-color: white;
        border: 1px solid #E3E8EF;
        border-left: 5px solid {BLUE_PRIMARY};
        border-radius: 8px;
        padding: 14px 16px;
    }}
    div[data-testid="stMetricLabel"] {{ color: {TEXT_DARK}; font-weight: 600; }}
    div[data-testid="stMetricValue"] {{ color: {BLUE_PRIMARY}; }}
    section[data-testid="stSidebar"] {{ background-color: white; border-right: 1px solid #E3E8EF; }}
    h1, h2, h3 {{ color: {TEXT_DARK}; }}
    </style>
    """,
    unsafe_allow_html=True,
)

candidate_dirs = [
    Path(__file__).resolve().parent / "Data" / "Raw",
    Path(__file__).resolve().parent / "data" / "Raw",
    Path(__file__).resolve().parent.parent / "Capstone Project" / "Data" / "Raw",
    Path(__file__).resolve().parent.parent / "Capstone Project" / "data" / "Raw",
]
DATA_DIR = next((p for p in candidate_dirs if p.exists()), candidate_dirs[0])
if not DATA_DIR.exists():
    raise FileNotFoundError(
        "Could not find the data folder. Checked: " + ", ".join(str(p) for p in candidate_dirs)
    )


# --------------------------------------------------------------------------
# DATA LOADING  (cached — mirrors Power BI's "import" connection mode)
# --------------------------------------------------------------------------
@st.cache_data
def load_data():
    fund_master = pd.read_csv(DATA_DIR / "01_fund_master.csv", parse_dates=["launch_date"])
    nav = pd.read_csv(DATA_DIR / "02_nav_history.csv", parse_dates=["date"])
    aum = pd.read_csv(DATA_DIR / "03_aum_by_fund_house.csv", parse_dates=["date"])
    sip = pd.read_csv(DATA_DIR / "04_monthly_sip_inflows.csv")
    sip["month"] = pd.to_datetime(sip["month"], format="%Y-%m")
    category_inflows = pd.read_csv(DATA_DIR / "05_category_inflows.csv")
    category_inflows["month"] = pd.to_datetime(category_inflows["month"], format="%Y-%m")
    folio = pd.read_csv(DATA_DIR / "06_industry_folio_count.csv")
    folio["month"] = pd.to_datetime(folio["month"], format="%Y-%m")
    scheme_perf = pd.read_csv(DATA_DIR / "07_scheme_performance.csv")
    transactions = pd.read_csv(DATA_DIR / "08_investor_transactions.csv", parse_dates=["transaction_date"])
    holdings = pd.read_csv(DATA_DIR / "09_portfolio_holdings.csv", parse_dates=["portfolio_date"])
    bench = pd.read_csv(DATA_DIR / "10_benchmark_indices.csv", parse_dates=["date"])

    # relationships: amfi_code links fund_master <-> nav/scheme_perf/holdings
    #                date links nav <-> bench
    nav = nav.merge(fund_master[["amfi_code", "scheme_name", "fund_house", "category", "plan"]], on="amfi_code", how="left")
    transactions = transactions.merge(fund_master[["amfi_code", "scheme_name"]], on="amfi_code", how="left")

    return dict(
        fund_master=fund_master, nav=nav, aum=aum, sip=sip,
        category_inflows=category_inflows, folio=folio, scheme_perf=scheme_perf,
        transactions=transactions, holdings=holdings, bench=bench,
    )


data = load_data()

# --------------------------------------------------------------------------
# SIDEBAR NAV
# --------------------------------------------------------------------------
st.sidebar.markdown(f"<h2 style='color:{BLUE_PRIMARY};'>📊 Bluestock</h2>", unsafe_allow_html=True)
st.sidebar.caption("Mutual Fund Analytics Dashboard")
page = st.sidebar.radio(
    "Pages",
    ["1 · Industry Overview", "2 · Fund Performance", "3 · Investor Analytics", "4 · SIP & Market Trends"],
)
st.sidebar.markdown("---")
st.sidebar.caption("Data: FY2022–FY2025 · 40 schemes · 10 AMCs")

if "drill_scheme" not in st.session_state:
    st.session_state.drill_scheme = None


# ==========================================================================
# PAGE 1 — INDUSTRY OVERVIEW
# ==========================================================================
if page.startswith("1"):
    st.title("Industry Overview")

    fund_master, aum, sip, folio = data["fund_master"], data["aum"], data["sip"], data["folio"]

    latest_aum_date = aum["date"].max()
    total_aum_cr = aum[aum["date"] == latest_aum_date]["aum_crore"].sum()
    latest_sip = sip.sort_values("month").iloc[-1]
    latest_folio = folio.sort_values("month").iloc[-1]
    n_schemes = fund_master["amfi_code"].nunique()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total AUM", f"₹{total_aum_cr/1e5:,.1f}L Cr", help=f"As of {latest_aum_date:%b %Y}")
    c2.metric("Monthly SIP Inflows", f"₹{latest_sip['sip_inflow_crore']:,.0f} Cr", help=f"As of {latest_sip['month']:%b %Y}")
    c3.metric("Total Folios", f"{latest_folio['total_folios_crore']:.2f} Cr", help=f"As of {latest_folio['month']:%b %Y}")
    c4.metric("Schemes Tracked", f"{n_schemes:,}")

    st.markdown("###")
    col1, col2 = st.columns([3, 2])

    with col1:
        industry_aum = aum.groupby("date", as_index=False)["aum_crore"].sum()
        fig = px.line(industry_aum, x="date", y="aum_crore", title="Industry AUM trend (2022–2025)",
                       template=PLOTLY_TEMPLATE, color_discrete_sequence=[BLUE_PRIMARY])
        fig.update_traces(line_width=3, hovertemplate="%{x|%b %Y}<br>₹%{y:,.0f} Cr<extra></extra>")
        fig.update_layout(yaxis_title="AUM (₹ Cr)", xaxis_title="")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        latest_by_house = aum[aum["date"] == latest_aum_date].sort_values("aum_crore", ascending=True)
        fig2 = px.bar(latest_by_house, x="aum_crore", y="fund_house", orientation="h",
                       title=f"AUM by AMC ({latest_aum_date:%b %Y})",
                       template=PLOTLY_TEMPLATE, color_discrete_sequence=[BLUE_ACCENT])
        fig2.update_traces(hovertemplate="%{y}<br>₹%{x:,.0f} Cr<extra></extra>")
        fig2.update_layout(xaxis_title="AUM (₹ Cr)", yaxis_title="")
        st.plotly_chart(fig2, use_container_width=True)


# ==========================================================================
# PAGE 2 — FUND PERFORMANCE
# ==========================================================================
elif page.startswith("2"):
    st.title("Fund Performance")

    scheme_perf, nav, bench, fund_master = data["scheme_perf"], data["nav"], data["bench"], data["fund_master"]
    perf = scheme_perf.merge(fund_master[["amfi_code", "plan"]], on="amfi_code", how="left", suffixes=("", "_fm"))

    f1, f2, f3 = st.columns(3)
    house_sel = f1.multiselect("Fund house", sorted(perf["fund_house"].unique()))
    cat_sel = f2.multiselect("Category", sorted(perf["category"].unique()))
    plan_sel = f3.multiselect("Plan", sorted(perf["plan"].dropna().unique()))

    filtered = perf.copy()
    if house_sel:
        filtered = filtered[filtered["fund_house"].isin(house_sel)]
    if cat_sel:
        filtered = filtered[filtered["category"].isin(cat_sel)]
    if plan_sel:
        filtered = filtered[filtered["plan"].isin(plan_sel)]

    col1, col2 = st.columns([3, 2])
    with col1:
        fig = px.scatter(
            filtered, x="std_dev_ann_pct", y="return_5yr_pct", size="aum_crore", color="category",
            hover_name="scheme_name", size_max=45, template=PLOTLY_TEMPLATE,
            color_discrete_sequence=COLOR_SEQUENCE,
            title="5-yr return vs risk (bubble size = AUM)",
            labels={"std_dev_ann_pct": "Annualized volatility (%)", "return_5yr_pct": "5-yr return (%)"},
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("**Fund scorecard** — click a row, then check the box below to drill through")
        display_cols = ["scheme_name", "fund_house", "category", "return_1yr_pct", "return_5yr_pct",
                         "sharpe_ratio", "std_dev_ann_pct", "morningstar_rating", "risk_grade"]
        st.dataframe(
            filtered[display_cols].sort_values("sharpe_ratio", ascending=False),
            use_container_width=True, height=380, hide_index=True,
        )

    st.markdown("---")
    st.subheader("Drill-through → NAV detail vs benchmark")
    scheme_options = sorted(filtered["scheme_name"].unique()) if not filtered.empty else sorted(perf["scheme_name"].unique())
    default_idx = scheme_options.index(st.session_state.drill_scheme) if st.session_state.drill_scheme in scheme_options else 0
    chosen = st.selectbox("Select a scheme", scheme_options, index=default_idx)
    st.session_state.drill_scheme = chosen

    scheme_row = fund_master[fund_master["scheme_name"] == chosen].iloc[0]
    scheme_nav = nav[nav["scheme_name"] == chosen].sort_values("date")
    bench_name = scheme_row["benchmark"].split()[0].replace("100", "").upper()
    bench_match = bench[bench["index_name"].str.contains("NIFTY", case=False)]
    # fall back to NIFTY50 if exact benchmark index not present in the benchmark file
    bmk = bench[bench["index_name"] == "NIFTY50"] if "NIFTY50" in bench["index_name"].unique() else bench_match

    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(x=scheme_nav["date"], y=scheme_nav["nav"], name=chosen,
                               line=dict(color=BLUE_PRIMARY, width=2.5)))
    if not bmk.empty:
        bmk_norm = bmk.copy()
        # rebase benchmark to the fund's NAV starting level so trends are comparable
        scale = scheme_nav["nav"].iloc[0] / bmk_norm["close_value"].iloc[0]
        bmk_norm["scaled"] = bmk_norm["close_value"] * scale
        fig3.add_trace(go.Scatter(x=bmk_norm["date"], y=bmk_norm["scaled"], name=f"{bmk_norm['index_name'].iloc[0]} (rebased)",
                                   line=dict(color=GOLD_ACCENT, width=2, dash="dot")))
    fig3.update_layout(template=PLOTLY_TEMPLATE, title=f"{chosen} — NAV vs benchmark", height=420,
                        yaxis_title="Value", xaxis_title="")
    st.plotly_chart(fig3, use_container_width=True)

    with st.expander("Scheme detail card"):
        detail = scheme_perf[scheme_perf["scheme_name"] == chosen].iloc[0]
        d1, d2, d3, d4 = st.columns(4)
        d1.metric("1-yr return", f"{detail['return_1yr_pct']:.2f}%")
        d2.metric("5-yr return", f"{detail['return_5yr_pct']:.2f}%")
        d3.metric("Sharpe ratio", f"{detail['sharpe_ratio']:.2f}")
        d4.metric("Max drawdown", f"{detail['max_drawdown_pct']:.2f}%")


# ==========================================================================
# PAGE 3 — INVESTOR ANALYTICS
# ==========================================================================
elif page.startswith("3"):
    st.title("Investor Analytics")

    transactions = data["transactions"]

    f1, f2, f3 = st.columns(3)
    state_sel = f1.multiselect("State", sorted(transactions["state"].dropna().unique()))
    age_sel = f2.multiselect("Age group", sorted(transactions["age_group"].dropna().unique()))
    tier_sel = f3.multiselect("City tier", sorted(transactions["city_tier"].dropna().unique()))

    txn = transactions.copy()
    if state_sel:
        txn = txn[txn["state"].isin(state_sel)]
    if age_sel:
        txn = txn[txn["age_group"].isin(age_sel)]
    if tier_sel:
        txn = txn[txn["city_tier"].isin(tier_sel)]

    col1, col2 = st.columns([3, 2])
    with col1:
        state_amt = txn.groupby("state", as_index=False)["amount_inr"].sum().sort_values("amount_inr", ascending=True).tail(15)
        fig = px.bar(state_amt, x="amount_inr", y="state", orientation="h", template=PLOTLY_TEMPLATE,
                     title="Transaction amount by state (top 15)", color_discrete_sequence=[BLUE_PRIMARY])
        fig.update_layout(xaxis_title="Total amount (₹)", yaxis_title="")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        type_split = txn.groupby("transaction_type", as_index=False)["amount_inr"].sum()
        fig2 = px.pie(type_split, names="transaction_type", values="amount_inr", hole=0.45,
                       template=PLOTLY_TEMPLATE, color_discrete_sequence=COLOR_SEQUENCE,
                       title="SIP / Lumpsum / Redemption split")
        st.plotly_chart(fig2, use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        sip_only = txn[txn["transaction_type"] == "SIP"]
        age_avg = sip_only.groupby("age_group", as_index=False)["amount_inr"].mean().sort_values("age_group")
        fig3 = px.bar(age_avg, x="age_group", y="amount_inr", template=PLOTLY_TEMPLATE,
                      title="Average SIP amount by age group", color_discrete_sequence=[BLUE_ACCENT])
        fig3.update_layout(xaxis_title="Age group", yaxis_title="Avg SIP amount (₹)")
        st.plotly_chart(fig3, use_container_width=True)

    with col4:
        txn["month"] = txn["transaction_date"].dt.to_period("M").dt.to_timestamp()
        monthly_vol = txn.groupby("month", as_index=False).size()
        fig4 = px.line(monthly_vol, x="month", y="size", template=PLOTLY_TEMPLATE,
                       title="Monthly transaction volume", color_discrete_sequence=[GOLD_ACCENT])
        fig4.update_traces(line_width=3)
        fig4.update_layout(xaxis_title="", yaxis_title="Transaction count")
        st.plotly_chart(fig4, use_container_width=True)


# ==========================================================================
# PAGE 4 — SIP & MARKET TRENDS
# ==========================================================================
elif page.startswith("4"):
    st.title("SIP & Market Trends")

    sip, bench, category_inflows = data["sip"], data["bench"], data["category_inflows"]

    nifty = bench[bench["index_name"] == "NIFTY50"].copy()
    nifty["month"] = nifty["date"].dt.to_period("M").dt.to_timestamp()
    nifty_monthly = nifty.groupby("month", as_index=False)["close_value"].last()
    merged = sip.merge(nifty_monthly, on="month", how="left")

    fig = go.Figure()
    fig.add_trace(go.Bar(x=merged["month"], y=merged["sip_inflow_crore"], name="SIP inflow (₹ Cr)",
                          marker_color=BLUE_ACCENT, yaxis="y1"))
    fig.add_trace(go.Scatter(x=merged["month"], y=merged["close_value"], name="NIFTY 50", mode="lines",
                              line=dict(color=GOLD_ACCENT, width=3), yaxis="y2"))
    fig.update_layout(
        template=PLOTLY_TEMPLATE, height=460, title="Monthly SIP inflow vs NIFTY 50 (2022–2025)",
        yaxis=dict(title="SIP inflow (₹ Cr)"),
        yaxis2=dict(title="NIFTY 50", overlaying="y", side="right", showgrid=False),
        legend=dict(orientation="h", y=1.08),
    )
    st.plotly_chart(fig, use_container_width=True)

    col1, col2 = st.columns([3, 2])
    with col1:
        heat = category_inflows.pivot_table(index="category", columns="month", values="net_inflow_crore", aggfunc="sum").fillna(0)
        heat.columns = [c.strftime("%b-%y") for c in heat.columns]
        fig2 = px.imshow(heat, aspect="auto", color_continuous_scale="RdYlGn",
                          template=PLOTLY_TEMPLATE, title="Category inflow heatmap")
        fig2.update_layout(xaxis_title="Month", yaxis_title="")
        st.plotly_chart(fig2, use_container_width=True)

    with col2:
        fy25 = category_inflows[(category_inflows["month"] >= "2024-04-01") & (category_inflows["month"] <= "2025-03-01")]
        top5 = fy25.groupby("category", as_index=False)["net_inflow_crore"].sum().sort_values("net_inflow_crore", ascending=False).head(5)
        fig3 = px.bar(top5.sort_values("net_inflow_crore"), x="net_inflow_crore", y="category", orientation="h",
                      template=PLOTLY_TEMPLATE, title="Top 5 categories by net inflow — FY25",
                      color_discrete_sequence=[BLUE_PRIMARY])
        fig3.update_layout(xaxis_title="Net inflow (₹ Cr)", yaxis_title="")
        st.plotly_chart(fig3, use_container_width=True)
