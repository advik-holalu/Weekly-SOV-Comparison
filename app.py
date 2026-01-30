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

    for c in ["Week", "Month", "Category", "City", "Brand", "Platform"]:
        df[c] = df[c].astype(str).str.strip()

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
# SIDEBAR FILTERS
# =====================================================
st.sidebar.header("Filters")

df_f = df.copy()

platform_opts = sorted(df["Platform"].unique())
platform = st.sidebar.multiselect(
    "Platform",
    platform_opts,
    default=["Zepto"] if "Zepto" in platform_opts else []
)
if platform:
    df_f = df_f[df_f["Platform"].isin(platform)]

cat_opts = sorted(df_f["Category"].unique())
category = st.sidebar.multiselect(
    "Category",
    cat_opts,
    default=["Indian Sweets"] if "Indian Sweets" in cat_opts else []
)
if category:
    df_f = df_f[df_f["Category"].isin(category)]

city_opts = sorted(df_f["City"].unique())

default_city = ["PAN India"] if "PAN India" in city_opts else (
    ["Bangalore"] if "Bangalore" in city_opts else city_opts[:1]
)

city = st.sidebar.multiselect(
    "City",
    city_opts,
    default=default_city
)

if city:
    df_f = df_f[df_f["City"].isin(city)]

month_opts = sorted(df_f["Month"].unique())

preferred_months = ["Apr", "May", "Jun"]
default_months = [m for m in preferred_months if m in month_opts]

# fallback if Apr/May/Jun not present
if not default_months:
    default_months = month_opts

month = st.sidebar.multiselect(
    "Month",
    month_opts,
    default=default_months
)

if month:
    df_f = df_f[df_f["Month"].isin(month)]

# =====================================================
# BRAND (SESSION SAFE - NO BOUNCE)
# =====================================================
brands_available = sorted(df_f["Brand"].unique())

# Initialize once
if "brands" not in st.session_state:
    if GO_DESI in brands_available:
        st.session_state.brands = [GO_DESI]
    else:
        st.session_state.brands = brands_available[:1]

# Remove selections that disappeared due to filters
st.session_state.brands = [b for b in st.session_state.brands if b in brands_available]

# Widget (state-controlled)
brands = st.sidebar.multiselect(
    "Brand",
    brands_available,
    key="brands"
)

df_plot = df_f[df_f["Brand"].isin(brands)]

# =====================================================
# METRIC SELECTORS
# =====================================================
st.sidebar.markdown("---")

metric_keys = list(METRICS.keys())

m1 = st.sidebar.selectbox(
    "Compare Metric (Solid)",
    metric_keys,
    index=metric_keys.index("Est. Category Share")
)

m2_options = [m for m in metric_keys if m != m1]

# Default dashed = Overall SOV (if available)
default_m2 = "Overall SOV" if "Overall SOV" in m2_options else m2_options[0]

m2 = st.sidebar.selectbox(
    "Baseline Metric (Dashed)",
    m2_options,
    index=m2_options.index(default_m2)
)

col1 = METRICS[m1]
col2 = METRICS[m2]

# =====================================================
# WARN MISSING BRANDS
# =====================================================
missing = set(brands) - set(df_plot["Brand"].unique())
if missing:
    st.caption("⚠️ Not available in selected filters: " + ", ".join(missing))

# =====================================================
# CHART
# =====================================================
st.title("Weekly SOV vs Share")

if df_plot.empty:
    st.stop()

df_plot = df_plot.sort_values("Date")
x_order = df_plot[["Week", "Date"]].drop_duplicates().sort_values("Date")["Week"]

colors = build_color_map(sorted(df_plot["Brand"].unique()))

fig = go.Figure()

for b in sorted(df_plot["Brand"].unique()):
    d = df_plot[df_plot["Brand"] == b]

    fig.add_trace(go.Scatter(
        x=d["Week"],
        y=d[col1],
        mode="lines+markers+text",
        text=[f"{v:.1f}%" for v in d[col1]],
        textposition="top center",
        name=f"{b} — {m1}",
        line=dict(color=colors[b], width=2),
    ))

    fig.add_trace(go.Scatter(
        x=d["Week"],
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
