"""Item modifiers: rolling them onto items and reading them back.

A :class:`Modifier` wraps one raw modifier from ``mods.json`` and, once rolled,
remembers the concrete value chosen for each of its stats so it can be both
applied to a stat sheet and rendered as readable text.
"""

from . import data
from .rng import randint
from .translate import translate_stats


class Modifier:
    def __init__(self, mod_id, raw):
        self.id = mod_id
        self.name = raw.get("name") or ""
        self.generation_type = raw.get("generation_type")
        self.group = (raw.get("groups") or ["Nothing"])[0]
        self.required_level = raw.get("required_level", 1)
        self.tier_tags = raw.get("implicit_tags", [])
        self.raw = raw
        # Each entry: {"id", "min", "max", "value"}.
        self.stats = []

    # -- construction ------------------------------------------------------
    @classmethod
    def from_id(cls, mod_id):
        return cls(mod_id, data.modifiers()[mod_id])

    def roll(self):
        """Roll a concrete value for every stat between its min and max."""
        self.stats = []
        for stat in self.raw.get("stats", []):
            low, high = stat.get("min", 0), stat.get("max", 0)
            value = randint(low, high) if low != high else low
            self.stats.append({"id": stat["id"], "min": low, "max": high, "value": value})
        return self

    # -- presentation ------------------------------------------------------
    @property
    def lines(self):
        return translate_stats(self.stats)

    def reprJSON(self):
        return {
            "id": self.id,
            "name": self.name,
            "type": self.generation_type,
            "group": self.group,
            "stats": self.stats,
            "lines": self.lines,
        }

    def __repr__(self):
        return f"<Modifier {self.id} {self.lines}>"
