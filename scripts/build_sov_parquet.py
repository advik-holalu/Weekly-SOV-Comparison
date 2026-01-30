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

# Columns we actually need
KEEP_COLS = [
    "Date",
    "Week",
    "Month",
    "Category",
    "City",
    "Brand",
    "Est. Category Share",
    "Est. Category Share SP",
    "Overall SOV",
    "Organic SOV",
    "Ad SOV",
]

# =====================================================
# LOAD + TAG PLATFORM
# =====================================================
dfs = []

for platform, path in FILES.items():
    print(f"Loading {platform} → {path.name}")

    df = pd.read_excel(path, sheet_name="Sheet1", engine="openpyxl")
    df.columns = df.columns.str.strip()

    # Platform column
    df["Platform"] = platform

    # Keep only required columns
    df = df[[*KEEP_COLS, "Platform"]]

    # Types
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

    for c in KEEP_COLS:
        if c not in ["Date", "Week", "Month", "Category", "City", "Brand"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    for c in ["Week", "Month", "Category", "City", "Brand", "Platform"]:
        df[c] = df[c].astype(str).str.strip()

    dfs.append(df)

# =====================================================
# MERGE ALL PLATFORMS
# =====================================================
full = pd.concat(dfs, ignore_index=True)

# Drop junk rows
full = full.dropna(subset=["Date", "Week", "Brand", "City", "Category"])

# =====================================================
# AGGREGATE TO WEEKLY BRAND LEVEL
# =====================================================
print("Aggregating...")

agg = (
    full.groupby(
        ["Date", "Week", "Month", "Platform", "Category", "City", "Brand"],
        as_index=False
    )
    .mean(numeric_only=True)
)

# =====================================================
# WRITE PARQUET
# =====================================================
OUT.parent.mkdir(exist_ok=True)

agg.to_parquet(OUT, index=False)

print("=================================================")
print(f"Saved → {OUT}")
print(f"Rows: {len(agg):,}")
print("Done.")
