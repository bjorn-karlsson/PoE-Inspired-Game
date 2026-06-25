# PoE-Inspired Game

A small **Path of Exile inspired** item-generation and combat engine written in
pure Python. It loads real PoE base-item and modifier data, rolls randomized
loot with readable affixes, equips it onto characters, and resolves combat
through an ARPG-style damage pipeline.

> This started as a year-old prototype (`Engine/`) and has been refactored into
> a clean, tested package (`poe_engine/`). See **[What changed](#what-changed)**.

## Quick start

No third-party dependencies — just Python 3.8+.

```bash
python play.py                 # generate loot, gear a hero, simulate a fight
python play.py --seed 42       # reproducible run
python play.py --drops 8 --drop-level 80
```

### Inventory Test (graphical bench)

A pygame inventory / character bench (no combat) for inspecting items and the
stat system:

```bash
pip install pygame
python inventory_test.py            # fullscreen, random loot
python inventory_test.py --seed 1   # reproducible loot
python inventory_test.py --windowed
```

- Inventory grid + equipment paper-doll; items show their **type** (the full
  name is in the tooltip).
- **Drag and drop**: drag a bag item onto the paper-doll to **equip** (auto-routed
  to the right slot), drag an equipped item back to the bag to **unequip**, and
  drag a currency orb onto a bag item to **use** it. Clicking still works too.
- Hover any item for a PoE-style tooltip (item level, requirements, properties,
  mods). **Hold Alt** to also see each mod's **affix type** (implicit / prefix /
  suffix), affix name, **tier** and value **range**. Tiers are **contextual to
  the base type**, matching the in-game tier numbers.
- **Currency** (12 orbs): Magic-and-better items drop **unidentified** (marked
  `?`); a **Scroll of Wisdom** identifies them. Transmutation / Augmentation /
  Alteration / Regal / Alchemy / Chaos / Exalted / Divine / Blessed / Annulment
  / Scouring each follow PoE-style crafting rules. Click an orb to select it (or
  drag it); right-click / Esc cancels.
- Stats panel with selectable **tabs** (Defense / Offense / Attributes / All)
  and mouse-wheel **scrolling**.
- **New Loot (reseed)** button rerolls everything with a fresh random seed.
- **Debug** mode: pick a stat and see exactly how it is built — every source
  item's flat / increased / more contribution, the final calculation, and a
  match-check against the engine total.
- Rarity is colour-coded (white/blue/yellow/orange).

Run the tests:

```bash
python -m unittest discover -s tests -v
python inventory_test.py --selftest   # headless smoke test of the UI
```

## Example

```python
from poe_engine import Character, Monster, seed
from poe_engine.items import Item
from poe_engine.combat import simulate_fight

seed(7)

# Roll a random item and print it like an in-game tooltip.
boots = Item.generate(drop_level=68, item_class="Boots", rarity_bonus=40)
print(boots.describe())

hero = Character("Hero", level=10)
hero.equip(boots)

winner = simulate_fight(hero, Monster("Goatman", level=8), verbose=True)
print("Winner:", winner.name)
```

## Architecture

```
poe_engine/
├── config.py        Constants & data paths
├── data.py          Lazy, cached loaders + derived indexes over the JSON data
├── rng.py           Shared seedable RNG (chance rolls, weighted choice)
├── serialize.py     reprJSON-based JSON encoding helpers
├── stats.py         Stat math (flat / increased / more) + the Stats sheet
├── stat_router.py   Maps raw mod stat-ids onto Stats fields
├── translate.py     Renders rolled mod stats into readable text
├── rarity.py        Rarity tiers and rolling
├── modifiers.py     A rolled modifier (value + readable lines)
├── items.py         Base selection, item generation, equipment slots
├── inventory.py     Size-limited inventory
├── character.py     BaseCharacter / Character / Monster
├── combat.py        Hit chance, crit, mitigation, damage application
└── data/            Bundled PoE base-item & modifier JSON
```

### How a stat is calculated

Every `Stat` combines its contributions the way ARPGs do:

```
(positive − negative) × (1 + increased% − reduced%) × more ÷ less
```

clamped to an optional min/max. Attribute bonuses (e.g. Strength → Life) are
applied during `Stats.calculate()` and are **idempotent** — recalculating never
double-counts them.

### How an item rolls

1. Pick an eligible base item for the requested `drop_level` / `item_class`.
2. Roll a rarity (Normal / Magic / Rare / Unique), influenced by a luck bonus.
3. Pick prefix/suffix counts for that rarity and draw mods by spawn weight,
   skipping duplicate mod groups, rolling each affix value within its range.
4. `item.build_stats()` routes the rolled stat-ids onto a `Stats` sheet so the
   item actually affects the wearer.

### Combat pipeline

`combat.attack(attacker, defender)`:

1. **Hit** — accuracy vs. evasion.
2. **Crit** — a crit multiplies the whole hit.
3. **Mitigate** — armour reduces physical; resistances reduce each element.
4. **Apply** — damage hits energy shield first, then life.

## What changed

The refactor fixed real bugs and reorganized the prototype:

- **Base-item selection bug** (`round(random()*len − 1)`) that could index `-1`
  and never picked the last base — replaced with proper weighted selection.
- **Stat-join bug** that copied Strength into Intelligence.
- **`calculate()` double-counting** attribute bonuses on repeated calls.
- **Inventory bug** (`if item := isinstance(...)`) treating a bool as an item.
- **Ring slots** that did nothing — now real dual `ring1` / `ring2` slots.
- Renamed the misspelled `choasResistance` → `chaosResistance`.
- Replaced debug `print` spam and a dead-code `main.py` with a real CLI demo.
- Added **mod value rolling**, **readable affix text**, a **combat pipeline**,
  a **seedable RNG**, **tests**, and standard repo hygiene
  (`.gitignore`, removed the committed `Engine.rar` and `__pycache__`).

## Roadmap ideas

- Hand-authored **unique** items with fixed mods.
- Tooltip **stat-diff** vs the currently-equipped item (green/red deltas).
- Skills, gems and damage-over-time.
- Persistence (save/load characters and stashes).
```
