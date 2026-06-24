"""Items: base types, generation, and equipment slots."""

from . import data
from .modifiers import Modifier
from .rarity import Rarities, Rarity
from .rng import randint, uniform, weighted_choice
from .stats import Stats


# Weapon item classes from the data, mapped onto the generic Weapon slot.
_WEAPON_CLASSES = {
    "One Hand Sword", "Thrusting One Hand Sword", "Two Hand Sword",
    "One Hand Axe", "Two Hand Axe", "One Hand Mace", "Two Hand Mace",
    "Sceptre", "Wand", "Claw", "Dagger", "Rune Dagger",
    "Bow", "Staff", "Warstaff", "FishingRod",
}


class Item:
    """A concrete, generated item instance."""

    def __init__(self):
        self.domain = None
        self.dropLevel = None
        self.itemClass = None
        self.name = None
        self.tags = []

        self.inventoryWidth = 1
        self.inventoryHeight = 1

        self.properties = {}
        self.requirements = {}

        self.rarity = Rarity()
        self.implicits = []   # list[Modifier]
        self.prefixes = []    # list[Modifier]
        self.suffixes = []    # list[Modifier]

    # -- inventory ---------------------------------------------------------
    @property
    def inventorySize(self):
        return (self.inventoryWidth or 1) * (self.inventoryHeight or 1)

    @property
    def explicits(self):
        return self.prefixes + self.suffixes

    def reprJSON(self):
        return {
            "name": self.name,
            "itemClass": self.itemClass,
            "rarity": self.rarity.rarity.name,
            "dropLevel": self.dropLevel,
            "implicits": self.implicits,
            "prefixes": self.prefixes,
            "suffixes": self.suffixes,
        }

    def build_stats(self) -> Stats:
        """Build a fresh :class:`Stats` sheet from this item's rolled mods."""
        from .stat_router import apply_modifier

        sheet = Stats()
        for mod in self.implicits + self.explicits:
            apply_modifier(sheet, mod)
        return sheet

    def describe(self) -> str:
        """A PoE-style text block for the item."""
        lines = [self.name or "Unknown Item",
                 f"{self.itemClass}  ({self.rarity.rarity.name})"]
        for mod in self.implicits:
            lines.extend(f"  {line}" for line in mod.lines)
        if self.explicits:
            lines.append("  " + "-" * 20)
        for mod in self.explicits:
            lines.extend(f"  {line}" for line in mod.lines)
        return "\n".join(lines)

    # -- generation --------------------------------------------------------
    @classmethod
    def generate(cls, domain="item", drop_level=100, item_class=None, rarity_bonus=None):
        base_name, base = _pick_base(domain, drop_level, item_class)
        item_cls = _class_for(base.get("item_class"))
        item = item_cls()

        item.domain = base.get("domain")
        item.dropLevel = base.get("drop_level")
        item.itemClass = base.get("item_class")
        item.name = base.get("name")
        item.tags = base.get("tags") or []
        item.inventoryWidth = base.get("inventory_width") or 1
        item.inventoryHeight = base.get("inventory_height") or 1
        item.properties = base.get("properties") or {}
        item.requirements = base.get("requirements") or {}

        for implicit_id in base.get("implicits") or []:
            try:
                item.implicits.append(Modifier.from_id(implicit_id).roll())
            except KeyError:
                pass  # implicit references a mod not present in the dump

        if rarity_bonus is None:
            rarity_bonus = Rarity.random_bonus()
        item.rarity = Rarity(rarity_bonus)
        item.rarity.roll()
        item._roll_explicit_mods()
        return item

    def _roll_explicit_mods(self):
        prefixes, suffixes = _mod_counts(self.rarity.rarity)
        if prefixes == 0 and suffixes == 0:
            return

        candidates = _candidate_mods(self.tags, self.dropLevel)
        used_groups = set()
        self.prefixes = _roll_from(candidates["prefix"], prefixes, used_groups)
        self.suffixes = _roll_from(candidates["suffix"], suffixes, used_groups)


# -- module-level generation helpers --------------------------------------

def _class_for(item_class):
    if item_class in _WEAPON_CLASSES:
        return Weapon
    return {
        "Helmet": Helmet,
        "Body Armour": BodyArmour,
        "Gloves": Gloves,
        "Boots": Boots,
        "Amulet": Amulet,
        "Ring": Ring,
        "Belt": Belt,
        "Shield": Shield,
    }.get(item_class, Item)


def _pick_base(domain, drop_level, item_class):
    eligible = {}
    for name, base in data.base_items().items():
        if base.get("domain") != domain:
            continue
        if (base.get("drop_level") or 0) > drop_level:
            continue
        if item_class and base.get("item_class") != item_class:
            continue
        eligible[name] = 1  # uniform weight among eligible bases
    if not eligible:
        raise ValueError(f"No base items match domain={domain!r}, "
                         f"drop_level<={drop_level}, item_class={item_class!r}")
    chosen = weighted_choice(eligible)
    return chosen, data.base_items()[chosen]


def _mod_counts(rarity):
    if rarity == Rarities.MAGIC:
        prefixes = randint(0, 1)
        suffixes = randint(0, 1)
        if prefixes + suffixes == 0:  # magic items always have at least one mod
            if randint(0, 1):
                prefixes = 1
            else:
                suffixes = 1
        return prefixes, suffixes
    if rarity in (Rarities.RARE, Rarities.UNIQUE):
        prefixes = randint(1, 3)
        suffixes = randint(1, 3)
        return prefixes, suffixes
    return 0, 0


def _candidate_mods(item_tags, drop_level):
    """Collect spawnable prefix/suffix mods for the item's tags.

    Returns ``{"prefix": {id: weight}, "suffix": {id: weight}}`` plus a side
    table of mod groups so we can avoid rolling two mods from the same group.
    """
    item_tags = set(item_tags)
    result = {"prefix": {}, "suffix": {}}
    for mod_id, mod in data.item_modifiers().items():
        if mod.get("required_level", 1) > (drop_level or 0):
            continue
        gen_type = mod["generation_type"]
        best_weight = 0
        for weight in mod.get("spawn_weights", []):
            if weight["tag"] in item_tags and weight["weight"] > 0:
                best_weight = max(best_weight, weight["weight"])
        if best_weight > 0:
            result[gen_type][mod_id] = best_weight
    return result


def _roll_from(weighted_ids, count, used_groups):
    chosen = []
    pool = dict(weighted_ids)
    for _ in range(count):
        if not pool:
            break
        mod_id = weighted_choice(pool)
        if mod_id is None:
            break
        modifier = Modifier.from_id(mod_id).roll()
        del pool[mod_id]
        if modifier.group in used_groups:
            continue  # skip duplicate-group mods, slot is consumed
        used_groups.add(modifier.group)
        chosen.append(modifier)
    return chosen


# -- item type hierarchy ---------------------------------------------------

class Weapon(Item): pass
class Shield(Item): pass

class Armour(Item): pass
class Helmet(Armour): pass
class BodyArmour(Armour): pass
class Gloves(Armour): pass
class Boots(Armour): pass

class Accessory(Item): pass
class Amulet(Accessory): pass
class Ring(Accessory): pass
class Belt(Accessory): pass


# Slot key on Equipments -> the Item subclass it accepts.
SLOTS = {
    "weapon": Weapon,
    "offhand": Shield,
    "helmet": Helmet,
    "bodyArmour": BodyArmour,
    "gloves": Gloves,
    "boots": Boots,
    "amulet": Amulet,
    "belt": Belt,
    "ring1": Ring,
    "ring2": Ring,
}


class Equipments:
    """The set of equipped items on a character."""

    def __init__(self):
        for slot in SLOTS:
            setattr(self, slot, None)

    def reprJSON(self):
        return {slot: getattr(self, slot) for slot in SLOTS}

    def slot_for(self, item: Item):
        """Return the slot name an item should occupy (handles dual rings)."""
        if isinstance(item, Ring):
            return "ring1" if self.ring1 is None else "ring2"
        for slot, accepted in SLOTS.items():
            if slot in ("ring1", "ring2"):
                continue
            if isinstance(item, accepted):
                return slot
        return None

    def equip(self, item: Item):
        """Equip *item*, returning whatever it replaced (or ``None``)."""
        slot = self.slot_for(item)
        if slot is None:
            return None
        replaced = getattr(self, slot)
        setattr(self, slot, item)
        return replaced

    def unequip(self, slot):
        replaced = getattr(self, slot, None)
        setattr(self, slot, None)
        return replaced

    def equipped_items(self):
        return [getattr(self, slot) for slot in SLOTS if getattr(self, slot)]
