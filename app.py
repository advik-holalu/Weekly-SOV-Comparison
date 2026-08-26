import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path

st.set_page_config(
    page_title="Weekly SOV Dashboard",
    layout="wide",
    initial_sidebar_state="collapsed",
)

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

    # =====================================================
    # DERIVED COLUMNS (computed once here, then cached)
    # Moved out of the tab1 rerun path to avoid recomputing
    # over the full frame on every filter change.
    # =====================================================
    month_order = {
        "Jan": 1, "Feb": 2, "Mar": 3,
        "Apr": 4, "May": 5, "Jun": 6,
        "Jul": 7, "Aug": 8, "Sep": 9,
        "Oct": 10, "Nov": 11, "Dec": 12,
    }

    df["MonthNum"] = df["Month"].map(month_order)

    # Financial Year (Apr–Mar) — vectorized replacement for row-wise apply
    df["FY"] = df["Year"].where(df["MonthNum"] >= 4, df["Year"] - 1)

    # Financial Quarter — vectorized replacement for row-wise apply
    # Q1=Apr-Jun, Q2=Jul-Sep, Q3=Oct-Dec, Q4=Jan-Mar
    df["Quarter"] = np.select(
        [
            df["MonthNum"].isin([4, 5, 6]),
            df["MonthNum"].isin([7, 8, 9]),
            df["MonthNum"].isin([10, 11, 12]),
        ],
        ["Q1", "Q2", "Q3"],
        default="Q4",
    )

    df["FYQuarter"] = df["FY"].astype(str) + " - " + df["Quarter"]

    # =====================================================
    # DTYPE DOWNCAST (memory only — no change to values,
    # sort order, or filter option lists).
    # Week is intentionally left as string: it is used in
    # string concatenation for WeekLabel, which category
    # dtype would break.
    # =====================================================
    df["Year"] = df["Year"].astype("Int64")

    for c in ["Platform", "Category", "City", "Brand", "Month"]:
        df[c] = df[c].astype("category")

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
# BLINKIT BRANDED ROLLUPS
# Pre-summed total rows in BlinkitVS.xlsx. All 4 feed the Branded
# Summary chart. Only the 3 per-category sums are excluded from the
# working frame (they'd pollute the real Candies/Sweets/Snacks
# categories); the "GO DESi" brand-total row has its own unique
# "GO DESi" category, so it is KEPT in the working frame and surfaced
# as a selectable category too.
# =====================================================
BLINKIT_ROLLUPS = [
    "GO DESi Candies/POPz Branded Keywords",
    "GO DESi Sweets Branded Keywords",
    "GO DESi Snacks Branded Keywords",
    "GO DESi",
]
BLINKIT_ROLLUP_NAMES_LOWER = {r.strip().lower() for r in BLINKIT_ROLLUPS}

# Rows removed from the working (per-keyword) frame: the 3 per-category
# sums only — NOT the "GO DESi" brand total.
BLINKIT_MAIN_EXCLUDE_LOWER = {
    r.strip().lower() for r in BLINKIT_ROLLUPS if r.strip().lower() != "go desi"
}


# =====================================================
# TABS
# Blinkit is listed first so it is the default-open tab.
# =====================================================
tab_blinkit, tab_sov = st.tabs(["Blinkit Volume Share", "SOV vs Market Share"])


# =====================================================
# ====================== SOV TAB =======================
# =====================================================
with tab_sov:

    # =====================================================
    # FILTERS (inline — moved out of the global sidebar so they do
    # not bleed across tabs). Widget logic, order of application,
    # defaults, keys, and cascading option-narrowing are unchanged;
    # only the container (sidebar -> tab body) and layout differ.
    # =====================================================
    with st.expander("Filters", expanded=True):

        # df_f carries the derived columns (MonthNum, FY, Quarter,
        # FYQuarter) from the cached load_data() — no recompute here.
        df_f = df.copy()

        frow1_c1, frow1_c2, frow1_c3 = st.columns(3)

        # ---- FINANCIAL YEAR (MULTI + SELECT ALL) ----
        with frow1_c1:
            fy_opts = sorted(df_f["FY"].dropna().unique())

            # Display labels → FY25, FY26
            fy_display = [f"FY{str(int(y))[-2:]}" for y in fy_opts]

            # Map display → actual FY value
            fy_map = dict(zip(fy_display, fy_opts))

            fy_display_with_all = ["Select All"] + fy_display

            selected_fy_display = st.multiselect(
                "Financial Year",
                fy_display_with_all,
                default=["Select All"]
            )

            if "Select All" in selected_fy_display:
                selected_fy = fy_opts
            else:
                selected_fy = [fy_map[x] for x in selected_fy_display]

        df_f = df_f[df_f["FY"].isin(selected_fy)]

        # ---- PLATFORM ----
        with frow1_c2:
            platform_opts = sorted(df["Platform"].unique())

            platform_display = ["Select All"] + platform_opts

            selected_platform = st.multiselect(
                "Platform",
                platform_display,
                default=["Zepto"] if "Zepto" in platform_opts else ["Select All"]
            )

            if "Select All" in selected_platform:
                platform = platform_opts
            else:
                platform = selected_platform

        df_f = df_f[df_f["Platform"].isin(platform)]

        # ---- CATEGORY ----
        with frow1_c3:
            cat_opts = sorted(df_f["Category"].unique())

            cat_display = ["Select All"] + cat_opts

            selected_category = st.multiselect(
                "Category",
                cat_display,
                default=["Indian Sweets"] if "Indian Sweets" in cat_opts else ["Select All"]
            )

            if "Select All" in selected_category:
                category = cat_opts
            else:
                category = selected_category

        df_f = df_f[df_f["Category"].isin(category)]

        frow2_c1, frow2_c2, frow2_c3 = st.columns(3)

        # ---- CITY ----
        with frow2_c1:
            city_opts = sorted(df_f["City"].unique())

            city_display = ["Select All"] + city_opts

            default_city = (
                ["PAN India"] if "PAN India" in city_opts
                else ["Bangalore"] if "Bangalore" in city_opts
                else ["Select All"]
            )

            selected_city = st.multiselect(
                "City",
                city_display,
                default=default_city
            )

            if "Select All" in selected_city:
                city = city_opts
            else:
                city = selected_city

        df_f = df_f[df_f["City"].isin(city)]

        # ---- QUARTER (DEFAULT = ALL) ----
        with frow2_c2:
            quarter_opts = (
                df_f[["FYQuarter", "Date"]]
                .drop_duplicates()
                .sort_values("Date")
            )["FYQuarter"].unique().tolist()

            quarter_display = ["Select All"] + quarter_opts

            selected_quarters = st.multiselect(
                "Quarter (Financial Year)",
                quarter_display,
                default=["Select All"]
            )

            if "Select All" in selected_quarters:
                quarters = quarter_opts
            else:
                quarters = selected_quarters

        df_f = df_f[df_f["FYQuarter"].isin(quarters)]

        # ---- MONTH (DEFAULT = ALL) ----
        with frow2_c3:
            month_opts = (
                df_f[["Month", "MonthNum"]]
                .drop_duplicates()
                .sort_values("MonthNum")
            )["Month"].tolist()

            month_display = ["Select All"] + month_opts

            selected_months = st.multiselect(
                "Month",
                month_display,
                default=["Select All"]
            )

            if "Select All" in selected_months:
                months = month_opts
            else:
                months = selected_months

        df_f = df_f[df_f["Month"].isin(months)]

        # ---- BRAND ----
        brands_available = sorted(df_f["Brand"].unique())

        if "brands" not in st.session_state:
            if GO_DESI in brands_available:
                st.session_state.brands = [GO_DESI]
            else:
                st.session_state.brands = brands_available[:1]

        st.session_state.brands = [b for b in st.session_state.brands if b in brands_available]

        brands = st.multiselect(
            "Brand",
            brands_available,
            key="brands"
        )

        df_plot = df_f[df_f["Brand"].isin(brands)]

        # ---- METRICS ----
        st.divider()

        metric_keys = list(METRICS.keys())

        mcol1, mcol2 = st.columns(2)

        with mcol1:
            m1 = st.selectbox(
                "Compare Metric (Solid)",
                metric_keys,
                index=metric_keys.index("Est. Category Share")
            )

        m2_options = [m for m in metric_keys if m != m1]

        default_m2 = "Overall SOV" if "Overall SOV" in m2_options else m2_options[0]

        with mcol2:
            m2 = st.selectbox(
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
# ==================== BLINKIT TAB =====================
# =====================================================
with tab_blinkit:
    st.title("Blinkit Volume Share")

    df = load_blinkit().copy()

    # =========================
    # SPLIT OUT BRANDED ROLLUP TOTALS
    # Match by keyword name (case-insensitive), never by row position.
    #  - df_rollups: all 4 pre-summed totals -> Branded Summary chart.
    #  - working df: excludes only the 3 per-category sums; the "GO DESi"
    #    brand-total row is KEPT so it appears as its own Category.
    # =========================
    _kw_norm = df["Keyword"].astype(str).str.strip().str.lower()
    _is_rollup = _kw_norm.isin(BLINKIT_ROLLUP_NAMES_LOWER)
    _is_main_excluded = _kw_norm.isin(BLINKIT_MAIN_EXCLUDE_LOWER)

    df_rollups = df[_is_rollup].copy()
    df = df[~_is_main_excluded].copy()

    # =========================
    # SEED DEFAULT FILTER STATE — ONCE PER SESSION (DoD dashboard).
    # Seed via the widgets' session_state keys (not default=) behind a
    # flag, so later reruns keep whatever the user has since selected —
    # including a deliberately cleared filter — instead of snapping back.
    #   Category = Indian Sweets + GO DESi, Keyword Type = Competition
    #   + Branded (Branded so the GO DESi brand-total is visible on load),
    #   Keyword = empty (empty => all keywords matching Category+Type).
    # =========================
    if "blinkit_filters_seeded" not in st.session_state:
        st.session_state["blinkit_category"] = ["Indian Sweets", "GO DESi"]
        st.session_state["blinkit_ktype"] = ["Competition", "Branded"]
        st.session_state["blinkit_keyword"] = []
        st.session_state["blinkit_filters_seeded"] = True

    # =========================
    # FILTERS (inline at the TOP, in an expander — consistent with the
    # SOV tab. Kept above the charts so changing a filter doesn't cause
    # the tall charts to re-render above the control and jump the page.
    # Widgets, defaults, and order of application are unchanged.
    # =========================
    with st.expander("Filters", expanded=True):

        col1, col2 = st.columns(2)

        # CATEGORY  (default seeded via session_state key)
        with col1:
            category = st.multiselect(
                "Category",
                sorted(df["Category"].unique()),
                key="blinkit_category",
            )

        # KEYWORD TYPE  (default seeded via session_state key)
        with col2:
            keyword_type_opts = sorted(df["Keyword Type"].unique())
            keyword_type_display = ["All"] + keyword_type_opts

            selected_keyword_type = st.multiselect(
                "Keyword Type",
                keyword_type_display,
                key="blinkit_ktype",
            )

            if "All" in selected_keyword_type:
                keyword_type = keyword_type_opts
            else:
                keyword_type = selected_keyword_type

        df = df[df["Category"].isin(category)]
        df = df[df["Keyword Type"].isin(keyword_type)]

        col3, col4 = st.columns(2)

        # KEYWORD  (default seeded empty; empty => all matching keywords)
        with col3:
            keyword_opts = sorted(df["Keyword"].unique())

            selected_keywords = st.multiselect(
                "Keyword",
                keyword_opts,
                key="blinkit_keyword",
            )

            # Empty selection means "all keywords matching Category +
            # Keyword Type" — so the growth table and All-Keywords chart
            # open on the full set, not a single keyword.
            keywords = selected_keywords if selected_keywords else keyword_opts

        # WEEK  (unchanged default = All)
        with col4:
            week_cols = [c for c in df.columns if "W" in c]
            week_display = ["All"] + week_cols

            selected_weeks = st.multiselect(
                "Week",
                week_display,
                default=["All"],
                key="blinkit_week",
            )

            if "All" in selected_weeks:
                selected_weeks = week_cols

        df = df[df["Keyword"].isin(keywords)]

    # Reserve slots BELOW the filters, filled at the end of this block
    # so they can reuse week_sort() and the finalized filtered frame.
    # Order = creation order:
    #   1) Growth / de-growth table   2) Branded Summary chart
    # both ABOVE the All-Keywords chart.
    growth_container = st.container()
    summary_container = st.container()

    # =========================
    # TRANSFORM
    # =========================
    df_melt = df.melt(
        id_vars=["Category", "Keyword Type", "Keyword"],
        value_vars=selected_weeks,
        var_name="Week",
        value_name="Searches"
    )

    # ---- CLEAN NUMBERS (IMPORTANT FIX) ----
    df_melt["Searches"] = (
        df_melt["Searches"]
        .astype(str)
        .str.replace(",", "", regex=False)
        .replace("-", None)
    )

    df_melt["Searches"] = pd.to_numeric(df_melt["Searches"], errors="coerce")

    # =========================
    # SORT WEEKS PROPERLY
    # =========================
    def week_sort(w):
        try:
            parts = w.split()
            month_year = parts[0]
            week = int(parts[1].replace("W", ""))

            month_map = {
                "Jan": 1, "Feb": 2, "Mar": 3,
                "Apr": 4, "May": 5, "Jun": 6,
                "Jul": 7, "Aug": 8, "Sep": 9,
                "Oct": 10, "Nov": 11, "Dec": 12
            }

            month = month_map[month_year[:3]]
            year = int("20" + month_year[3:])

            return (year, month, week)
        except:
            return (0, 0, 0)

    df_melt["sort_key"] = df_melt["Week"].apply(week_sort)
    df_melt = df_melt.sort_values("sort_key")

    # =========================
    # PLOT
    # =========================
    fig = go.Figure()

    for k in keywords:
        d = df_melt[df_melt["Keyword"] == k].copy()

        # drop missing values only (after fixing parsing)
        d = d.dropna(subset=["Searches"])

        fig.add_trace(go.Scatter(
            x=d["Week"],
            y=d["Searches"],
            mode="lines+markers+text",
            text=[
                f"{int(v):,}" if pd.notna(v) else ""
                for v in d["Searches"]
            ],
            textposition="top center",
            name=k,
            line=dict(width=3)
        ))

    # enforce correct x order
    x_order = df_melt["Week"].drop_duplicates().tolist()

    fig.update_layout(
        height=600,
        yaxis_title="Search Volume",
        xaxis_title="Week",
        xaxis=dict(categoryorder="array", categoryarray=x_order),
        legend=dict(orientation="h", y=-0.2),
    )

    st.plotly_chart(fig, use_container_width=True)

    # =========================
    # BRANDED SUMMARY KEYWORDS (unfiltered — 4 rollup rows only)
    # Rendered in the slot reserved above, so it appears ABOVE the
    # All-Keywords chart. Uses df_rollups directly (never the filtered
    # frame) and reuses week_sort() + the same melt→clean→sort pipeline.
    # =========================
    with summary_container:
        st.subheader("Branded Summary Keywords")
        st.caption(
            "**Note:** this graph is not affected by any of the filters. "
            "The **All Keywords** graph below it is."
        )

        if df_rollups.empty:
            st.info("None of the branded summary keywords are in the sheet.")
        else:
            # Plot ALL week columns in the file (ignore the Week filter)
            rollup_week_cols = [c for c in df_rollups.columns if "W" in c]

            rollup_melt = df_rollups.melt(
                id_vars=["Category", "Keyword Type", "Keyword"],
                value_vars=rollup_week_cols,
                var_name="Week",
                value_name="Searches"
            )

            # ---- CLEAN NUMBERS (same as existing chart) ----
            rollup_melt["Searches"] = (
                rollup_melt["Searches"]
                .astype(str)
                .str.replace(",", "", regex=False)
                .replace("-", None)
            )

            rollup_melt["Searches"] = pd.to_numeric(
                rollup_melt["Searches"], errors="coerce"
            )

            # ---- SORT WEEKS (reuse existing week_sort) ----
            rollup_melt["sort_key"] = rollup_melt["Week"].apply(week_sort)
            rollup_melt = rollup_melt.sort_values("sort_key")

            fig_rollup = go.Figure()

            for k in df_rollups["Keyword"].tolist():
                d = rollup_melt[rollup_melt["Keyword"] == k].copy()

                d = d.dropna(subset=["Searches"])

                fig_rollup.add_trace(go.Scatter(
                    x=d["Week"],
                    y=d["Searches"],
                    mode="lines+markers+text",
                    text=[
                        f"{int(v):,}" if pd.notna(v) else ""
                        for v in d["Searches"]
                    ],
                    textposition="top center",
                    name=k,
                    line=dict(width=3)
                ))

            # enforce correct x order
            x_order = rollup_melt["Week"].drop_duplicates().tolist()

            fig_rollup.update_layout(
                height=600,
                yaxis_title="Search Volume",
                xaxis_title="Week",
                xaxis=dict(categoryorder="array", categoryarray=x_order),
                legend=dict(orientation="h", y=-0.2),
            )

            st.plotly_chart(fig_rollup, use_container_width=True)

            st.caption(f"{len(df_rollups)} keywords plotted, one colour each.")

    # =========================
    # GROWTH / DE-GROWTH TABLE (last two weeks)
    # Rendered in the slot reserved at the top, so it sits ABOVE the
    # Branded Summary chart. Respects the Category / Keyword Type /
    # Keyword filters (uses the filtered non-rollup `df`) but IGNORES
    # the Week multiselect — it always compares the two most recent
    # week columns, ordered chronologically via week_sort().
    # =========================
    with growth_container:
        st.subheader("Growth / de-growth")

        growth_week_cols = sorted(
            [c for c in df.columns if "W" in c], key=week_sort
        )

        if len(growth_week_cols) < 2:
            st.info("Need at least two weeks of data to compare.")
        else:
            prev_week = growth_week_cols[-2]
            latest_week = growth_week_cols[-1]

            def _clean_week(col):
                return pd.to_numeric(
                    col.astype(str).str.replace(",", "", regex=False).replace("-", None),
                    errors="coerce",
                )

            prev_num = _clean_week(df[prev_week])
            latest_num = _clean_week(df[latest_week])

            prev_z = prev_num.fillna(0)
            latest_z = latest_num.fillna(0)

            # Drop rows where both weeks are NaN/0 (nothing to say)
            keep = ~((prev_z == 0) & (latest_z == 0))

            abs_change = latest_z - prev_z

            # Change % as a NUMBER: growth vs prev; inf ("New") when
            # prev is 0/NaN but latest > 0; NaN when both effectively 0.
            chg = pd.Series(np.nan, index=df.index, dtype="float64")
            pos = prev_z > 0
            chg[pos] = (latest_z[pos] - prev_z[pos]) / prev_z[pos] * 100
            chg[(prev_z == 0) & (latest_z > 0)] = np.inf

            prev_label = f"Prev ({prev_week})"
            latest_label = f"Latest ({latest_week})"

            table = pd.DataFrame({
                "Category": df["Category"],
                "Keyword Type": df["Keyword Type"],
                "Keyword": df["Keyword"],
                prev_label: prev_num,
                latest_label: latest_num,
                "Absolute Change": abs_change,
                "Change %": chg,
            })[keep]

            table = (
                table
                .sort_values("Change %", ascending=False, na_position="last")
                .reset_index(drop=True)
            )

            n = len(table)

            if n == 0:
                st.info("No rows to compare for the current filters.")
            else:
                up = int((table["Change %"] > 0).sum())
                down = int((table["Change %"] < 0).sum())

                st.caption(
                    f"{n} keywords, {prev_week} to {latest_week} — "
                    f"{up} up, {down} down. Sorted by Change % descending; "
                    "click any column header to re-sort."
                )

                # Scale shading intensity to magnitude vs the 90th
                # percentile of finite absolute moves this week.
                finite_moves = (
                    table["Change %"]
                    .replace([np.inf, -np.inf], np.nan)
                    .dropna()
                    .abs()
                )
                p90 = float(np.percentile(finite_moves, 90)) if len(finite_moves) else 0.0

                def _shade(row):
                    v = row["Change %"]
                    if pd.isna(v):
                        return [""] * len(row)
                    if np.isinf(v):  # "New" — distinct colour
                        return ["background-color: rgba(37, 99, 235, 0.28)"] * len(row)
                    if v == 0:
                        return [""] * len(row)
                    mag = min(1.0, abs(v) / p90) if p90 > 0 else 1.0
                    alpha = 0.10 + 0.35 * mag
                    rgb = "22, 163, 74" if v > 0 else "220, 38, 38"
                    return [f"background-color: rgba({rgb}, {alpha:.3f})"] * len(row)

                def _fmt_int(v):
                    return "—" if pd.isna(v) else f"{v:,.0f}"

                def _fmt_signed(v):
                    return "—" if pd.isna(v) else f"{v:+,.0f}"

                def _fmt_pct(v):
                    if pd.isna(v):
                        return "—"
                    if np.isinf(v):
                        return "New"
                    return f"{v:.1f}%"

                styler = (
                    table.style
                    .apply(_shade, axis=1)
                    .format({
                        prev_label: _fmt_int,
                        latest_label: _fmt_int,
                        "Absolute Change": _fmt_signed,
                        "Change %": _fmt_pct,
                    })
                )

                st.dataframe(styler, use_container_width=True, hide_index=True)