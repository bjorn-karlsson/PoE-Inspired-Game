"""Randomness helpers used across the engine.

A single module-level :class:`random.Random` instance is used so that the whole
engine can be made deterministic in tests via :func:`seed`.
"""

import random as _random

from .config import ROUND_DECIMALS

_rng = _random.Random()


def seed(value):
    """Seed the shared RNG (useful for reproducible tests/demos)."""
    _rng.seed(value)


def chance_roll(odds_percent) -> bool:
    """Return ``True`` with probability ``odds_percent`` (0-100)."""
    if odds_percent <= 0:
        return False
    if odds_percent >= 100:
        return True
    return round(_rng.random() * 100, ROUND_DECIMALS) <= odds_percent


def uniform(low, high) -> float:
    return _rng.uniform(low, high)


def randint(low, high) -> int:
    return _rng.randint(low, high)


def choice(seq):
    return _rng.choice(seq)


def weighted_choice(weights: dict):
    """Pick a key from ``{item: weight}`` proportional to its weight.

    Returns ``None`` if all weights are zero / the mapping is empty.
    """
    total = sum(weights.values())
    if total <= 0:
        return None
    roll = _rng.uniform(0, total)
    for item, weight in weights.items():
        roll -= weight
        if roll < 0:
            return item
    return None  # pragma: no cover - floating point edge
