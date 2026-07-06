import pandas as pd
from pathlib import Path

# =====================================================
# PATHS
# =====================================================
ROOT = Path(__file__).resolve().parents[1]

RAW = ROOT / "data_raw"
OUT = ROOT / "data_agg" / "sov_weekly.parquet"

FILES = {
    "Blinkit": RAW / "blinkit.xlsx",
    "Instamart": RAW / "instamart.xlsx",
    "Zepto": RAW / "zepto.xlsx",
}

# =====================================================
# REQUIRED COLUMNS (NEW SCHEMA)
# =====================================================
KEEP_COLS = [
    "Date",
    "Week",
    "Month",
    "Year",
    "Category",
    "City",
    "Brand",
    "Est. Category Share",
    "Est. Category Share SP",
    "Overall SOV",
    "Organic SOV",
    "Ad SOV",
]

NUMERIC_COLS = [
    "Est. Category Share",
    "Est. Category Share SP",
    "Overall SOV",
    "Organic SOV",
    "Ad SOV",
]

DIM_COLS = ["Week", "Month", "Year", "Category", "City", "Brand"]

# =====================================================
# LOAD + TAG PLATFORM
# =====================================================
dfs = []

for platform, path in FILES.items():
    print(f"Loading {platform} → {path.name}")

    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")

    df = pd.read_excel(path, sheet_name=0, engine="openpyxl")
    df.columns = df.columns.astype(str).str.strip()

    # Validate schema
    missing = [c for c in KEEP_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"{platform} missing columns: {missing}")

    # Keep only required columns
    df = df[KEEP_COLS].copy()

    # Platform column
    df["Platform"] = platform

    # Types
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Year"] = pd.to_numeric(df["Year"], errors="coerce")

    for c in NUMERIC_COLS:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    for c in DIM_COLS + ["Platform"]:
        df[c] = df[c].astype(str).str.strip()

    dfs.append(df)

# =====================================================
# MERGE ALL PLATFORMS
# =====================================================
full = pd.concat(dfs, ignore_index=True)

# Drop unusable rows
full = full.dropna(subset=["Date", "Week", "Brand", "City", "Category"])

# =====================================================
# WEEKLY BRAND AGGREGATION
# =====================================================
print("Aggregating weekly brand metrics...")

agg = (
    full.groupby(
        ["Date", "Week", "Month", "Year", "Platform", "Category", "City", "Brand"],
        as_index=False
    )
    .mean(numeric_only=True)
)

# Sort for deterministic output
agg = agg.sort_values(["Platform", "Category", "City", "Brand", "Date"])

# =====================================================
# WRITE PARQUET
# =====================================================
# =====================================================
# DIAGNOSTICS
# =====================================================
MONTH_ORDER = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}

print("\n================ YEAR / MONTH DIAGNOSTIC ================\n")

# Years present (Year is stored as a string in the parquet)
years_present = sorted(agg["Year"].dropna().unique(), key=lambda y: int(y))
print(f"Years in parquet: {[int(y) for y in years_present]}\n")

year_month_summary = (
    agg.groupby(["Year", "Month"])
       .size()
       .reset_index(name="Rows")
)
year_month_summary["MonthNum"] = year_month_summary["Month"].map(MONTH_ORDER)
year_month_summary = year_month_summary.sort_values(["Year", "MonthNum"])

for year in years_present:
    year_df = year_month_summary[year_month_summary["Year"] == year]
    months = year_df["Month"].tolist()
    print(f"Year: {int(year)}  ({len(months)} months: {', '.join(months)})")

    for _, row in year_df.iterrows():
        print(f"   {row['Month']:<4} → {row['Rows']:>7,} rows")
    print()

print("=========================================================\n")


# =====================================================
# WRITE PARQUET
# =====================================================
OUT.parent.mkdir(exist_ok=True)

agg.to_parquet(OUT, index=False)

print("Saved →", OUT)
print("Total Rows:", len(agg))
print("Done.")
