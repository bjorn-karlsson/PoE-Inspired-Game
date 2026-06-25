"""poe_engine -- a small Path of Exile inspired item & combat engine.

Public API::

    from poe_engine import Item, Character, Monster, simulate_fight

See ``play.py`` in the project root for a runnable demo.
"""

from .character import CLASS_NAMES, CLASSES, BaseCharacter, Character, Monster
from .combat import attack, hit_chance, simulate_fight
from .inventory import Inventory
from .items import (
    Accessory, Amulet, Armour, Belt, BodyArmour, Boots, Equipments, Gloves,
    Helmet, Item, Ring, Shield, Weapon,
)
from .modifiers import Modifier
from .rarity import Rarities, Rarity
from .rng import seed
from .stats import Stat, Stats

__all__ = [
    "BaseCharacter", "Character", "Monster", "CLASSES", "CLASS_NAMES",
    "attack", "hit_chance", "simulate_fight",
    "Inventory",
    "Item", "Weapon", "Shield", "Armour", "Helmet", "BodyArmour", "Gloves",
    "Boots", "Accessory", "Amulet", "Ring", "Belt", "Equipments",
    "Modifier", "Rarity", "Rarities", "Stat", "Stats", "seed",
]

__version__ = "0.1.0"
