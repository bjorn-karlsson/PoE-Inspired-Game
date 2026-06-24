"""Item rarity and how it is rolled."""

from enum import Enum

from .rng import chance_roll, uniform


class Rarities(Enum):
    NORMAL = 1   # no mods
    MAGIC = 2    # 1-2 mods
    RARE = 3     # 4-6 mods
    UNIQUE = 4   # fixed, hand-designed mods


# Base chance (in percent) to roll *at least* this rarity, before any bonus.
_RARITY_CHANCES = (
    (Rarities.UNIQUE, 0.2),
    (Rarities.RARE, 4.0),
    (Rarities.MAGIC, 25.0),
)


class Rarity:
    """Holds a rolled rarity plus a small luck/quality bonus (0-100)."""

    def __init__(self, bonus=0.0):
        self.rarity = Rarities.NORMAL
        self.bonus = float(bonus)

    def reprJSON(self):
        return {"rarity": self.rarity.name, "bonus": round(self.bonus, 2)}

    def roll(self):
        for rarity, base_chance in _RARITY_CHANCES:
            if chance_roll(base_chance + self.bonus):
                self.rarity = rarity
                return self.rarity
        self.rarity = Rarities.NORMAL
        return self.rarity

    @staticmethod
    def random_bonus(max_bonus=10.0):
        return uniform(0, max_bonus)
