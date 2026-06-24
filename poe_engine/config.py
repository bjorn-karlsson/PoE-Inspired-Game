"""Global configuration constants for the engine."""

from pathlib import Path

# Number of decimal places used when rounding stat values.
ROUND_DECIMALS = 1

# Resistances are capped here by default (classic ARPG 75% max res).
DEFAULT_MAX_RESISTANCE = 75


def _find_data_dir() -> Path:
    """Locate the bundled game data.

    The data lives next to this package (``poe_engine/data``).  We also fall
    back to a couple of legacy locations so the engine keeps working if the
    data has not been relocated yet (e.g. the original ``Engine/data``).
    """
    here = Path(__file__).resolve().parent
    candidates = [
        here / "data",
        here.parent / "data",
        here.parent / "Engine" / "data",
    ]
    for candidate in candidates:
        if (candidate / "base_items.json").exists():
            return candidate
    # Default to the in-package location even if missing, so errors are clear.
    return candidates[0]


DATA_DIR = _find_data_dir()
