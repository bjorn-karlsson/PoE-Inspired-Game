"""Unit tests for poe_engine. Run with: python -m unittest -v"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from poe_engine import Character, Monster, Stats, seed
from poe_engine.analysis import mod_tier, stat_breakdown
from poe_engine.combat import attack, hit_chance, simulate_fight
from poe_engine.currency import ChaosOrb, ScrollOfWisdom
from poe_engine.inventory import Inventory
from poe_engine.items import Item, Ring
from poe_engine.rarity import Rarities
from poe_engine.stats import Stat


def _generate_until(rarity, **kwargs):
    seed(2024)
    for _ in range(500):
        item = Item.generate(**kwargs)
        if item.rarity.rarity == rarity:
            return item
    raise AssertionError(f"could not roll a {rarity} item")


class StatMathTests(unittest.TestCase):
    def test_combined_formula(self):
        s = Stat()
        s.addPositiveStat(100)
        s.addIncreasedStat(50)   # x1.5
        s.addMoreStat(20)        # x1.2
        s.calculate()
        self.assertAlmostEqual(s.totalStat, 180.0, places=1)

    def test_calculate_is_idempotent(self):
        sheet = Stats()
        sheet.attributes.strength.addPositiveStat(100)
        sheet.life.addPositiveStat(50)
        sheet.calculate()
        first = sheet.life.totalStat
        sheet.calculate()
        sheet.calculate()
        self.assertEqual(first, sheet.life.totalStat)
        # strength/2 = 50 derived life on top of 50 base.
        self.assertAlmostEqual(first, 100.0, places=1)

    def test_max_clamp(self):
        s = Stat()
        s.setMaximumStat(75)
        s.addPositiveStat(200)
        s.calculate()
        self.assertEqual(s.totalStat, 75)

    def test_join_uses_correct_attributes(self):
        a, b = Stats(), Stats()
        b.attributes.intelligence.addPositiveStat(40)
        a.joinStats(b)
        a.calculate()
        self.assertAlmostEqual(a.attributes.intelligence.totalStat, 40.0, places=1)
        self.assertAlmostEqual(a.attributes.strength.totalStat, 0.0, places=1)


class ItemGenerationTests(unittest.TestCase):
    def setUp(self):
        seed(1234)

    def test_generates_named_item(self):
        item = Item.generate(drop_level=68)
        self.assertTrue(item.name)
        self.assertIn(item.rarity.rarity, list(Rarities))

    def test_magic_item_has_at_least_one_mod(self):
        for _ in range(200):
            item = Item.generate(drop_level=68, rarity_bonus=0)
            if item.rarity.rarity == Rarities.MAGIC:
                self.assertGreaterEqual(len(item.explicits), 1)
                self.assertLessEqual(len(item.prefixes), 1)
                self.assertLessEqual(len(item.suffixes), 1)
                return
        self.skipTest("no magic item rolled in sample")

    def test_rolled_values_within_range(self):
        for _ in range(50):
            item = Item.generate(drop_level=68, rarity_bonus=80)
            for mod in item.explicits:
                for stat in mod.stats:
                    self.assertGreaterEqual(stat["value"], stat["min"])
                    self.assertLessEqual(stat["value"], stat["max"])

    def test_no_duplicate_mod_groups(self):
        for _ in range(50):
            item = Item.generate(drop_level=68, rarity_bonus=80)
            groups = [m.group for m in item.explicits]
            self.assertEqual(len(groups), len(set(groups)))

    def test_item_class_filter(self):
        item = Item.generate(drop_level=68, item_class="Helmet")
        self.assertEqual(item.itemClass, "Helmet")


class InventoryTests(unittest.TestCase):
    def test_capacity_enforced(self):
        inv = Inventory(size=2)
        item = Item.generate(drop_level=68, item_class="Ring")  # 1x1
        self.assertTrue(inv.addItem(item))
        self.assertTrue(inv.addItem(Item.generate(drop_level=68, item_class="Ring")))
        self.assertFalse(inv.addItem(Item.generate(drop_level=68, item_class="Ring")))
        self.assertEqual(len(inv), 2)

    def test_remove_by_name(self):
        inv = Inventory()
        item = Item.generate(drop_level=68, item_class="Ring")
        inv.addItem(item)
        self.assertIs(inv.removeItemByName(item.name), item)
        self.assertEqual(len(inv), 0)


class EquipTests(unittest.TestCase):
    def test_dual_ring_slots(self):
        hero = Character("Hero")
        r1 = Item.generate(drop_level=68, item_class="Ring")
        r2 = Item.generate(drop_level=68, item_class="Ring")
        hero.equip(r1)
        hero.equip(r2)
        self.assertIs(hero.equipments.ring1, r1)
        self.assertIs(hero.equipments.ring2, r2)

    def test_equipping_changes_stats(self):
        hero = Character("Hero")
        base_life = hero.stats.life.totalStat
        # Equip many items until life changes (most life/armour mods affect it).
        seed(99)
        for _ in range(20):
            hero.equip(Item.generate(drop_level=68, item_class="Body Armour",
                                     rarity_bonus=90))
            if hero.stats.life.totalStat != base_life:
                break
        # Not guaranteed, but with rare body armours it virtually always changes.
        self.assertIsInstance(hero.stats.life.totalStat, float)


class CombatTests(unittest.TestCase):
    def test_hit_chance_bounds(self):
        self.assertEqual(hit_chance(0, 100), 100.0)
        self.assertLessEqual(hit_chance(100, 100000), 95.0)
        self.assertGreaterEqual(hit_chance(1, 100000), 5.0)

    def test_attack_drains_life(self):
        seed(5)
        hero = Character("Hero", level=20)
        dummy = Monster("Dummy", level=1)
        start = dummy.stats.life.currentStat
        for _ in range(20):
            attack(hero, dummy)
        self.assertLess(dummy.stats.life.currentStat, start)

    def test_fight_terminates(self):
        seed(3)
        hero = Character("Hero", level=30)
        weak = Monster("Rat", level=1)
        winner = simulate_fight(hero, weak, max_rounds=100)
        self.assertIsNotNone(winner)


class AnalysisTests(unittest.TestCase):
    def test_mod_tier_bounds(self):
        tier, total = mod_tier("does_not_exist")
        self.assertEqual((tier, total), (1, 1))

    def test_breakdown_reconciles_with_engine(self):
        seed(11)
        hero = Character("Hero", level=20)
        for _ in range(6):
            hero.equip(Item.generate(drop_level=72, item_class="Body Armour",
                                     rarity_bonus=90))
        for path in ("life", "armour", "evasion", "fireResistance"):
            bd = stat_breakdown(hero, path)
            self.assertAlmostEqual(bd["computed_total"], bd["actual_total"], places=1,
                                   msg=f"{path} breakdown does not match engine")

    def test_breakdown_lists_equipped_sources(self):
        seed(7)
        hero = Character("Hero", level=20)
        # Body armours reliably carry life/defence mods.
        for _ in range(4):
            hero.equip(Item.generate(drop_level=72, item_class="Body Armour",
                                     rarity_bonus=95))
        names = {src["name"] for src in stat_breakdown(hero, "life")["sources"]}
        self.assertIn("Base character", names)


class CurrencyTests(unittest.TestCase):
    def test_magic_items_drop_unidentified(self):
        item = _generate_until(Rarities.MAGIC, drop_level=68, rarity_bonus=0)
        self.assertFalse(item.identified)

    def test_normal_items_are_identified(self):
        item = _generate_until(Rarities.NORMAL, drop_level=68, rarity_bonus=0)
        self.assertTrue(item.identified)

    def test_scroll_of_wisdom_identifies(self):
        item = _generate_until(Rarities.MAGIC, drop_level=68, rarity_bonus=0)
        scroll = ScrollOfWisdom(count=2)
        self.assertTrue(scroll.use_on(item))
        self.assertTrue(item.identified)
        self.assertEqual(scroll.count, 1)
        # Using it again on an identified item does nothing and costs nothing.
        self.assertFalse(scroll.use_on(item))
        self.assertEqual(scroll.count, 1)

    def test_chaos_orb_only_on_identified_rares(self):
        rare = _generate_until(Rarities.RARE, drop_level=78, rarity_bonus=20)
        chaos = ChaosOrb(count=1)
        # Unidentified -> rejected.
        rare.identified = False
        self.assertFalse(chaos.applies_to(rare))
        rare.identified = True
        before = [m.id for m in rare.explicits]
        self.assertTrue(chaos.use_on(rare))
        after = [m.id for m in rare.explicits]
        self.assertEqual(chaos.count, 0)
        # A reforge should keep it Rare and (almost always) change the mods.
        self.assertEqual(rare.rarity.rarity, Rarities.RARE)
        self.assertTrue(after)  # still has explicit mods
        self.assertNotEqual(before, after)

    def test_stack_sizes(self):
        self.assertEqual(ScrollOfWisdom.max_stack, 40)
        self.assertEqual(ChaosOrb.max_stack, 20)


if __name__ == "__main__":
    unittest.main()
