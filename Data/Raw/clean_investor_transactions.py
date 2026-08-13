"""
clean_investor_transactions.py
-------------------------------
Cleans 08_investor_transactions.csv.

Steps:
    1. Standardise transaction_type to {SIP, Lumpsum, Redemption}
    2. Fix date formats -> proper datetime (handles mixed formats defensively)
    3. Validate amount_inr > 0
    4. Check kyc_status against allowed enum {Verified, Pending, Rejected}
    5. Log every row that had to be corrected or dropped, instead of
       silently mutating data.

Run standalone:
    python clean_investor_transactions.py
"""

import pandas as pd
import numpy as np
from pathlib import Path

# Resolve file paths relative to this script so code works regardless of CWD
SCRIPT_DIR = Path(__file__).resolve().parent
RAW_PATH = SCRIPT_DIR / "08_investor_transactions.csv"
OUT_PATH = SCRIPT_DIR / "processed" / "investor_transactions_clean.csv"
REJECTS_PATH = SCRIPT_DIR / "processed" / "investor_transactions_rejected.csv"
LOG_PATH = SCRIPT_DIR / "reports" / "investor_transactions_dq_log.txt"

# Canonical values + common variants seen in messy source exports.
# Keys are lowercased/stripped for matching; values are the canonical label.
TRANSACTION_TYPE_MAP = {
    "sip": "SIP",
    "systematic investment plan": "SIP",
    "lumpsum": "Lumpsum",
    "lump sum": "Lumpsum",
    "lump-sum": "Lumpsum",
    "one time": "Lumpsum",
    "one-time": "Lumpsum",
    "redemption": "Redemption",
    "redeem": "Redemption",
    "withdrawal": "Redemption",
}

VALID_KYC_STATUSES = {"Verified", "Pending", "Rejected"}


def _standardise_transaction_type(series: pd.Series) -> pd.Series:
    normalised = series.astype(str).str.strip().str.lower()
    mapped = normalised.map(TRANSACTION_TYPE_MAP)
    return mapped


def clean_investor_transactions(raw_path: Path = RAW_PATH):
    log = []
    df = pd.read_csv(raw_path)
    log.append(f"Loaded {len(df):,} raw rows from {raw_path.name}")
    rejected_frames = []

    # --- 1. Standardise transaction_type --------------------------------
    original_type = df["transaction_type"].copy()
    df["transaction_type"] = _standardise_transaction_type(df["transaction_type"])
    bad_type_mask = df["transaction_type"].isna()
    if bad_type_mask.any():
        bad_values = sorted(original_type[bad_type_mask].unique())
        log.append(
            f"Found {bad_type_mask.sum()} rows with unrecognised transaction_type "
            f"values {bad_values} -> moved to rejects"
        )
        rejected_frames.append(df[bad_type_mask].assign(reject_reason="invalid_transaction_type"))
        df = df[~bad_type_mask]
    else:
        log.append("transaction_type: all values already valid (SIP / Lumpsum / Redemption)")

    # --- 2. Fix date formats ---------------------------------------------
    # Try the expected ISO format first (fast path); fall back to flexible
    # parsing per-row for anything that doesn't match, so mixed formats in
    # future data pulls don't silently corrupt dates.
    parsed = pd.to_datetime(df["transaction_date"], format="%Y-%m-%d", errors="coerce")
    still_bad = parsed.isna()
    if still_bad.any():
        fallback = pd.to_datetime(
            df.loc[still_bad, "transaction_date"], errors="coerce", dayfirst=True
        )
        parsed.loc[still_bad] = fallback
        recovered = still_bad.sum() - parsed[still_bad].isna().sum()
        if recovered:
            log.append(f"Recovered {recovered} dates using flexible day-first parsing")
    df["transaction_date"] = parsed

    unparseable = df["transaction_date"].isna()
    if unparseable.any():
        log.append(f"Dropped {unparseable.sum()} rows with unparseable transaction_date")
        rejected_frames.append(df[unparseable].assign(reject_reason="unparseable_date"))
        df = df[~unparseable]
    else:
        log.append("transaction_date: all values parsed successfully")

    # Flag (don't drop) transactions dated in the future relative to today
    future_dates = df["transaction_date"] > pd.Timestamp.today().normalize()
    if future_dates.any():
        log.append(f"WARNING: {future_dates.sum()} rows have a transaction_date in the future")

    # --- 3. Validate amount_inr > 0 ---------------------------------------
    df["amount_inr"] = pd.to_numeric(df["amount_inr"], errors="coerce")
    bad_amount = df["amount_inr"].isna() | (df["amount_inr"] <= 0)
    if bad_amount.any():
        log.append(f"Found {bad_amount.sum()} rows with non-numeric or non-positive amount_inr -> moved to rejects")
        rejected_frames.append(df[bad_amount].assign(reject_reason="invalid_amount"))
        df = df[~bad_amount]
    else:
        log.append("amount_inr: all values are valid positive numbers")

    # --- 4. Check kyc_status enum -------------------------------------------
    df["kyc_status"] = df["kyc_status"].astype(str).str.strip().str.title()
    bad_kyc = ~df["kyc_status"].isin(VALID_KYC_STATUSES)
    if bad_kyc.any():
        bad_values = sorted(df.loc[bad_kyc, "kyc_status"].unique())
        log.append(
            f"Found {bad_kyc.sum()} rows with kyc_status outside "
            f"{sorted(VALID_KYC_STATUSES)}: {bad_values} -> moved to rejects"
        )
        rejected_frames.append(df[bad_kyc].assign(reject_reason="invalid_kyc_status"))
        df = df[~bad_kyc]
    else:
        log.append(f"kyc_status: all values within {sorted(VALID_KYC_STATUSES)}")

    # --- 5. Duplicate check -------------------------------------------------
    dupes = df.duplicated().sum()
    if dupes:
        log.append(f"Dropped {dupes} exact duplicate rows")
        df = df.drop_duplicates()

    df = df.sort_values(["transaction_date", "investor_id"]).reset_index(drop=True)

    rejects = (
        pd.concat(rejected_frames, ignore_index=True)
        if rejected_frames
        else pd.DataFrame(columns=list(df.columns) + ["reject_reason"])
    )

    log.append(f"Final clean row count: {len(df):,}  |  rejected: {len(rejects):,}")
    return df, rejects, log


if __name__ == "__main__":
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    clean_df, rejects_df, log_lines = clean_investor_transactions()
    clean_df.to_csv(OUT_PATH, index=False)
    rejects_df.to_csv(REJECTS_PATH, index=False)
    LOG_PATH.write_text("\n".join(log_lines) + "\n")

    print("\n".join(log_lines))
    print(f"\nSaved -> {OUT_PATH}")
    print(f"Rejects -> {REJECTS_PATH}")
