"""Introspection helpers for the inventory UI / debugging.

Two things live here:

* :func:`mod_tier` -- where a modifier ranks within its group (PoE "tier").
* :func:`stat_breakdown` -- exactly how a character's stat is built up, source
  by source (base, each equipped item, attribute derivations) so you can verify
  the additive / increased / more math.
"""

from functools import lru_cache

from . import data
from .config import ROUND_DECIMALS
from .stats import PoolStat


# ---------------------------------------------------------------- tiers ----
@lru_cache(maxsize=None)
def _group_tier_table() -> dict:
    """Map ``mod_id -> (tier, total_tiers)`` ranking within its group.

    Higher required level == better tier (tier 1 is best), matching how PoE
    numbers tiers within a mod group.
    """
    groups = {}
    for mod_id, mod in data.item_modifiers().items():
        group = (mod.get("groups") or ["?"])[0]
        groups.setdefault(group, []).append(
            (mod.get("required_level", 1), mod_id))

    table = {}
    for members in groups.values():
        members.sort(key=lambda item: (-item[0], item[1]))
        total = len(members)
        for index, (_, mod_id) in enumerate(members):
            table[mod_id] = (index + 1, total)
    return table


def mod_tier(mod_id) -> tuple:
    """Return ``(tier, total_tiers)`` for *mod_id* (defaults to ``(1, 1)``)."""
    return _group_tier_table().get(mod_id, (1, 1))


# --------------------------------------------------------------- stats ----
def resolve_stat(stats, path):
    """Resolve a dotted stat path, e.g. ``"attributes.strength"``."""
    obj = stats
    for part in path.split("."):
        obj = getattr(obj, part)
    return obj


def component_dict(stat) -> dict:
    """Return the non-neutral contribution fields of a :class:`Stat`."""
    fields = {}
    if stat.positiveStat:
        fields["positive"] = stat.positiveStat
    if stat.negativeStat:
        fields["negative"] = stat.negativeStat
    if stat.increasedStat:
        fields["increased"] = stat.increasedStat
    if stat.reducedStat:
        fields["reduced"] = stat.reducedStat
    if stat.moreStat != 1.0:
        fields["more"] = stat.moreStat
    if stat.lessStat != 1.0:
        fields["less"] = stat.lessStat
    return fields


# Attribute -> derived stat contributions, mirroring Stats.calculate().
def attribute_derivation(stats, path):
    """Return ``(kind, amount)`` an attribute contributes to *path*, or None."""
    strength = stats.attributes.strength.totalStat
    dexterity = stats.attributes.dexterity.totalStat
    intelligence = stats.attributes.intelligence.totalStat
    mapping = {
        "life": ("positive", strength / 2),
        "physicalDamage": ("positive", strength / 2),
        "mana": ("positive", intelligence / 2),
        "energyShield": ("increased", intelligence / 5),
        "spellDamage": ("increased", intelligence / 5),
        "rangedDamage": ("increased", dexterity / 5),
        "accuracy": ("positive", dexterity * 2),
        "evasion": ("positive", dexterity / 2),
    }
    result = mapping.get(path)
    if result is None or result[1] == 0:
        return None
    return result


def _equipped_items(character):
    from .items import SLOTS  # local import avoids a cycle
    for slot in SLOTS:
        item = getattr(character.equipments, slot, None)
        if item is not None:
            yield slot, item


def stat_breakdown(character, path) -> dict:
    """Build a full, source-by-source breakdown of ``character.stats[path]``."""
    sources = []

    # Base: a fresh, equipment-free character of the same kind/level.
    base_char = type(character)(character.name, character.level)
    base_components = component_dict(resolve_stat(base_char.stats, path))
    if base_components:
        sources.append({"name": "Base character", "components": base_components})

    # Each equipped item's contribution.
    for slot, item in _equipped_items(character):
        item_components = component_dict(resolve_stat(item.build_stats(), path))
        if item_components:
            sources.append({
                "name": f"{item.name}",
                "slot": slot,
                "components": item_components,
            })

    # Attribute-derived contribution (computed from final attribute totals).
    derived = attribute_derivation(character.stats, path)
    if derived:
        kind, amount = derived
        sources.append({
            "name": "Attributes (derived)",
            "components": {kind: round(amount, ROUND_DECIMALS)},
        })

    totals = {"positive": 0.0, "negative": 0.0, "increased": 0.0,
              "reduced": 0.0, "more": 1.0, "less": 1.0}
    for source in sources:
        for key, value in source["components"].items():
            if key in ("more", "less"):
                totals[key] *= value
            else:
                totals[key] += value

    computed = ((totals["positive"] - totals["negative"])
                * (1 + totals["increased"] / 100 - totals["reduced"] / 100)
                * totals["more"] / totals["less"])
    computed = round(computed, ROUND_DECIMALS)

    stat = resolve_stat(character.stats, path)
    clamp = None
    if stat.totalMaximum is not None and computed >= stat.totalMaximum:
        computed, clamp = stat.totalMaximum, f"capped at {stat.totalMaximum}"
    elif stat.totalMinimum is not None and computed <= stat.totalMinimum:
        computed, clamp = stat.totalMinimum, f"floored at {stat.totalMinimum}"

    return {
        "path": path,
        "sources": sources,
        "totals": totals,
        "computed_total": computed,
        "actual_total": stat.totalStat,
        "clamp": clamp,
        "is_pool": isinstance(stat, PoolStat),
    }
