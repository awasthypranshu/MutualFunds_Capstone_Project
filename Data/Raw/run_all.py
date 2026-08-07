"""
run_all.py
----------
Runs all three cleaning steps and writes a combined data-quality summary.

Usage:
    python run_all.py
"""

import sys
from pathlib import Path

# Use script directory for relative paths so run_all works from any CWD
SCRIPT_DIR = Path(__file__).resolve().parent

# Quick dependency check so users get a helpful message when packages
# (like pandas) are not installed in the active interpreter.
REQUIRED_PACKAGES = ("pandas", "numpy")
missing = []
for pkg in REQUIRED_PACKAGES:
    try:
        __import__(pkg)
    except Exception:
        missing.append(pkg)

if missing:
    print("Missing required Python packages:", ", ".join(missing))
    print("Install them with:")
    print("  python -m pip install -r requirements.txt")
    print("Or activate your virtualenv and install the same requirements.")
    sys.exit(1)

from clean_nav_history import clean_nav_history
from clean_investor_transactions import clean_investor_transactions
from clean_scheme_performance import clean_scheme_performance

PROCESSED = SCRIPT_DIR / "processed"
REPORTS = SCRIPT_DIR / "reports"


def main():
    PROCESSED.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)

    summary = ["MUTUAL FUND DATA CLEANING -- SUMMARY", "=" * 40, ""]

    # 1. NAV history
    nav_df, nav_log = clean_nav_history()
    nav_df.to_csv(PROCESSED / "nav_history_clean.csv", index=False)
    summary += ["## 02_nav_history.csv", *[f"  - {l}" for l in nav_log], ""]

    # 2. Investor transactions
    txn_df, txn_rejects, txn_log = clean_investor_transactions()
    txn_df.to_csv(PROCESSED / "investor_transactions_clean.csv", index=False)
    txn_rejects.to_csv(PROCESSED / "investor_transactions_rejected.csv", index=False)
    summary += ["## 08_investor_transactions.csv", *[f"  - {l}" for l in txn_log], ""]

    # 3. Scheme performance
    perf_df, perf_log = clean_scheme_performance()
    perf_df.to_csv(PROCESSED / "scheme_performance_clean.csv", index=False)
    summary += ["## 07_scheme_performance.csv", *[f"  - {l}" for l in perf_log], ""]

    (REPORTS / "combined_dq_summary.txt").write_text("\n".join(summary) + "\n")
    print("\n".join(summary))
    print("All cleaned files written to processed/, logs written to reports/")


if __name__ == "__main__":
    main()
