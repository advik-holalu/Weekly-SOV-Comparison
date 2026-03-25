import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path

st.set_page_config(page_title="Weekly SOV Dashboard", layout="wide")

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data_agg" / "sov_weekly.parquet"

GO_DESI = "Go Desi"
GO_DESI_COLOR = "#F05A28"

# =====================================================
# LOAD PARQUET (CLOUD SAFE)
# =====================================================
@st.cache_data(show_spinner=False)
def load_data():
    df = pd.read_parquet(DATA)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Year"] = pd.to_numeric(df["Year"], errors="coerce")

    for c in ["Week", "Month", "Category", "City", "Brand", "Platform"]:
        df[c] = df[c].astype(str).str.strip()

    return df

@st.cache_data(show_spinner=False)
def load_blinkit():
    path = ROOT / "data_raw" / "BlinkitVS.xlsx"
    df = pd.read_excel(path, engine="openpyxl")
    df.columns = df.columns.str.strip()
    return df

df = load_data()

# =====================================================
# METRICS
# =====================================================
METRICS = {
    "Est. Category Share": "Est. Category Share",
    "Est. Category Share SP": "Est. Category Share SP",
    "Overall SOV": "Overall SOV",
    "Organic SOV": "Organic SOV",
    "Ad SOV": "Ad SOV",
}

# =====================================================
# COLOR MAP
# =====================================================
def build_color_map(brands):
    palette = px.colors.qualitative.Set2 + px.colors.qualitative.Bold
    it = iter(palette)
    out = {}

    if GO_DESI in brands:
        out[GO_DESI] = GO_DESI_COLOR

    for b in brands:
        if b == GO_DESI:
            continue
        out[b] = next(it, "#4C78A8")

    return out


# =====================================================
# TABS
# =====================================================
tab1, tab2 = st.tabs(["SOV vs Market Share", "Blinkit Volume Share"])


# =====================================================
# ====================== TAB 1 =========================
# =====================================================
with tab1:

    # =====================================================
    # SIDEBAR FILTERS
    # =====================================================
    st.sidebar.header("Filters")

    df_f = df.copy()

    # =====================================================
    # FINANCIAL YEAR LOGIC (APR–MAR)
    # =====================================================

    month_order = {
        "Jan": 1, "Feb": 2, "Mar": 3,
        "Apr": 4, "May": 5, "Jun": 6,
        "Jul": 7, "Aug": 8, "Sep": 9,
        "Oct": 10, "Nov": 11, "Dec": 12,
    }

    df_f["MonthNum"] = df_f["Month"].map(month_order)

    # Financial Year
    df_f["FY"] = df_f.apply(
        lambda x: x["Year"] if x["MonthNum"] >= 4 else x["Year"] - 1,
        axis=1
    )

    # Financial Quarter
    def get_fy_quarter(m):
        if m in [4,5,6]:
            return "Q1"
        elif m in [7,8,9]:
            return "Q2"
        elif m in [10,11,12]:
            return "Q3"
        else:
            return "Q4"

    df_f["Quarter"] = df_f["MonthNum"].apply(get_fy_quarter)

    df_f["FYQuarter"] = df_f["FY"].astype(str) + " - " + df_f["Quarter"]

    # =====================================================
    # PLATFORM
    # =====================================================
    platform_opts = sorted(df["Platform"].unique())

    platform_display = ["Select All"] + platform_opts

    selected_platform = st.sidebar.multiselect(
        "Platform",
        platform_display,
        default=["Zepto"] if "Zepto" in platform_opts else ["Select All"]
    )

    if "Select All" in selected_platform:
        platform = platform_opts
    else:
        platform = selected_platform

    df_f = df_f[df_f["Platform"].isin(platform)]


    # =====================================================
    # CATEGORY
    # =====================================================
    cat_opts = sorted(df_f["Category"].unique())

    cat_display = ["Select All"] + cat_opts

    selected_category = st.sidebar.multiselect(
        "Category",
        cat_display,
        default=["Indian Sweets"] if "Indian Sweets" in cat_opts else ["Select All"]
    )

    if "Select All" in selected_category:
        category = cat_opts
    else:
        category = selected_category

    df_f = df_f[df_f["Category"].isin(category)]


    # =====================================================
    # CITY
    # =====================================================
    city_opts = sorted(df_f["City"].unique())

    city_display = ["Select All"] + city_opts

    default_city = (
        ["PAN India"] if "PAN India" in city_opts
        else ["Bangalore"] if "Bangalore" in city_opts
        else ["Select All"]
    )

    selected_city = st.sidebar.multiselect(
        "City",
        city_display,
        default=default_city
    )

    if "Select All" in selected_city:
        city = city_opts
    else:
        city = selected_city

    df_f = df_f[df_f["City"].isin(city)]

    # =====================================================
    # QUARTER FILTER (DEFAULT = ALL)
    # =====================================================

    quarter_opts = (
        df_f[["FYQuarter", "Date"]]
        .drop_duplicates()
        .sort_values("Date")
    )["FYQuarter"].unique().tolist()

    quarter_display = ["Select All"] + quarter_opts

    selected_quarters = st.sidebar.multiselect(
        "Quarter (Financial Year)",
        quarter_display,
        default=["Select All"]
    )

    if "Select All" in selected_quarters:
        quarters = quarter_opts
    else:
        quarters = selected_quarters

    df_f = df_f[df_f["FYQuarter"].isin(quarters)]

    # =====================================================
    # MONTH FILTER (DEFAULT = ALL)
    # =====================================================

    month_opts = (
        df_f[["Month", "MonthNum"]]
        .drop_duplicates()
        .sort_values("MonthNum")
    )["Month"].tolist()

    month_display = ["Select All"] + month_opts

    selected_months = st.sidebar.multiselect(
        "Month",
        month_display,
        default=["Select All"]
    )

    if "Select All" in selected_months:
        months = month_opts
    else:
        months = selected_months

    df_f = df_f[df_f["Month"].isin(months)]

    # =====================================================
    # BRAND
    # =====================================================
    brands_available = sorted(df_f["Brand"].unique())

    if "brands" not in st.session_state:
        if GO_DESI in brands_available:
            st.session_state.brands = [GO_DESI]
        else:
            st.session_state.brands = brands_available[:1]

    st.session_state.brands = [b for b in st.session_state.brands if b in brands_available]

    brands = st.sidebar.multiselect(
        "Brand",
        brands_available,
        key="brands"
    )

    df_plot = df_f[df_f["Brand"].isin(brands)]

    # =====================================================
    # METRICS
    # =====================================================
    st.sidebar.markdown("---")

    metric_keys = list(METRICS.keys())

    m1 = st.sidebar.selectbox(
        "Compare Metric (Solid)",
        metric_keys,
        index=metric_keys.index("Est. Category Share")
    )

    m2_options = [m for m in metric_keys if m != m1]

    default_m2 = "Overall SOV" if "Overall SOV" in m2_options else m2_options[0]

    m2 = st.sidebar.selectbox(
        "Baseline Metric (Dashed)",
        m2_options,
        index=m2_options.index(default_m2)
    )

    col1 = METRICS[m1]
    col2 = METRICS[m2]

    # =====================================================
    # CHART
    # =====================================================
    st.title("Weekly SOV vs Share")

    if df_plot.empty:
        st.stop()

    df_plot = df_plot.sort_values("Date")

    df_plot["WeekLabel"] = (
        df_plot["Year"].astype(int).astype(str)
        + " - "
        + df_plot["Week"]
    )

    week_order_df = (
        df_plot[["WeekLabel", "Date"]]
        .drop_duplicates()
        .sort_values("Date")
    )

    x_order = week_order_df["WeekLabel"].tolist()

    colors = build_color_map(sorted(df_plot["Brand"].unique()))

    fig = go.Figure()

    for b in sorted(df_plot["Brand"].unique()):
        d = df_plot[df_plot["Brand"] == b]

        fig.add_trace(go.Scatter(
            x=d["WeekLabel"],
            y=d[col1],
            mode="lines+markers+text",
            text=[f"{v:.1f}%" for v in d[col1]],
            textposition="top center",
            name=f"{b} — {m1}",
            line=dict(color=colors[b], width=2),
        ))

        fig.add_trace(go.Scatter(
            x=d["WeekLabel"],
            y=d[col2],
            mode="lines+markers+text",
            text=[f"{v:.1f}%" for v in d[col2]],
            textposition="bottom center",
            name=f"{b} — {m2}",
            line=dict(color=colors[b], width=2, dash="dash"),
        ))

    fig.update_layout(
        height=600,
        xaxis=dict(categoryorder="array", categoryarray=x_order),
        yaxis_title="%",
        legend=dict(orientation="h", y=-0.25),
    )

    st.plotly_chart(fig, use_container_width=True)


# =====================================================
# ====================== TAB 2 =========================
# =====================================================
with tab2:
    st.title("Blinkit Volume Share")

    df = load_blinkit().copy()   # independent from global filters

    # =========================
    # FILTERS
    # =========================
    st.markdown("### Filters")

    col1, col2 = st.columns(2)

    # -------------------------
    # CATEGORY (default fixed)
    # -------------------------
    with col1:
        category = st.multiselect(
            "Category",
            sorted(df["Category"].unique()),
            default=["Indian Sweets"]
        )

    # -------------------------
    # KEYWORD TYPE (All logic)
    # -------------------------
    with col2:
        keyword_type_opts = sorted(df["Keyword Type"].unique())
        keyword_type_display = ["All"] + keyword_type_opts

        selected_keyword_type = st.multiselect(
            "Keyword Type",
            keyword_type_display,
            default=["All"]
        )

        if "All" in selected_keyword_type:
            keyword_type = keyword_type_opts
        else:
            keyword_type = selected_keyword_type

    df = df[df["Category"].isin(category)]
    df = df[df["Keyword Type"].isin(keyword_type)]

    col3, col4 = st.columns(2)

    # -------------------------
    # KEYWORD (default GO DESi)
    # -------------------------
    with col3:
        keyword_opts = sorted(df["Keyword"].unique())

        keywords = st.multiselect(
            "Keyword",
            keyword_opts,
            default=["GO DESi"] if "GO DESi" in keyword_opts else keyword_opts[:1]
        )

    # -------------------------
    # WEEK (All logic)
    # -------------------------
    with col4:
        week_cols = [c for c in df.columns if "W" in c]
        week_display = ["All"] + week_cols

        selected_weeks = st.multiselect(
            "Week",
            week_display,
            default=["All"]
        )

        if "All" in selected_weeks:
            selected_weeks = week_cols

    df = df[df["Keyword"].isin(keywords)]

    # =========================
    # TRANSFORM
    # =========================
    df_melt = df.melt(
        id_vars=["Category", "Keyword Type", "Keyword"],
        value_vars=selected_weeks,
        var_name="Week",
        value_name="Searches"
    )

    df_melt["Searches"] = pd.to_numeric(df_melt["Searches"], errors="coerce")

    # =========================
    # SORT WEEKS PROPERLY
    # =========================
    def week_sort(w):
        try:
            year = int("20" + w[:2])
            week = int(w.split("W")[1])
            return (year, week)
        except:
            return (0, 0)

    df_melt["sort_key"] = df_melt["Week"].apply(week_sort)
    df_melt = df_melt.sort_values("sort_key")

    # =========================
    # PLOT
    # =========================
    fig = go.Figure()

    for k in keywords:
        d = df_melt[df_melt["Keyword"] == k]

        fig.add_trace(go.Scatter(
            x=d["Week"],
            y=d["Searches"],
            mode="lines+markers+text",
            text=[f"{int(v):,}" for v in d["Searches"]],
            textposition="top center",
            name=k,
            line=dict(width=3)
        ))

    fig.update_layout(
        height=600,
        yaxis_title="Search Volume",
        xaxis_title="Week",
        legend=dict(orientation="h", y=-0.2),
    )

    st.plotly_chart(fig, use_container_width=True)