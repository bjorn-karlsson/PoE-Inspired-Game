"""The stat system.

A :class:`Stat` models a single value built the way ARPG stats are: flat
additions, ``increased``/``reduced`` (additive percentages) and ``more``/``less``
(multiplicative percentages).  The final value is::

    (positive - negative) * (1 + increased% - reduced%) * more / less

clamped to an optional min/max.
"""

from .config import ROUND_DECIMALS, DEFAULT_MAX_RESISTANCE
from .rng import chance_roll


class Stat:
    def __init__(self):
        self.normalize()
        self.totalMaximum = None
        self.totalMinimum = None

    # -- lifecycle ---------------------------------------------------------
    def normalize(self):
        """Reset every contribution back to its neutral value."""
        self.totalStat = 0.0
        self.positiveStat = 0.0
        self.negativeStat = 0.0
        self.increasedStat = 0.0
        self.reducedStat = 0.0
        self.moreStat = 1.0
        self.lessStat = 1.0

    def reprJSON(self):
        repr_dict = {}
        if self.totalStat != 0:
            repr_dict["totalStat"] = self.totalStat
        if self.positiveStat != 0:
            repr_dict["positiveStat"] = self.positiveStat
        if self.negativeStat != 0:
            repr_dict["negativeStat"] = self.negativeStat
        if self.increasedStat != 0:
            repr_dict["increasedStat"] = self.increasedStat
        if self.reducedStat != 0:
            repr_dict["reducedStat"] = self.reducedStat
        if self.moreStat != 1:
            repr_dict["moreStat"] = self.moreStat
        if self.lessStat != 1:
            repr_dict["lessStat"] = self.lessStat
        if isinstance(self.totalMaximum, (int, float)):
            repr_dict["totalMaximum"] = self.totalMaximum
        if isinstance(self.totalMinimum, (int, float)):
            repr_dict["totalMinimum"] = self.totalMinimum
        return repr_dict

    # -- mutators ----------------------------------------------------------
    def addPositiveStat(self, value): self.positiveStat += value
    def removePositiveStat(self, value): self.positiveStat -= value
    def addNegativeStat(self, value): self.negativeStat += value
    def removeNegativeStat(self, value): self.negativeStat -= value

    def addReducedStat(self, value): self.reducedStat += value
    def addIncreasedStat(self, value): self.increasedStat += value
    def removeReducedStat(self, value): self.reducedStat -= value
    def removeIncreasedStat(self, value): self.increasedStat -= value

    def addMoreStat(self, value): self.moreStat *= 1 + (value / 100)
    def removeMoreStat(self, value): self.moreStat /= 1 + (value / 100)
    def addLessStat(self, value): self.lessStat *= 1 + (value / 100)
    def removeLessStat(self, value): self.lessStat /= 1 + (value / 100)

    def setMaximumStat(self, value): self.totalMaximum = value
    def setMinimumStat(self, value): self.totalMinimum = value

    # -- evaluation --------------------------------------------------------
    def calculate(self):
        total = round(
            (self.positiveStat - self.negativeStat)
            * (1 + (self.increasedStat / 100) - (self.reducedStat / 100))
            * self.moreStat
            / self.lessStat,
            ROUND_DECIMALS,
        )
        if self.totalMaximum is not None and total >= self.totalMaximum:
            total = self.totalMaximum
        elif self.totalMinimum is not None and total <= self.totalMinimum:
            total = self.totalMinimum
        self.totalStat = total
        return total

    # -- composition -------------------------------------------------------
    def joinStat(self, other: "Stat"):
        self.positiveStat += other.positiveStat
        self.negativeStat += other.negativeStat
        self.increasedStat += other.increasedStat
        self.reducedStat += other.reducedStat
        self.moreStat *= other.moreStat
        self.lessStat *= other.lessStat

    def disconnectStat(self, other: "Stat"):
        self.positiveStat -= other.positiveStat
        self.negativeStat -= other.negativeStat
        self.increasedStat -= other.increasedStat
        self.reducedStat -= other.reducedStat
        self.moreStat /= other.moreStat
        self.lessStat /= other.lessStat


# Friendly aliases used by the data/translation layer so a stat id can be
# routed to the right field on a :class:`Stats` sheet.
ATTRIBUTES = ("strength", "dexterity", "intelligence")


class AttributeStat:
    def __init__(self):
        self.strength = Stat()
        self.dexterity = Stat()
        self.intelligence = Stat()

    def reprJSON(self):
        repr_dict = {}
        for key, val in self.__dict__.items():
            repr_val = val.reprJSON()
            if repr_val:
                repr_dict[key] = repr_val
        return repr_dict

    def addPositiveToAllAttributes(self, value):
        for attr in ATTRIBUTES:
            getattr(self, attr).addPositiveStat(value)

    def addIncreasedToAllAttributes(self, value):
        for attr in ATTRIBUTES:
            getattr(self, attr).addIncreasedStat(value)


class PoolStat(Stat):
    """A resource pool (life/mana/energy shield) with a current value."""

    def __init__(self):
        super().__init__()
        self.currentStat = None
        self.regenerateStat = Stat()

    def reprJSON(self):
        repr_dict = super().reprJSON()
        if self.currentStat is not None:
            repr_dict["currentStat"] = self.currentStat
        regen = self.regenerateStat.reprJSON()
        if regen:
            repr_dict["regenerateStat"] = regen
        return repr_dict

    def normalize(self):
        super().normalize()
        if getattr(self, "regenerateStat", None) is not None:
            self.regenerateStat.normalize()

    def calculate(self):
        self.regenerateStat.calculate()
        return super().calculate()

    def regenerate(self):
        if self.currentStat is None:
            return
        new_value = self.currentStat + self.regenerateStat.totalStat
        self.currentStat = max(0.0, min(new_value, self.totalStat))

    def drain(self, amount):
        if self.currentStat is None:
            return
        self.currentStat = max(0.0, round(self.currentStat - amount, ROUND_DECIMALS))

    def fill(self):
        self.currentStat = self.totalStat


class LifeStat(PoolStat): pass
class ManaStat(PoolStat): pass
class EnergyShieldStat(PoolStat): pass

class EvasionStat(Stat): pass
class ArmourStat(Stat): pass

class FireResistanceStat(Stat): pass
class ColdResistanceStat(Stat): pass
class LightningResistanceStat(Stat): pass
class ChaosResistanceStat(Stat): pass

class AccuracyStat(Stat): pass
class PhysicalDamageStat(Stat): pass
class RangedDamageStat(Stat): pass
class SpellDamageStat(Stat): pass
class FireDamageStat(Stat): pass
class ColdDamageStat(Stat): pass
class LightningDamageStat(Stat): pass
class ChaosDamageStat(Stat): pass

class AttackSpeedStat(Stat): pass
class CastSpeedStat(Stat): pass


class CriticalStrikeChanceStat(Stat):
    def roll(self) -> bool:
        return chance_roll(self.totalStat)


class CriticalStrikeDamageStat(Stat):
    def calculateDamage(self, current_damage) -> float:
        return round(current_damage * ((self.totalStat + 100) / 100), ROUND_DECIMALS)


class Stats:
    """A full stat sheet for a character or a piece of equipment."""

    def __init__(self):
        self.attributes = AttributeStat()

        self.life = LifeStat()
        self.mana = ManaStat()
        self.energyShield = EnergyShieldStat()
        self.evasion = EvasionStat()
        self.armour = ArmourStat()

        self.fireResistance = FireResistanceStat()
        self.coldResistance = ColdResistanceStat()
        self.lightningResistance = LightningResistanceStat()
        self.chaosResistance = ChaosResistanceStat()

        self.accuracy = AccuracyStat()
        self.physicalDamage = PhysicalDamageStat()
        self.rangedDamage = RangedDamageStat()
        self.spellDamage = SpellDamageStat()
        self.fireDamage = FireDamageStat()
        self.coldDamage = ColdDamageStat()
        self.lightningDamage = LightningDamageStat()
        self.chaosDamage = ChaosDamageStat()

        self.attackSpeed = AttackSpeedStat()
        self.castSpeed = CastSpeedStat()

        self.criticalStrikeChance = CriticalStrikeChanceStat()
        self.criticalStrikeDamage = CriticalStrikeDamageStat()

    def reprJSON(self):
        repr_dict = {}
        for key, val in self.__dict__.items():
            repr_val = val.reprJSON()
            if repr_val:
                repr_dict[key] = repr_val
        return repr_dict

    # -- iteration helpers -------------------------------------------------
    def _simple_stats(self):
        """Yield (key, stat) for every non-attribute stat on the sheet."""
        for key, val in self.__dict__.items():
            if isinstance(val, AttributeStat):
                continue
            yield key, val

    # -- evaluation --------------------------------------------------------
    def calculate(self):
        """Resolve every stat, applying attribute-derived bonuses once.

        The attribute bonuses are applied to a *copy* of the relevant fields so
        that calling :meth:`calculate` repeatedly never compounds them.
        """
        self.attributes.strength.calculate()
        self.attributes.dexterity.calculate()
        self.attributes.intelligence.calculate()

        strength = self.attributes.strength.totalStat
        dexterity = self.attributes.dexterity.totalStat
        intelligence = self.attributes.intelligence.totalStat

        # Attribute derivations, computed from resolved attribute totals.
        derived = {
            "life": ("positive", strength / 2),
            "physicalDamage": ("positive", strength / 2),
            "mana": ("positive", intelligence / 2),
            "energyShield": ("increased", intelligence / 5),
            "spellDamage": ("increased", intelligence / 5),
            "rangedDamage": ("increased", dexterity / 5),
            "accuracy": ("positive", dexterity * 2),
            "evasion": ("positive", dexterity / 2),
        }

        for key, stat in self._simple_stats():
            bonus = derived.get(key)
            if bonus is None:
                stat.calculate()
                continue
            kind, amount = bonus
            if kind == "positive":
                stat.positiveStat += amount
                stat.calculate()
                stat.positiveStat -= amount
            else:  # increased
                stat.increasedStat += amount
                stat.calculate()
                stat.increasedStat -= amount

    # -- composition -------------------------------------------------------
    def joinStats(self, other: "Stats"):
        for attr in ATTRIBUTES:
            getattr(self.attributes, attr).joinStat(getattr(other.attributes, attr))
        for key, stat in self._simple_stats():
            other_stat = getattr(other, key)
            stat.joinStat(other_stat)
            if isinstance(stat, PoolStat):
                stat.regenerateStat.joinStat(other_stat.regenerateStat)

    def disconnectStats(self, other: "Stats"):
        for attr in ATTRIBUTES:
            getattr(self.attributes, attr).disconnectStat(getattr(other.attributes, attr))
        for key, stat in self._simple_stats():
            other_stat = getattr(other, key)
            stat.disconnectStat(other_stat)
            if isinstance(stat, PoolStat):
                stat.regenerateStat.disconnectStat(other_stat.regenerateStat)

    def normalize(self):
        for attr in ATTRIBUTES:
            getattr(self.attributes, attr).normalize()
        for _, stat in self._simple_stats():
            stat.normalize()

    def setBaseMaxResistances(self, cap=DEFAULT_MAX_RESISTANCE):
        self.fireResistance.setMaximumStat(cap)
        self.coldResistance.setMaximumStat(cap)
        self.lightningResistance.setMaximumStat(cap)
        self.chaosResistance.setMaximumStat(cap)

    def calculateCritModifier(self, value: float) -> float:
        if self.criticalStrikeChance.roll():
            return self.criticalStrikeDamage.calculateDamage(value)
        return value
