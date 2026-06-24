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


class Character(BaseCharacter):
    def __init__(self, name, level=1):
        self.inventory = Inventory()
        super().__init__(name, level)

    def setBaseStats(self):
        super().setBaseStats()
        self.stats.life.addPositiveStat(50)
        self.stats.life.regenerateStat.addPositiveStat(10)
        self.stats.mana.addPositiveStat(40)
        self.stats.mana.regenerateStat.addPositiveStat(10)
        self.stats.evasion.addPositiveStat(53)
        self.stats.physicalDamage.addPositiveStat(5)
        self.stats.accuracy.addPositiveStat(50)
        self.stats.criticalStrikeChance.addPositiveStat(5)

    def reprJSON(self):
        repr_dict = super().reprJSON()
        repr_dict["inventory"] = self.inventory
        return repr_dict
