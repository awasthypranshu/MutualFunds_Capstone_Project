from importlib.util import spec_from_file_location, module_from_spec
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_module(rel_path: str, name: str):
    path = REPO_ROOT / rel_path
    spec = spec_from_file_location(name, str(path))
    mod = module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_clean_nav_history_paths():
    mod = _load_module('Data/Raw/clean_nav_history.py', 'clean_nav_history')
    script_dir = Path(mod.__file__).resolve().parent
    assert mod.RAW_PATH.parent == script_dir
    assert mod.OUT_PATH.parent == script_dir / 'processed'


def test_investor_transactions_paths():
    mod = _load_module('Data/Raw/clean_investor_transactions.py', 'clean_investor_transactions')
    script_dir = Path(mod.__file__).resolve().parent
    assert mod.RAW_PATH.parent == script_dir
    assert mod.REJECTS_PATH.parent == script_dir / 'processed'


def test_scheme_performance_paths():
    mod = _load_module('Data/Raw/clean_scheme_performance.py', 'clean_scheme_performance')
    script_dir = Path(mod.__file__).resolve().parent
    assert mod.RAW_PATH.parent == script_dir
    assert mod.OUT_PATH.parent == script_dir / 'processed'


def test_run_all_paths():
    mod = _load_module('Data/Raw/run_all.py', 'run_all')
    script_dir = Path(mod.__file__).resolve().parent
    assert mod.PROCESSED.parent == script_dir
    assert mod.REPORTS.parent == script_dir
