"""Item rarity and how it is rolled."""

from enum import Enum

from .rng import chance_roll, uniform


class Rarities(Enum):
    NORMAL = 1   # no mods
    MAGIC = 2    # 1-2 mods
    RARE = 3     # 4-6 mods
    UNIQUE = 4   # fixed, hand-designed mods


# How each rarity's chance scales with the luck/rarity bonus.  Uniques are
# deliberately barely affected so a high bonus produces more rares/magics, not a
# flood of uniques (base %, per-point-of-bonus %).
_RARITY_CURVE = (
    (Rarities.UNIQUE, 0.2, 0.02),
    (Rarities.RARE, 5.0, 0.5),
    (Rarities.MAGIC, 30.0, 1.0),
)


class Rarity:
    """Holds a rolled rarity plus a small luck/rarity bonus (0-100)."""

    def __init__(self, bonus=0.0):
        self.rarity = Rarities.NORMAL
        self.bonus = float(bonus)

    def reprJSON(self):
        return {"rarity": self.rarity.name, "bonus": round(self.bonus, 2)}

    def roll(self):
        for rarity, base_chance, per_point in _RARITY_CURVE:
            if chance_roll(base_chance + self.bonus * per_point):
                self.rarity = rarity
                return self.rarity
        self.rarity = Rarities.NORMAL
        return self.rarity

    @staticmethod
    def random_bonus(max_bonus=8.0):
        return uniform(0, max_bonus)
