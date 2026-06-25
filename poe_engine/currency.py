"""Currency orbs -- stackable consumables that modify items.

A slice of Path of Exile's crafting currency. Each orb knows whether it can be
applied to a given item (:meth:`Currency.applies_to`) so the UI can grey it out,
and what it does (:meth:`Currency._apply`).

Crafting rules implemented (close to PoE):

* Scroll of Wisdom -- identify an item.
* Orb of Transmutation -- Normal -> Magic.
* Orb of Augmentation -- add a mod to a Magic item with a free affix.
* Orb of Alteration -- reforge a Magic item with new Magic mods.
* Regal Orb -- Magic -> Rare, adding one mod.
* Orb of Alchemy -- Normal -> Rare.
* Chaos Orb -- reforge a Rare with new mods.
* Exalted Orb -- add a mod to a Rare item with a free affix.
* Divine Orb -- reroll the numeric values of a magic/rare item's mods.
* Blessed Orb -- reroll the numeric values of implicit mods.
* Orb of Annulment -- remove a random mod.
* Orb of Scouring -- strip all mods, reverting to Normal.
"""

from .rarity import Rarities


class Currency:
    """Base class for a stack of one currency type."""

    name = "Currency"
    max_stack = 10
    description = ""
    _deny_reason = "cannot be used on this item"

    def __init__(self, count=1):
        self.count = count

    def reprJSON(self):
        return {"name": self.name, "count": self.count, "max_stack": self.max_stack}

    # -- behaviour (override in subclasses) --------------------------------
    def applies_to(self, item) -> bool:
        return False

    def _apply(self, item) -> bool:
        raise NotImplementedError

    # -- shared use logic --------------------------------------------------
    def use_on(self, item) -> bool:
        """Apply one unit to *item*; consume a stack on success."""
        if self.count <= 0 or not self.applies_to(item):
            return False
        if self._apply(item):
            self.count -= 1
            return True
        return False

    def reason(self, item) -> str:
        if self.count <= 0:
            return "none left"
        return "ready" if self.applies_to(item) else self._deny_reason


def _is(item, *rarities):
    return item.identified and item.rarity.rarity in rarities


# --------------------------------------------------------------- orbs ------
class ScrollOfWisdom(Currency):
    name = "Scroll of Wisdom"
    max_stack = 40
    description = "Identifies an item."
    _deny_reason = "already identified"

    def applies_to(self, item):
        return not item.identified

    def _apply(self, item):
        item.identified = True
        return True


class OrbOfTransmutation(Currency):
    name = "Orb of Transmutation"
    max_stack = 40
    description = "Upgrades a Normal item to a Magic item."
    _deny_reason = "needs a Normal item"

    def applies_to(self, item):
        return _is(item, Rarities.NORMAL)

    def _apply(self, item):
        item.set_rarity(Rarities.MAGIC)
        item.reroll_explicits()
        return True


class OrbOfAugmentation(Currency):
    name = "Orb of Augmentation"
    max_stack = 30
    description = "Adds a new modifier to a Magic item."
    _deny_reason = "needs a Magic item with a free affix"

    def applies_to(self, item):
        return _is(item, Rarities.MAGIC) and bool(item.open_affix_types())

    def _apply(self, item):
        return item.add_random_affix() is not None


class OrbOfAlteration(Currency):
    name = "Orb of Alteration"
    max_stack = 20
    description = "Reforges a Magic item with new random modifiers."
    _deny_reason = "needs a Magic item"

    def applies_to(self, item):
        return _is(item, Rarities.MAGIC)

    def _apply(self, item):
        item.reroll_explicits()
        return True


class RegalOrb(Currency):
    name = "Regal Orb"
    max_stack = 10
    description = "Upgrades a Magic item to a Rare item, adding one modifier."
    _deny_reason = "needs a Magic item"

    def applies_to(self, item):
        return _is(item, Rarities.MAGIC)

    def _apply(self, item):
        item.set_rarity(Rarities.RARE)
        item.add_random_affix()
        return True


class OrbOfAlchemy(Currency):
    name = "Orb of Alchemy"
    max_stack = 10
    description = "Upgrades a Normal item to a Rare item."
    _deny_reason = "needs a Normal item"

    def applies_to(self, item):
        return _is(item, Rarities.NORMAL)

    def _apply(self, item):
        item.set_rarity(Rarities.RARE)
        item.reroll_explicits()
        return True


class ChaosOrb(Currency):
    name = "Chaos Orb"
    max_stack = 10
    description = "Reforges a Rare item with new random modifiers."
    _deny_reason = "needs a Rare item"

    def applies_to(self, item):
        return _is(item, Rarities.RARE)

    def _apply(self, item):
        item.reroll_explicits()
        return True


class ExaltedOrb(Currency):
    name = "Exalted Orb"
    max_stack = 10
    description = "Adds a new modifier to a Rare item."
    _deny_reason = "needs a Rare item with a free affix"

    def applies_to(self, item):
        return _is(item, Rarities.RARE) and bool(item.open_affix_types())

    def _apply(self, item):
        return item.add_random_affix() is not None


class DivineOrb(Currency):
    name = "Divine Orb"
    max_stack = 10
    description = "Rerolls the numeric values of an item's modifiers."
    _deny_reason = "needs an item with modifiers"

    def applies_to(self, item):
        return _is(item, Rarities.MAGIC, Rarities.RARE, Rarities.UNIQUE) \
            and bool(item.explicits)

    def _apply(self, item):
        item.reroll_values()
        return True


class BlessedOrb(Currency):
    name = "Blessed Orb"
    max_stack = 20
    description = "Rerolls the numeric values of an item's implicit modifiers."
    _deny_reason = "needs an item with implicit modifiers"

    def applies_to(self, item):
        return item.identified and bool(item.implicits)

    def _apply(self, item):
        item.reroll_implicit_values()
        return True


class OrbOfAnnulment(Currency):
    name = "Orb of Annulment"
    max_stack = 20
    description = "Removes a random modifier from an item."
    _deny_reason = "needs an item with modifiers"

    def applies_to(self, item):
        return _is(item, Rarities.MAGIC, Rarities.RARE) and bool(item.explicits)

    def _apply(self, item):
        return item.remove_random_affix() is not None


class OrbOfScouring(Currency):
    name = "Orb of Scouring"
    max_stack = 30
    description = "Removes all modifiers from an item."
    _deny_reason = "needs a Magic or Rare item"

    def applies_to(self, item):
        return _is(item, Rarities.MAGIC, Rarities.RARE) and bool(item.explicits)

    def _apply(self, item):
        item.scour()
        return True


# In rough order of the PoE crafting progression.
CURRENCY_TYPES = [
    ScrollOfWisdom, OrbOfTransmutation, OrbOfAugmentation, OrbOfAlteration,
    RegalOrb, OrbOfAlchemy, ChaosOrb, ExaltedOrb, DivineOrb, BlessedOrb,
    OrbOfAnnulment, OrbOfScouring,
]


def starter_currency():
    """A generous starting set of every currency type for the test bench."""
    return [cls(count=cls.max_stack) for cls in CURRENCY_TYPES]
