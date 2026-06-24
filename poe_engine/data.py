"""Lazy, cached access to the bundled game data.

The raw JSON files are large (``mods.json`` alone is well over a megabyte), so
they are loaded on first use and cached.  Derived indexes that the engine needs
repeatedly (e.g. the set of item modifiers, or a stat-id -> translation lookup)
are built once and memoized here as well.
"""

import json
from functools import lru_cache

from .config import DATA_DIR


def _load(filename):
    with open(DATA_DIR / filename, encoding="utf-8") as handle:
        return json.load(handle)


@lru_cache(maxsize=None)
def base_items() -> dict:
    """All base item types keyed by their metadata id."""
    return _load("base_items.json")


@lru_cache(maxsize=None)
def modifiers() -> dict:
    """All modifiers keyed by their internal id."""
    return _load("mods.json")


@lru_cache(maxsize=None)
def tags() -> list:
    return _load("tags.json")


@lru_cache(maxsize=None)
def stat_translations() -> list:
    return _load("stat_translations.json")


@lru_cache(maxsize=None)
def item_modifiers() -> dict:
    """Subset of :func:`modifiers` that can roll on items (prefix/suffix)."""
    result = {}
    for name, mod in modifiers().items():
        if mod.get("domain") != "item":
            continue
        if mod.get("generation_type") not in ("prefix", "suffix"):
            continue
        if not mod.get("spawn_weights"):
            continue
        result[name] = mod
    return result


@lru_cache(maxsize=None)
def translation_index() -> dict:
    """Map a *frozenset of stat ids* to its English translation entry.

    Many lines combine several stat ids (e.g. "Adds # to # Fire Damage"), so we
    key on the full id set as well as on individual ids for fall-back lookups.
    """
    index = {}
    for entry in stat_translations():
        english = entry.get("English")
        if not english:
            continue
        ids = tuple(entry.get("ids", ()))
        index[frozenset(ids)] = english[0]
        # Also register single-id fall-backs that are not already present.
        for stat_id in ids:
            index.setdefault(frozenset((stat_id,)), english[0])
    return index
