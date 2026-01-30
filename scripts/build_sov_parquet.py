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

DIM_COLS = ["Week", "Month", "Category", "City", "Brand"]

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
        ["Date", "Week", "Month", "Platform", "Category", "City", "Brand"],
        as_index=False
    )
    .mean(numeric_only=True)
)

# Sort for deterministic output
agg = agg.sort_values(["Platform", "Category", "City", "Brand", "Date"])

# =====================================================
# WRITE PARQUET
# =====================================================
OUT.parent.mkdir(exist_ok=True)

agg.to_parquet(OUT, index=False)

print("=================================================")
print(f"Saved → {OUT}")
print(f"Rows: {len(agg):,}")
print("Done.")
