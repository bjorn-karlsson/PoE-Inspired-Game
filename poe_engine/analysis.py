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
def _family_members() -> dict:
    """Group spawnable item mods by ``(type, generation_type)`` family."""
    families = {}
    for mod_id, mod in data.modifiers().items():
        if mod.get("domain") != "item":
            continue
        if mod.get("generation_type") not in ("prefix", "suffix"):
            continue
        if mod.get("is_essence_only"):
            continue
        if not mod.get("spawn_weights"):
            continue
        key = (mod.get("type") or (mod.get("groups") or ["?"])[0],
               mod["generation_type"])
        families.setdefault(key, []).append(mod_id)
    return families


def _family_key(mod):
    return (mod.get("type") or (mod.get("groups") or ["?"])[0],
            mod.get("generation_type"))


@lru_cache(maxsize=None)
def _ranked_family(family_key, tags):
    """Family members ordered best-first (highest required level = tier 1).

    When *tags* is given, only mods that can actually spawn on those tags are
    counted -- this is what makes the tier contextual to the item's base type,
    matching the tier numbers shown in-game.
    """
    members = _family_members().get(family_key, ())
    mods = data.modifiers()
    if tags is not None:
        tagset = set(tags)
        filtered = [m for m in members
                    if any(w["tag"] in tagset and w["weight"] > 0
                           for w in mods[m].get("spawn_weights", []))]
        members = filtered or list(members)
    return tuple(sorted(members,
                        key=lambda m: (-mods[m].get("required_level", 1), m)))


def mod_tier(mod_id, item_tags=None) -> tuple:
    """Return ``(tier, total_tiers)`` for *mod_id*.

    The data has no literal "tier" field, but in Path of Exile the tier shown
    when alt-hovering is the rank of a modifier within its affix family (mod
    ``type``) ordered by required level -- tier 1 is the best. Passing the
    item's tags restricts the ranking to mods that can roll on that base type,
    reproducing the in-game tier numbers (Hale, Healthy, Sanguine, ... for life).
    """
    mod = data.modifiers().get(mod_id)
    if mod is None:
        return (1, 1)
    tags = tuple(sorted(item_tags)) if item_tags is not None else None
    ranked = _ranked_family(_family_key(mod), tags)
    if mod_id not in ranked:
        return (1, max(1, len(ranked)))
    return (ranked.index(mod_id) + 1, len(ranked))


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
