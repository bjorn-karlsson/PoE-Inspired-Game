"""Route raw modifier stat ids onto a :class:`~poe_engine.stats.Stats` sheet.

There are thousands of distinct stat ids in the data dump; mapping every one is
out of scope.  Instead we handle the common, combat-relevant families so that
equipped items meaningfully change a character's stats.  Unmapped ids are
ignored for the *numeric* model but still render in an item's readable text.
"""

from .stats import ATTRIBUTES


def _add(sheet, field, kind, value):
    stat = getattr(sheet, field)
    if kind == "positive":
        stat.addPositiveStat(value)
    elif kind == "increased":
        stat.addIncreasedStat(value)
    elif kind == "more":
        stat.addMoreStat(value)


def _all_attributes(sheet, kind, value):
    for attr in ATTRIBUTES:
        stat = getattr(sheet.attributes, attr)
        (stat.addPositiveStat if kind == "positive" else stat.addIncreasedStat)(value)


# Substring -> (field, kind).  Longest/most-specific keys are checked first.
_FLAT = {
    "base_maximum_life": ("life", "positive"),
    "base_maximum_mana": ("mana", "positive"),
    "local_energy_shield": ("energyShield", "positive"),
    "base_maximum_energy_shield": ("energyShield", "positive"),
    "local_base_evasion_rating": ("evasion", "positive"),
    "local_base_physical_damage_reduction_rating": ("armour", "positive"),
    "local_accuracy_rating": ("accuracy", "positive"),
    "base_accuracy_rating": ("accuracy", "positive"),
    "base_critical_strike_multiplier_+": ("criticalStrikeDamage", "positive"),
}

_INCREASED = {
    "local_physical_damage_+%": ("physicalDamage", "increased"),
    "physical_damage_+%": ("physicalDamage", "increased"),
    "spell_damage_+%": ("spellDamage", "increased"),
    "fire_damage_+%": ("fireDamage", "increased"),
    "cold_damage_+%": ("coldDamage", "increased"),
    "lightning_damage_+%": ("lightningDamage", "increased"),
    "chaos_damage_+%": ("chaosDamage", "increased"),
    "local_attack_speed_+%": ("attackSpeed", "increased"),
    "attack_speed_+%": ("attackSpeed", "increased"),
    "base_cast_speed_+%": ("castSpeed", "increased"),
    "evasion_rating_+%": ("evasion", "increased"),
    "armour_+%": ("armour", "increased"),
    "accuracy_rating_+%": ("accuracy", "increased"),
    "critical_strike_chance_+%": ("criticalStrikeChance", "increased"),
    "maximum_life_+%": ("life", "increased"),
    "maximum_mana_+%": ("mana", "increased"),
    "energy_shield_+%": ("energyShield", "increased"),
}

_RESISTANCE = {
    "base_fire_damage_resistance_%": "fireResistance",
    "base_cold_damage_resistance_%": "coldResistance",
    "base_lightning_damage_resistance_%": "lightningResistance",
    "base_chaos_damage_resistance_%": "chaosResistance",
}

_ELEMENT_OF = {"fire": "fireDamage", "cold": "coldDamage",
               "lightning": "lightningDamage", "chaos": "chaosDamage",
               "physical": "physicalDamage"}


def apply_modifier(sheet, modifier):
    """Apply one rolled :class:`~poe_engine.modifiers.Modifier` to *sheet*."""
    for stat in modifier.stats:
        apply_stat(sheet, stat["id"], stat.get("value", 0))


def apply_stat(sheet, stat_id, value):
    # Attributes
    if stat_id == "additional_all_attributes":
        return _all_attributes(sheet, "positive", value)
    if stat_id == "all_attributes_+%":
        return _all_attributes(sheet, "increased", value)
    for attr in ATTRIBUTES:
        if stat_id == f"additional_{attr}":
            return getattr(sheet.attributes, attr).addPositiveStat(value)
        if stat_id == f"{attr}_+%":
            return getattr(sheet.attributes, attr).addIncreasedStat(value)

    # Resistances (incl. "all elemental")
    if stat_id in _RESISTANCE:
        return _add(sheet, _RESISTANCE[stat_id], "positive", value)
    if stat_id in ("base_resist_all_elements_%", "base_all_elemental_resistance_%"):
        for field in ("fireResistance", "coldResistance", "lightningResistance"):
            _add(sheet, field, "positive", value)
        return

    # Direct flat / increased lookups
    if stat_id in _FLAT:
        field, kind = _FLAT[stat_id]
        return _add(sheet, field, kind, value)
    if stat_id in _INCREASED:
        field, kind = _INCREASED[stat_id]
        return _add(sheet, field, kind, value)

    # Added elemental / physical damage (min & max share the budget).
    if "added_" in stat_id and "_damage" in stat_id:
        for element, field in _ELEMENT_OF.items():
            if f"added_{element}_damage" in stat_id:
                return _add(sheet, field, "positive", value / 2)

    # Elemental damage with attacks -> spread across the three elements.
    if stat_id in ("elemental_damage_+%", "elemental_damage_with_attack_skills_+%"):
        for field in ("fireDamage", "coldDamage", "lightningDamage"):
            _add(sheet, field, "increased", value)
        return
    # Unmapped: ignored numerically (still shown in item text).
