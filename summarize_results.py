"""Backward-compatible import shim."""

from importlib import import_module
from pathlib import Path
import sys


SRC_DIR = Path(__file__).resolve().parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

_MODULE = import_module("pqccn_strongswan.analysis.summarize_results")
globals().update(
    {
        name: getattr(_MODULE, name)
        for name in dir(_MODULE)
        if not (name.startswith("__") and name.endswith("__"))
    }
)
