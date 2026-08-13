"""
clean_nav_history.py
---------------------
Cleans 02_nav_history.csv (AMFI daily NAV data pulled from mfapi.in).

Steps:
    1. Parse `date` to datetime
    2. Sort by amfi_code + date
    3. Remove exact duplicate rows and duplicate (amfi_code, date) keys
    4. Validate nav > 0 (invalid rows are dropped, not silently kept)
    5. Reindex each scheme to a full daily calendar and forward-fill NAV
       across non-trading days (weekends/holidays) -- this is what
       "forward-fill missing NAV" means here, since mfapi.in only returns
       NAV for actual trading days.
    6. Write cleaned CSV + a data-quality log.

Run standalone:
    python clean_nav_history.py
"""

import pandas as pd
import numpy as np
from pathlib import Path

# Resolve file paths relative to this script so code works regardless of CWD
SCRIPT_DIR = Path(__file__).resolve().parent
RAW_PATH = SCRIPT_DIR / "02_nav_history.csv"
OUT_PATH = SCRIPT_DIR / "processed" / "nav_history_clean.csv"
LOG_PATH = SCRIPT_DIR / "reports" / "nav_history_dq_log.txt"


def clean_nav_history(raw_path: Path = RAW_PATH) -> tuple[pd.DataFrame, list[str]]:
    log = []
    df = pd.read_csv(raw_path)
    log.append(f"Loaded {len(df):,} raw rows from {raw_path.name}")

    # --- 1. Parse dates -----------------------------------------------
    # dayfirst=False because the source format is ISO (YYYY-MM-DD);
    # errors='coerce' turns unparseable dates into NaT so we can catch them
    # instead of crashing.
    before = len(df)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    bad_dates = df["date"].isna().sum()
    if bad_dates:
        log.append(f"Dropped {bad_dates} rows with unparseable dates")
        df = df.dropna(subset=["date"])

    # --- 2. Validate NAV > 0 -------------------------------------------
    df["nav"] = pd.to_numeric(df["nav"], errors="coerce")
    invalid_nav = df["nav"].isna() | (df["nav"] <= 0)
    n_invalid = invalid_nav.sum()
    if n_invalid:
        log.append(f"Dropped {n_invalid} rows with non-numeric or non-positive NAV")
        df = df[~invalid_nav]

    # --- 3. Remove duplicates ------------------------------------------
    full_dupes = df.duplicated().sum()
    df = df.drop_duplicates()

    # duplicate (amfi_code, date) with conflicting NAV values -> keep last
    key_dupes = df.duplicated(subset=["amfi_code", "date"], keep=False).sum()
    if key_dupes:
        log.append(
            f"Found {key_dupes} rows sharing an (amfi_code, date) key "
            "(after exact-dup removal) -- keeping the last occurrence"
        )
    df = df.drop_duplicates(subset=["amfi_code", "date"], keep="last")
    log.append(f"Removed {full_dupes} exact duplicate rows")

    # --- 4. Sort ---------------------------------------------------------
    df = df.sort_values(["amfi_code", "date"]).reset_index(drop=True)

    # --- 5. Forward-fill across the full calendar per scheme -------------
    filled_frames = []
    total_filled = 0
    for code, g in df.groupby("amfi_code", sort=False):
        g = g.set_index("date").sort_index()
        full_range = pd.date_range(g.index.min(), g.index.max(), freq="D")
        g_full = g.reindex(full_range)
        n_added = g_full["nav"].isna().sum()
        total_filled += n_added
        g_full["nav"] = g_full["nav"].ffill()
        g_full["amfi_code"] = code
        g_full["is_forward_filled"] = g_full.index.isin(g.index) == False  # noqa: E712
        g_full = g_full.reset_index().rename(columns={"index": "date"})
        filled_frames.append(g_full)

    result = pd.concat(filled_frames, ignore_index=True)
    result = result[["amfi_code", "date", "nav", "is_forward_filled"]]
    log.append(
        f"Reindexed to full daily calendar per scheme; "
        f"forward-filled {total_filled:,} non-trading-day gaps"
    )

    # Any NAV still null means the very first day for that scheme had no
    # value to ffill from -- flag rather than silently drop.
    leading_gaps = result["nav"].isna().sum()
    if leading_gaps:
        log.append(
            f"WARNING: {leading_gaps} rows still null after ffill "
            "(gap at the very start of a scheme's history)"
        )

    log.append(f"Final clean row count: {len(result):,} (schemes: {result['amfi_code'].nunique()})")
    return result, log


if __name__ == "__main__":
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    clean_df, log_lines = clean_nav_history()
    clean_df.to_csv(OUT_PATH, index=False)
    LOG_PATH.write_text("\n".join(log_lines) + "\n")

    print("\n".join(log_lines))
    print(f"\nSaved -> {OUT_PATH}")
