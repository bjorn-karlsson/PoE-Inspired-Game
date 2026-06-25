"""Characters and monsters: anything that wears gear and can fight."""

from .config import DEFAULT_MAX_RESISTANCE
from .inventory import Inventory
from .items import Equipments, Item
from .stats import Stats


class BaseCharacter:
    def __init__(self, name, level=1):
        self.name = name
        self.level = level
        self.alive = True
        self.equipments = Equipments()
        self.stats = Stats()
        self.recalibrate()

    def reprJSON(self):
        return {
            "name": self.name,
            "level": self.level,
            "alive": self.alive,
            "equipments": self.equipments.reprJSON(),
            "stats": self.stats.reprJSON(),
        }

    # -- stat lifecycle ----------------------------------------------------
    def setBaseStats(self):
        """Hook for subclasses to seed innate stats (called post-normalize)."""
        self.stats.setBaseMaxResistances(DEFAULT_MAX_RESISTANCE)

    def joinEquipmentStats(self):
        for item in self.equipments.equipped_items():
            self.stats.joinStats(item.build_stats())

    def recalibrate(self):
        """Recompute the full stat sheet from base + equipment, then refill."""
        self.stats.normalize()
        self.setBaseStats()
        self.joinEquipmentStats()
        self.stats.calculate()
        self.restore()

    # -- resource pools ----------------------------------------------------
    def restore(self):
        self.stats.life.fill()
        self.stats.mana.fill()
        self.stats.energyShield.fill()
        self.alive = self.stats.life.currentStat > 0

    def regenerate(self):
        self.stats.life.regenerate()
        self.stats.mana.regenerate()
        self.stats.energyShield.regenerate()
        self.alive = self.stats.life.currentStat > 0

    # -- equipment ---------------------------------------------------------
    def equip(self, item: Item):
        replaced = self.equipments.equip(item)
        self.recalibrate()
        return replaced

    def unequip(self, slot):
        replaced = self.equipments.unequip(slot)
        self.recalibrate()
        return replaced


class Monster(BaseCharacter):
    def __init__(self, name, level=1):
        super().__init__(name, level)

    def setBaseStats(self):
        super().setBaseStats()
        self.stats.life.addPositiveStat(30 + self.level * 8)
        self.stats.physicalDamage.addPositiveStat(5 + self.level * 2)


# Playable classes and their starting attributes (Str, Dex, Int), in the spirit
# of Path of Exile's seven classes.
CLASSES = {
    "Marauder": (32, 14, 14),
    "Ranger": (14, 32, 14),
    "Witch": (14, 14, 32),
    "Duelist": (23, 23, 14),
    "Templar": (23, 14, 23),
    "Shadow": (14, 23, 23),
    "Scion": (20, 20, 20),
}
CLASS_NAMES = list(CLASSES)


class Character(BaseCharacter):
    def __init__(self, name, char_class="Marauder", level=1):
        self.inventory = Inventory()
        self.char_class = char_class if char_class in CLASSES else "Scion"
        super().__init__(name, level)

    def setBaseStats(self):
        super().setBaseStats()
        strength, dexterity, intelligence = CLASSES[self.char_class]
        self.stats.attributes.strength.addPositiveStat(strength)
        self.stats.attributes.dexterity.addPositiveStat(dexterity)
        self.stats.attributes.intelligence.addPositiveStat(intelligence)

        # Per-level scaling (life/mana/accuracy grow as you level up).
        levels = self.level - 1
        self.stats.life.addPositiveStat(50 + 12 * levels)
        self.stats.life.regenerateStat.addPositiveStat(10)
        self.stats.mana.addPositiveStat(40 + 6 * levels)
        self.stats.mana.regenerateStat.addPositiveStat(10)
        self.stats.accuracy.addPositiveStat(2 * levels)
        self.stats.evasion.addPositiveStat(53)
        self.stats.physicalDamage.addPositiveStat(5)
        self.stats.criticalStrikeChance.addPositiveStat(5)

    def level_up(self, amount=1):
        self.level = max(1, self.level + amount)
        self.recalibrate()
        return self.level

    def reprJSON(self):
        repr_dict = super().reprJSON()
        repr_dict["class"] = self.char_class
        repr_dict["inventory"] = self.inventory
        return repr_dict
