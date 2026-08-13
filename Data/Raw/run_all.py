"""
Compatibility wrapper for moved `run_all.py`.

This file provides `PROCESSED` and `REPORTS` paths relative to
`Data/Raw/` so tests and any consumers relying on the original
location continue to work after the repository was reorganized.
"""
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROCESSED = SCRIPT_DIR / "processed"
REPORTS = SCRIPT_DIR / "reports"

# Note: This wrapper intentionally does not import or execute the
# implementation from `scripts/run_all.py` to avoid altering import
# semantics; it only exposes the paths the tests expect.
