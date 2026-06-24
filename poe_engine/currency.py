"""Currency orbs -- stackable consumables that modify items.

A small, extensible slice of Path of Exile's currency system:

* :class:`ScrollOfWisdom` -- identifies an unidentified item.
* :class:`ChaosOrb` -- reforges a rare item with new random modifiers.

Each currency type has a maximum stack size and knows whether it can be applied
to a given item (:meth:`Currency.applies_to`) so the UI can grey it out.
"""

from .rarity import Rarities


class Currency:
    """Base class for a stack of one currency type."""

    name = "Currency"
    max_stack = 10
    description = ""

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
        """Human-readable explanation of why it can/can't be used on *item*."""
        if self.count <= 0:
            return "none left"
        return "ready" if self.applies_to(item) else self._deny_reason


class ScrollOfWisdom(Currency):
    name = "Scroll of Wisdom"
    max_stack = 40
    description = "Identifies an item."
    _deny_reason = "already identified"

    def applies_to(self, item) -> bool:
        return not item.identified

    def _apply(self, item) -> bool:
        item.identified = True
        return True


class ChaosOrb(Currency):
    name = "Chaos Orb"
    max_stack = 20
    description = "Reforges a rare item with new random modifiers."
    _deny_reason = "needs an identified Rare item"

    def applies_to(self, item) -> bool:
        return item.identified and item.rarity.rarity == Rarities.RARE

    def _apply(self, item) -> bool:
        item.reroll_explicits()
        return True


# Convenience: the currencies the demo starts with.
def starter_currency():
    return [ScrollOfWisdom(count=40), ChaosOrb(count=20)]
