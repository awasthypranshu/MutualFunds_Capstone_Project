"""
clean_scheme_performance.py
----------------------------
Cleans 07_scheme_performance.csv.

Steps:
    1. Validate that all return / ratio columns are numeric (coerce, flag failures)
    2. Check expense_ratio_pct is within the plausible SEBI-style band 0.1% - 2.5%
    3. Flag statistical anomalies (outliers) in the return columns using an
       IQR-based rule -- flagged rows are KEPT (not dropped), since a real
       outlier fund (e.g. a small-cap fund with genuinely high returns) is
       valid data, not necessarily bad data. It's surfaced for manual review.
    4. Flag internal-consistency issues (e.g. rating out of 1-5 range,
       duplicate amfi_code, sharpe ratio null-but-std_dev present, etc.)

Run standalone:
    python clean_scheme_performance.py
"""

import pandas as pd
import numpy as np
from pathlib import Path

# Resolve file paths relative to this script so code works regardless of CWD
SCRIPT_DIR = Path(__file__).resolve().parent
RAW_PATH = SCRIPT_DIR / "07_scheme_performance.csv"
OUT_PATH = SCRIPT_DIR / "processed" / "scheme_performance_clean.csv"
LOG_PATH = SCRIPT_DIR / "reports" / "scheme_performance_dq_log.txt"

NUMERIC_COLS = [
    "return_1yr_pct", "return_3yr_pct", "return_5yr_pct", "benchmark_3yr_pct",
    "alpha", "beta", "sharpe_ratio", "sortino_ratio", "std_dev_ann_pct",
    "max_drawdown_pct", "aum_crore", "expense_ratio_pct",
]

EXPENSE_RATIO_MIN, EXPENSE_RATIO_MAX = 0.1, 2.5
RETURN_COLS_FOR_OUTLIERS = ["return_1yr_pct", "return_3yr_pct", "return_5yr_pct"]


def _flag_iqr_outliers(df: pd.DataFrame, col: str, k: float = 1.5) -> pd.Series:
    q1, q3 = df[col].quantile([0.25, 0.75])
    iqr = q3 - q1
    lower, upper = q1 - k * iqr, q3 + k * iqr
    return (df[col] < lower) | (df[col] > upper)


def clean_scheme_performance(raw_path: Path = RAW_PATH):
    log = []
    df = pd.read_csv(raw_path)
    log.append(f"Loaded {len(df):,} raw rows from {raw_path.name}")

    # --- 1. Validate numeric columns -------------------------------------
    non_numeric_report = {}
    for col in NUMERIC_COLS:
        coerced = pd.to_numeric(df[col], errors="coerce")
        n_bad = coerced.isna().sum() - df[col].isna().sum()  # newly-NaN = was non-numeric
        if n_bad > 0:
            non_numeric_report[col] = int(n_bad)
        df[col] = coerced

    if non_numeric_report:
        log.append(f"Non-numeric values coerced to NaN by column: {non_numeric_report}")
    else:
        log.append("All return/ratio/expense columns are numeric -- no coercion needed")

    still_null = df[NUMERIC_COLS].isna().sum()
    still_null = still_null[still_null > 0]
    if len(still_null):
        log.append(f"WARNING: nulls remaining after coercion: {still_null.to_dict()}")

    # --- 2. Expense ratio range check ------------------------------------
    df["expense_ratio_flag"] = ~df["expense_ratio_pct"].between(
        EXPENSE_RATIO_MIN, EXPENSE_RATIO_MAX
    )
    n_expense_flagged = df["expense_ratio_flag"].sum()
    if n_expense_flagged:
        bad_rows = df.loc[df["expense_ratio_flag"], ["amfi_code", "scheme_name", "expense_ratio_pct"]]
        log.append(
            f"Flagged {n_expense_flagged} schemes with expense_ratio_pct outside "
            f"[{EXPENSE_RATIO_MIN}, {EXPENSE_RATIO_MAX}]:\n{bad_rows.to_string(index=False)}"
        )
    else:
        log.append(f"expense_ratio_pct: all {len(df)} schemes within [{EXPENSE_RATIO_MIN}, {EXPENSE_RATIO_MAX}]%")

    # --- 3. Outlier flags on return columns (IQR rule, informational) -----
    df["return_outlier_flag"] = False
    for col in RETURN_COLS_FOR_OUTLIERS:
        mask = _flag_iqr_outliers(df, col)
        df["return_outlier_flag"] |= mask
        if mask.any():
            names = df.loc[mask, "scheme_name"].tolist()
            log.append(f"IQR outlier in {col}: {names}")
    if not df["return_outlier_flag"].any():
        log.append("No IQR-based return outliers detected")

    # --- 4. Consistency checks ---------------------------------------------
    dupe_codes = df["amfi_code"].duplicated().sum()
    if dupe_codes:
        log.append(f"WARNING: {dupe_codes} duplicate amfi_code values found")
    else:
        log.append("amfi_code: all values unique")

    bad_rating = ~df["morningstar_rating"].between(1, 5)
    if bad_rating.any():
        log.append(f"WARNING: {bad_rating.sum()} rows have morningstar_rating outside 1-5")

    # max_drawdown should be <= 0 (it's a loss figure); flag positive values
    bad_drawdown = df["max_drawdown_pct"] > 0
    if bad_drawdown.any():
        log.append(f"WARNING: {bad_drawdown.sum()} rows have a positive max_drawdown_pct (expected <= 0)")

    n_anomalies = int(df["expense_ratio_flag"].sum() + df["return_outlier_flag"].sum())
    log.append(f"Final row count: {len(df):,}  |  rows with >=1 flag: {(df['expense_ratio_flag'] | df['return_outlier_flag']).sum()}")

    return df, log


if __name__ == "__main__":
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    clean_df, log_lines = clean_scheme_performance()
    clean_df.to_csv(OUT_PATH, index=False)
    LOG_PATH.write_text("\n".join(log_lines) + "\n")

    print("\n".join(log_lines))
    print(f"\nSaved -> {OUT_PATH}")
