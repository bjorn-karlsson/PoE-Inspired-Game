#!/usr/bin/env python3
"""Playable demo for the poe_engine.

Run it::

    python play.py            # generate loot + simulate a fight
    python play.py --seed 42  # reproducible run
    python play.py --drops 8  # show more generated items
"""

import argparse

from poe_engine import Character, Monster, seed
from poe_engine.combat import simulate_fight
from poe_engine.items import Item


def show_drops(count, drop_level):
    print(f"\n=== Generated {count} item drops (item level {drop_level}) ===\n")
    rare_or_better = []
    for _ in range(count):
        item = Item.generate(drop_level=drop_level)
        print(item.describe())
        print()
        if item.rarity.rarity.value >= 3:
            rare_or_better.append(item)
    return rare_or_better


def gear_up(character, drop_level):
    """Generate one item per slot family and equip what fits."""
    print("\n=== Gearing up the hero ===\n")
    for item_class in ("Helmet", "Body Armour", "Gloves", "Boots",
                       "Amulet", "Ring", "Ring", "Belt", "One Hand Sword"):
        item = Item.generate(drop_level=drop_level, item_class=item_class,
                            rarity_bonus=40)  # bias toward interesting items
        character.equip(item)
        print(f"Equipped: {item.name} ({item.rarity.rarity.name})")
    print(f"\n{character.name} life: {character.stats.life.totalStat}, "
          f"phys dmg: {character.stats.physicalDamage.totalStat}, "
          f"accuracy: {character.stats.accuracy.totalStat}")


def main():
    parser = argparse.ArgumentParser(description="poe_engine demo")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--drops", type=int, default=4)
    parser.add_argument("--drop-level", type=int, default=68)
    args = parser.parse_args()

    if args.seed is not None:
        seed(args.seed)

    show_drops(args.drops, args.drop_level)

    hero = Character("Hero", level=10)
    gear_up(hero, args.drop_level)

    monster = Monster("The Brine King", level=12)
    print(f"\n=== {hero.name} vs {monster.name} ===\n")
    winner = simulate_fight(hero, monster, max_rounds=50, verbose=True)
    print(f"\nWinner: {winner.name if winner else 'nobody (timeout)'}")


if __name__ == "__main__":
    main()
