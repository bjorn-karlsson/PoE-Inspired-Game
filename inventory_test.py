#!/usr/bin/env python3
"""Inventory Test -- a graphical inventory / character bench for poe_engine.

A no-combat sandbox to inspect items, currency and the stat system:

* Resizable window; equipment paper-doll + a grid inventory that holds both
  items and stackable currency.
* Drag items onto the paper-doll to equip (only items that have a slot), drag
  equipped items back to the bag to unequip, drag items around the bag to
  rearrange, and drag a currency orb onto an item to use it.
* Hover an item for a PoE-style tooltip (item level, quality, requirements,
  mods). Hold **Alt** to also see each mod's affix type, name, tier and range.
* Stats panel with tabs (Defense / Offense / Attributes / All) + scrolling.
* **Debug** mode breaks a stat down by source with the full calculation.
* **New Loot** rerolls everything with a fresh random seed.

Run it::

    python inventory_test.py
    python inventory_test.py --seed 1
    python inventory_test.py --fullscreen
"""

import argparse
import os
import random as _random

import pygame

from poe_engine import CLASS_NAMES, Character
from poe_engine.analysis import mod_tier, resolve_stat, stat_breakdown
from poe_engine.currency import starter_currency
from poe_engine.items import SLOTS, Item
from poe_engine.rarity import Rarities
from poe_engine.rng import seed as rng_seed


# ---------------------------------------------------------------- colours ----
TEXT = (224, 224, 230)
DIM = (152, 152, 165)
FAINT = (108, 108, 124)
ACCENT = (214, 178, 96)
PANEL = (30, 31, 40)
PANEL_LIGHT = (52, 53, 66)
CELL = (22, 23, 30)
SLOT_BG = (40, 41, 54)
SLOT_EMPTY = (92, 93, 110)
BTN = (54, 55, 70)
BTN_HOT = (74, 76, 96)
BTN_ON = (74, 104, 78)
GOOD = (130, 220, 140)
BAD = (228, 120, 120)
QUALITY = (120, 210, 160)

RARITY_COLORS = {
    Rarities.NORMAL: (200, 200, 205),
    Rarities.MAGIC: (122, 152, 255),
    Rarities.RARE: (238, 218, 92),
    Rarities.UNIQUE: (208, 120, 46),
}
IMPLICIT_COLOR = (120, 200, 255)
EXPLICIT_COLOR = (162, 172, 255)

DOLL_LAYOUT = {
    "helmet": (1, 0), "amulet": (2, 0),
    "weapon": (0, 1), "bodyArmour": (1, 1), "offhand": (2, 1),
    "gloves": (0, 2), "belt": (1, 2), "ring1": (2, 2),
    "boots": (0, 3), "ring2": (2, 3),
}
SLOT_LABELS = {
    "weapon": "Weapon", "offhand": "Off-hand", "helmet": "Helmet",
    "bodyArmour": "Body", "gloves": "Gloves", "boots": "Boots",
    "amulet": "Amulet", "belt": "Belt", "ring1": "Ring", "ring2": "Ring",
}

STAT_REGISTRY = [
    ("attributes.strength", "Strength", "attr", "num"),
    ("attributes.dexterity", "Dexterity", "attr", "num"),
    ("attributes.intelligence", "Intelligence", "attr", "num"),
    ("life", "Life", "def", "num"),
    ("life.regenerateStat", "Life Regen", "def", "num"),
    ("mana", "Mana", "def", "num"),
    ("mana.regenerateStat", "Mana Regen", "def", "num"),
    ("energyShield", "Energy Shield", "def", "num"),
    ("armour", "Armour", "def", "num"),
    ("evasion", "Evasion", "def", "num"),
    ("fireResistance", "Fire Resistance", "def", "pct"),
    ("coldResistance", "Cold Resistance", "def", "pct"),
    ("lightningResistance", "Lightning Resistance", "def", "pct"),
    ("chaosResistance", "Chaos Resistance", "def", "pct"),
    ("physicalDamage", "Physical Damage", "off", "num"),
    ("fireDamage", "Fire Damage", "off", "num"),
    ("coldDamage", "Cold Damage", "off", "num"),
    ("lightningDamage", "Lightning Damage", "off", "num"),
    ("chaosDamage", "Chaos Damage", "off", "num"),
    ("spellDamage", "Spell Damage", "off", "num"),
    ("rangedDamage", "Ranged Damage", "off", "num"),
    ("accuracy", "Accuracy", "off", "num"),
    ("attackSpeed", "Attack Speed", "off", "num"),
    ("castSpeed", "Cast Speed", "off", "num"),
    ("criticalStrikeChance", "Crit Chance", "off", "pct1"),
    ("criticalStrikeDamage", "Crit Multiplier", "off", "pctplus"),
]
TABS = [("Defense", "def"), ("Offense", "off"), ("Attributes", "attr"), ("All", "all")]


def fmt_stat(stat, fmt):
    v = stat.totalStat
    if fmt == "pct":
        return f"{v:.0f}%"
    if fmt == "pct1":
        return f"{v:.1f}%"
    if fmt == "pctplus":
        return f"+{v:.0f}%"
    return f"{v:.1f}".rstrip("0").rstrip(".") or "0"


def prettify(stat_id):
    s = stat_id
    for prefix in ("local_", "base_"):
        if s.startswith(prefix):
            s = s[len(prefix):]
    return s.replace("_", " ")


_STOPWORDS = {"orb", "of", "scroll", "s", "blacksmith's", "armourer's"}


def orb_abbrev(name):
    for word in name.replace("'", "").split():
        if word.lower() not in _STOPWORDS:
            return word[:3]
    return name[:3]


def orb_color(name):
    palette = {
        "Wisdom": (120, 190, 230), "Transmutation": (120, 150, 240),
        "Augmentation": (120, 150, 240), "Alteration": (110, 130, 235),
        "Regal": (210, 160, 90), "Alchemy": (235, 200, 110),
        "Chaos": (210, 120, 60), "Exalted": (235, 215, 130),
        "Divine": (245, 235, 205), "Blessed": (200, 150, 230),
        "Annulment": (210, 110, 120), "Scouring": (160, 160, 170),
        "Whetstone": (170, 175, 185), "Scrap": (180, 150, 120),
    }
    for word in name.replace("'", "").split():
        if word in palette:
            return palette[word]
    return (180, 160, 110)


# ----------------------------------------------------------- bag entries ----
class Entry:
    """An item or a currency stack placed on the inventory grid."""

    def __init__(self, obj, currency=False):
        self.obj = obj
        self.currency = currency
        self.x = 0
        self.y = 0

    @property
    def w(self):
        return 1 if self.currency else max(1, self.obj.inventoryWidth)

    @property
    def h(self):
        return 1 if self.currency else max(1, self.obj.inventoryHeight)


# ----------------------------------------------------------- demo content ----
def make_loot(item_count=20, drop_level=74):
    classes = ["Helmet", "Body Armour", "Gloves", "Boots", "Amulet", "Ring",
               "Belt", "One Hand Sword", "Two Hand Axe", "Shield", "Bow",
               "Wand", "Sceptre", "Staff"]
    items = []
    for i in range(item_count):
        items.append(Item.generate(drop_level=drop_level,
                                    item_class=classes[i % len(classes)],
                                    rarity_bonus=22))
    return items


# ------------------------------------------------------------- the screen ----
class InventoryTest:
    def __init__(self, screen, item_count=20):
        self.screen = screen
        self.item_count = item_count
        self.W, self.H = screen.get_size()

        self.f_tiny = pygame.font.Font(None, 19)
        self.f_small = pygame.font.Font(None, 22)
        self.f = pygame.font.Font(None, 26)
        self.f_big = pygame.font.Font(None, 38)

        self.char_class = "Marauder"
        self.character = Character("Exile", char_class=self.char_class, level=1)
        self.entries = []

        # UI state
        self.tab = "def"
        self.cursor_item = None       # Entry picked up onto the cursor (move/equip)
        self.cursor_currency = None   # currency Entry readied on the cursor
        self.scroll = 0
        self.debug_mode = False
        self.debug_stat = None
        self.dbg_scroll = 0
        self._content_h = 0
        self._bd_cache = None
        self._bd_sig = None
        self.status_text = ""
        self.status_timer = 0

        self.slot_rects = {}
        self.buttons = {}
        self.tab_rects = []
        self.dbg_rows = []
        self.back_rect = None
        self.bg = None

        self._build_layout()
        self._fill_bag()

    # ===================================================== layout ============
    def on_resize(self, w, h):
        self.W, self.H = max(1120, w), max(720, h)
        self._build_layout()
        # keep positions; re-place anything that no longer fits
        for entry in self.entries:
            if not self._fits(entry, entry.x, entry.y):
                self._place(entry)

    def _build_layout(self):
        margin = 36
        self.panel_top = 132
        self.panel_bottom = self.H - 54
        self.panel_h = self.panel_bottom - self.panel_top

        # paper-doll
        self.doll_cell = max(74, min(96, (self.panel_h - 30) // 5))
        self.doll_gap = 10
        self.doll_origin = (margin, self.panel_top + 6)
        doll_w = 3 * (self.doll_cell + self.doll_gap) - self.doll_gap
        self.doll_panel = pygame.Rect(margin - 8, self.panel_top - 4,
                                      doll_w + 16, self.panel_h + 4)
        self.slot_rects = {}
        ox, oy = self.doll_origin
        for slot, (col, row) in DOLL_LAYOUT.items():
            x = ox + col * (self.doll_cell + self.doll_gap)
            y = oy + row * (self.doll_cell + self.doll_gap)
            self.slot_rects[slot] = pygame.Rect(x, y, self.doll_cell, self.doll_cell)

        # stats column
        self.stats_x = self.doll_panel.right + 28
        self.stats_w = 366
        self.stats_panel = pygame.Rect(self.stats_x, self.panel_top,
                                       self.stats_w, self.panel_h)

        # inventory column
        inv_x = self.stats_panel.right + 28
        self.inv_cell = 54
        self.inv_origin = (inv_x + 10, self.panel_top + 10)
        avail_w = self.W - margin - self.inv_origin[0]
        self.inv_cols = max(6, avail_w // self.inv_cell)
        self.inv_rows = max(6, (self.panel_h - 20) // self.inv_cell)
        self.inv_panel = pygame.Rect(inv_x, self.panel_top,
                                     self.inv_cols * self.inv_cell + 20,
                                     self.panel_h)

        # toolbar buttons (top-right, clear of the section headers)
        self.buttons = {}
        defs = [
            ("debug", f"Debug: {'ON' if self.debug_mode else 'OFF'}"),
            ("reload", "New Loot"),
            ("levelup", "Level +1"),
            ("class", f"Class: {self.char_class}"),
        ]
        x = self.W - margin
        for name, label in defs:
            w = self.f_small.size(label)[0] + 24
            x -= w
            self.buttons[name] = pygame.Rect(x, 34, w, 34)
            x -= 10

        # stat tabs
        self.tab_rects = []
        tx = self.stats_x + 6
        for label, key in TABS:
            w = self.f_small.size(label)[0] + 20
            self.tab_rects.append((key, label, pygame.Rect(tx, self.panel_top - 36, w, 28)))
            tx += w + 6

        self.bg = self._make_gradient()

    def _make_gradient(self):
        surf = pygame.Surface((self.W, self.H))
        top, bot = (24, 26, 36), (12, 12, 17)
        for y in range(self.H):
            t = y / max(1, self.H - 1)
            surf.fill(tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3)),
                      (0, y, self.W, 1))
        return surf

    # ===================================================== bag model =========
    def _fill_bag(self):
        self.entries = [Entry(i) for i in make_loot(self.item_count)]
        self.entries += [Entry(c, currency=True) for c in starter_currency()]
        # place items first (largest first), then currency
        self.entries.sort(key=lambda e: (e.currency, -(e.w * e.h)))
        for entry in self.entries:
            self._place(entry)

    def _fits(self, entry, gx, gy):
        if gx < 0 or gy < 0 or gx + entry.w > self.inv_cols or gy + entry.h > self.inv_rows:
            return False
        for other in self.entries:
            if other is entry:
                continue
            if (gx < other.x + other.w and gx + entry.w > other.x and
                    gy < other.y + other.h and gy + entry.h > other.y):
                return False
        return True

    def _place(self, entry):
        for y in range(self.inv_rows):
            for x in range(self.inv_cols):
                if self._fits(entry, x, y):
                    entry.x, entry.y = x, y
                    return True
        return False

    def _entry_rect(self, entry):
        ox, oy = self.inv_origin
        return pygame.Rect(ox + entry.x * self.inv_cell + 2,
                           oy + entry.y * self.inv_cell + 2,
                           entry.w * self.inv_cell - 4, entry.h * self.inv_cell - 4)

    def _entry_at(self, pos):
        for entry in self.entries:
            if self._entry_rect(entry).collidepoint(pos):
                return entry
        return None

    def _cell_at(self, pixel):
        ox, oy = self.inv_origin
        return ((pixel[0] - ox) // self.inv_cell, (pixel[1] - oy) // self.inv_cell)

    def _equippable(self, item):
        return self.character.equipments.slot_for(item) is not None

    def _slot_at(self, pos):
        for slot, rect in self.slot_rects.items():
            if rect.collidepoint(pos):
                return slot
        return None

    # ===================================================== interaction =======
    # Path-of-Exile-style mouse model:
    #   Left-click  -> pick an item up onto the cursor; left-click again to place
    #                  it (empty cell, equipment slot, or swap). While a currency
    #                  orb is on the cursor, left-click an item to use it.
    #   Right-click -> action: equip an item / unequip a slot; right-click a
    #                  currency to put it on the cursor (then left-click items to
    #                  apply it -- it stays until you right-click / Esc to cancel).
    def on_left_down(self, pos):
        if self._ui_click(pos):
            return
        if self.cursor_currency is not None:
            target = self._entry_at(pos)
            if target is not None and not target.currency:
                self._apply_currency(target.obj)
            return
        if self.cursor_item is not None:
            self._place_cursor_item(pos)
            return
        # empty hand: pick something up
        entry = self._entry_at(pos)
        if entry is not None:
            self.entries.remove(entry)
            self.cursor_item = entry
            return
        slot = self._slot_at(pos)
        if slot and getattr(self.character.equipments, slot):
            item = getattr(self.character.equipments, slot)
            self.character.unequip(slot)
            self._invalidate()
            self.cursor_item = Entry(item)

    def on_right_down(self, pos):
        if self.cursor_item is not None:
            self._return_cursor_item()
            return
        if self.cursor_currency is not None:
            self.cursor_currency = None
            return
        if self._ui_click(pos):
            return
        entry = self._entry_at(pos)
        if entry is not None:
            if entry.currency:
                self.cursor_currency = entry
                self._flash(f"{entry.obj.name} ready — left-click an item "
                            f"(right-click / Esc to cancel)")
            else:
                self._quick_equip(entry)
            return
        slot = self._slot_at(pos)
        if slot and getattr(self.character.equipments, slot):
            self._unequip(slot)

    # -- cursor item (move / equip / swap) ---------------------------------
    def _place_cursor_item(self, pos):
        entry = self.cursor_item
        item = entry.obj
        slot = self._slot_at(pos)
        if slot is not None:
            if self._try_equip_cursor(item):
                return
        if self.inv_panel.collidepoint(pos):
            gx, gy = self._cell_at(pos)
            if self._fits(entry, gx, gy):
                entry.x, entry.y = gx, gy
                self.entries.append(entry)
                self.cursor_item = None
                return
            self._try_swap(entry, pos)
        # clicked elsewhere: keep holding the item

    def _try_equip_cursor(self, item):
        if not item.identified:
            self._flash("Identify the item first (Scroll of Wisdom)")
            return True
        if not self._equippable(item):
            self._flash(f"{item.itemClass} can't be equipped there")
            return True
        replaced = self.character.equip(item)
        self._invalidate()
        self.cursor_item = Entry(replaced) if replaced is not None else None
        return True

    def _try_swap(self, entry, pos):
        occ = self._entry_at(pos)
        if occ is None or occ.currency:
            self._flash("Doesn't fit there")
            return
        ox, oy = occ.x, occ.y
        self.entries.remove(occ)
        if self._fits(entry, ox, oy):
            entry.x, entry.y = ox, oy
            self.entries.append(entry)
            self.cursor_item = occ  # swapped item goes to the cursor
        else:
            self.entries.append(occ)
            self._flash("Doesn't fit there")

    def _return_cursor_item(self):
        if self._place(self.cursor_item):
            self.entries.append(self.cursor_item)
            self.cursor_item = None
        else:
            self._flash("No room to drop it")

    # -- equipment / currency ----------------------------------------------
    def _quick_equip(self, entry):
        item = entry.obj
        if not item.identified:
            self._flash("Identify the item first (Scroll of Wisdom)")
            return
        if not self._equippable(item):
            self._flash(f"{item.itemClass} can't be equipped")
            return
        self.entries.remove(entry)
        replaced = self.character.equip(item)
        if replaced is not None:
            self._add_to_bag(replaced)
        self._invalidate()

    def _unequip(self, slot):
        item = getattr(self.character.equipments, slot)
        if item is None:
            return
        self.character.unequip(slot)
        self._add_to_bag(item)
        self._invalidate()

    def _add_to_bag(self, item):
        entry = Entry(item)
        if not self._place(entry):
            self._flash("No room in inventory")
            return
        self.entries.append(entry)

    def _apply_currency(self, item):
        entry = self.cursor_currency
        cur = entry.obj
        if cur.use_on(item):
            self._flash(f"{cur.name} used on {item.name}")
            self._invalidate()
            if cur.count <= 0:
                if entry in self.entries:
                    self.entries.remove(entry)
                self.cursor_currency = None
            # otherwise the orb stays on the cursor (PoE-style repeat use)
        else:
            self._flash(f"{cur.name}: {cur.reason(item)}")

    def _ui_click(self, pos):
        """Handle clicks on toolbar / tabs / debug rows. Returns True if used."""
        for name, fn in (("reload", self.reload_loot), ("debug", self._toggle_debug),
                         ("levelup", self._level_up), ("class", self._cycle_class)):
            if self.buttons[name].collidepoint(pos):
                fn()
                return True
        for key, _, rect in self.tab_rects:
            if rect.collidepoint(pos):
                self.tab, self.scroll = key, 0
                return True
        if self.debug_mode and self.debug_stat is not None:
            if self.back_rect and self.back_rect.collidepoint(pos):
                self.debug_stat = None
                self.dbg_scroll = 0
            return True
        if self.debug_mode:
            for path, rect in self.dbg_rows:
                if rect.collidepoint(pos):
                    self.debug_stat = path
                    self.dbg_scroll = 0
                    return True
            return True  # swallow clicks inside debug panel
        return False

    def _toggle_debug(self):
        self.debug_mode = not self.debug_mode
        self.debug_stat = None
        self.scroll = self.dbg_scroll = 0

    def _level_up(self):
        self.character.level_up()
        self._invalidate()
        self._flash(f"Levelled up to {self.character.level}")

    def _cycle_class(self):
        self.cursor_item = self.cursor_currency = None
        self._unequip_all()
        idx = (CLASS_NAMES.index(self.char_class) + 1) % len(CLASS_NAMES)
        self.char_class = CLASS_NAMES[idx]
        self.character = Character("Exile", char_class=self.char_class, level=1)
        self._invalidate()
        self._flash(f"Class: {self.char_class} (reset to level 1)")

    def _unequip_all(self):
        for slot in list(SLOTS):
            if getattr(self.character.equipments, slot):
                self._unequip(slot)

    def handle_scroll(self, dy, pos):
        if self.stats_panel.collidepoint(pos):
            step = 36
            if self.debug_mode and self.debug_stat:
                self.dbg_scroll = max(0, self.dbg_scroll - dy * step)
            else:
                self.scroll = max(0, self.scroll - dy * step)

    def handle_escape(self):
        if self.cursor_item is not None:
            self._return_cursor_item()
            return True
        if self.cursor_currency is not None:
            self.cursor_currency = None
            return True
        if self.debug_mode and self.debug_stat is not None:
            self.debug_stat = None
            return True
        if self.debug_mode:
            self.debug_mode = False
            return True
        return False

    def reload_loot(self):
        rng_seed(_random.randrange(1 << 30))
        self.character = Character("Exile", char_class=self.char_class, level=1)
        self.debug_stat = None
        self.cursor_item = None
        self.cursor_currency = None
        self.scroll = self.dbg_scroll = 0
        self._invalidate()
        self._fill_bag()
        self._flash("Rerolled all loot with a new seed")

    def _invalidate(self):
        self._bd_sig = None

    def _flash(self, text):
        self.status_text = text
        self.status_timer = 220

    # ===================================================== drawing ===========
    def draw(self, mouse_pos):
        s = self.screen
        s.blit(self.bg, (0, 0))

        s.blit(self.f_big.render(f"{self.character.name}", True, ACCENT), (36, 30))
        lvl = self.f_small.render(
            f"{self.char_class}  ·  Level {self.character.level}  ·  Inventory Test",
            True, DIM)
        s.blit(lvl, (36, 70))

        self._draw_toolbar(mouse_pos)
        self._header(s, "EQUIPMENT", self.doll_panel.x + 8, self.panel_top - 32)
        self._header(s, "CHARACTER" if not self.debug_mode else "DEBUG — STAT BREAKDOWN",
                     self.stats_x + 6, 70)
        self._header(s, "INVENTORY", self.inv_panel.x, self.panel_top - 32)

        self._draw_doll(s)
        if self.debug_mode:
            self._draw_debug(s)
        else:
            self._draw_stats(s)
        self._draw_inventory(s, mouse_pos)

        self._draw_help(s)
        if self.cursor_item is not None:
            self._draw_item_cursor(s, mouse_pos)
        elif self.cursor_currency is not None:
            self._draw_tooltip(s, mouse_pos)
            self._draw_orb_cursor(s, mouse_pos)
        else:
            self._draw_tooltip(s, mouse_pos)

        if self.status_timer > 0:
            self.status_timer -= 1
            surf = self.f_small.render(self.status_text, True, ACCENT)
            surf.set_alpha(min(255, self.status_timer * 3))
            s.blit(surf, (36, self.H - 78))

    def _header(self, s, text, x, y):
        surf = self.f.render(text, True, DIM)
        s.blit(surf, (x, y))
        pygame.draw.line(s, PANEL_LIGHT, (x, y + 26), (x + surf.get_width(), y + 26), 2)

    def _panel(self, s, rect):
        pygame.draw.rect(s, PANEL, rect, border_radius=10)
        pygame.draw.rect(s, PANEL_LIGHT, rect, width=1, border_radius=10)

    def _button(self, s, rect, label, hot, on=False):
        pygame.draw.rect(s, BTN_ON if on else (BTN_HOT if hot else BTN), rect, border_radius=7)
        pygame.draw.rect(s, PANEL_LIGHT, rect, width=1, border_radius=7)
        surf = self.f_small.render(label, True, TEXT)
        s.blit(surf, surf.get_rect(center=rect.center))

    def _draw_toolbar(self, mouse_pos):
        s = self.screen
        b = self.buttons
        self._button(s, b["class"], f"Class: {self.char_class}",
                     b["class"].collidepoint(mouse_pos))
        self._button(s, b["levelup"], "Level +1", b["levelup"].collidepoint(mouse_pos))
        self._button(s, b["reload"], "New Loot", b["reload"].collidepoint(mouse_pos))
        self._button(s, b["debug"], f"Debug: {'ON' if self.debug_mode else 'OFF'}",
                     b["debug"].collidepoint(mouse_pos), on=self.debug_mode)

    def _draw_doll(self, s):
        self._panel(s, self.doll_panel)
        for slot, rect in self.slot_rects.items():
            pygame.draw.rect(s, SLOT_BG, rect, border_radius=7)
            pygame.draw.rect(s, PANEL_LIGHT, rect, width=2, border_radius=7)
            item = getattr(self.character.equipments, slot)
            if item is None:
                lbl = self.f_small.render(SLOT_LABELS[slot], True, SLOT_EMPTY)
                s.blit(lbl, lbl.get_rect(center=rect.center))
            else:
                self._draw_item_icon(s, item, rect)

    def _draw_inventory(self, s, mouse_pos):
        self._panel(s, self.inv_panel)
        ox, oy = self.inv_origin
        grid = pygame.Rect(ox, oy, self.inv_cols * self.inv_cell, self.inv_rows * self.inv_cell)
        for c in range(self.inv_cols + 1):
            x = ox + c * self.inv_cell
            pygame.draw.line(s, (38, 39, 50), (x, oy), (x, grid.bottom))
        for r in range(self.inv_rows + 1):
            y = oy + r * self.inv_cell
            pygame.draw.line(s, (38, 39, 50), (ox, y), (grid.right, y))
        for entry in self.entries:
            rect = self._entry_rect(entry)
            if entry.currency:
                self._draw_currency_icon(s, entry.obj, rect)
            else:
                self._draw_item_icon(s, entry.obj, rect)

    def _draw_item_icon(self, s, item, rect):
        color = RARITY_COLORS.get(item.rarity.rarity, TEXT)
        pygame.draw.rect(s, CELL, rect, border_radius=6)
        pygame.draw.rect(s, color, rect, width=2, border_radius=6)
        self._wrapped_centered(s, item.itemClass, color, rect)
        if not item.identified:
            self._badge(s, rect.right - 17, rect.y + 3, "?", (235, 180, 90), (60, 45, 20))
        if getattr(item, "quality", 0):
            self._badge(s, rect.x + 4, rect.bottom - 18, f"{item.quality}", QUALITY, (24, 50, 36))

    def _draw_currency_icon(self, s, cur, rect):
        pygame.draw.rect(s, (30, 30, 40), rect, border_radius=6)
        pygame.draw.rect(s, (90, 84, 60), rect, width=1, border_radius=6)
        base = orb_color(cur.name)
        cx, cy = rect.centerx, rect.centery - 4
        pygame.draw.circle(s, base, (cx, cy), 15)
        pygame.draw.circle(s, (240, 236, 222), (cx - 5, cy - 5), 4)
        abbr = self.f_tiny.render(orb_abbrev(cur.name), True, (20, 18, 14))
        s.blit(abbr, abbr.get_rect(center=(cx, cy + 1)))
        cnt = self.f_tiny.render(str(cur.count), True, TEXT)
        s.blit(cnt, cnt.get_rect(centerx=cx, bottom=rect.bottom - 2))

    def _badge(self, s, x, y, text, fg, bg):
        rect = pygame.Rect(x, y, 15, 15)
        pygame.draw.rect(s, bg, rect, border_radius=3)
        surf = self.f_tiny.render(text, True, fg)
        s.blit(surf, surf.get_rect(center=rect.center))

    def _wrapped_centered(self, s, text, color, rect):
        words = str(text).split()
        lines, cur = [], ""
        for w in words:
            t = (cur + " " + w).strip()
            if self.f_tiny.size(t)[0] <= rect.width - 8:
                cur = t
            else:
                if cur:
                    lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        y = rect.centery - len(lines) * 8
        for line in lines[: max(1, rect.height // 16)]:
            surf = self.f_tiny.render(line, True, color)
            s.blit(surf, surf.get_rect(centerx=rect.centerx, y=y))
            y += 16

    # ---- stats panel -----------------------------------------------------
    def _draw_tabs(self, s, mouse_pos):
        for key, label, rect in self.tab_rects:
            self._button(s, rect, label, rect.collidepoint(mouse_pos), on=(self.tab == key))

    def _draw_stats(self, s):
        self._draw_tabs(s, pygame.mouse.get_pos())
        panel = self.stats_panel
        self._panel(s, panel)
        entries = [e for e in STAT_REGISTRY if self.tab in (e[2], "all")]
        s.set_clip(panel.inflate(-4, -4))
        x = panel.x + 16
        y = panel.y + 14 - self.scroll
        for path, label, _cat, fmt in entries:
            stat = resolve_stat(self.character.stats, path)
            if panel.y - 24 <= y <= panel.bottom:
                s.blit(self.f_small.render(label, True, DIM), (x, y))
                vs = self.f_small.render(fmt_stat(stat, fmt), True, TEXT)
                s.blit(vs, vs.get_rect(right=panel.right - 16, y=y))
            y += 27
        s.set_clip(None)
        self._content_h = len(entries) * 27 + 28
        self._clamp("scroll", panel.height)

    def _clamp(self, attr, view_h):
        setattr(self, attr, min(getattr(self, attr), max(0, self._content_h - view_h)))

    # ---- debug -----------------------------------------------------------
    def _draw_debug(self, s):
        panel = self.stats_panel
        self._panel(s, panel)
        if self.debug_stat is None:
            self._draw_debug_list(s, panel)
        else:
            self._draw_debug_detail(s, panel)

    def _draw_debug_list(self, s, panel):
        s.set_clip(panel.inflate(-4, -4))
        self.dbg_rows = []
        x, y = panel.x + 14, panel.y + 12 - self.scroll
        s.blit(self.f_tiny.render("click a stat to inspect", True, FAINT), (x, y))
        y += 24
        mouse = pygame.mouse.get_pos()
        for path, label, _cat, fmt in STAT_REGISTRY:
            row = pygame.Rect(panel.x + 6, y - 2, panel.width - 12, 24)
            self.dbg_rows.append((path, row))
            if panel.y <= y <= panel.bottom:
                if row.collidepoint(mouse):
                    pygame.draw.rect(s, PANEL_LIGHT, row, border_radius=4)
                s.blit(self.f_small.render(label, True, TEXT), (x, y))
                stat = resolve_stat(self.character.stats, path)
                vs = self.f_small.render(fmt_stat(stat, fmt), True, DIM)
                s.blit(vs, vs.get_rect(right=panel.right - 14, y=y))
            y += 26
        s.set_clip(None)
        self._content_h = len(STAT_REGISTRY) * 26 + 44
        self._clamp("scroll", panel.height)

    def _breakdown(self):
        eq = self.character.equipments
        sig = (self.debug_stat, tuple(id(getattr(eq, slot)) for slot in SLOTS))
        if sig != self._bd_sig:
            self._bd_cache = stat_breakdown(self.character, self.debug_stat)
            self._bd_sig = sig
        return self._bd_cache

    def _draw_debug_detail(self, s, panel):
        bd = self._breakdown()
        label = next((e[1] for e in STAT_REGISTRY if e[0] == self.debug_stat), self.debug_stat)
        self.dbg_rows = []
        self.back_rect = pygame.Rect(panel.x + 6, panel.y + 6, 150, 26)
        hot = self.back_rect.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(s, BTN_HOT if hot else BTN, self.back_rect, border_radius=5)
        s.blit(self.f_tiny.render("‹ back to list", True, TEXT),
               (self.back_rect.x + 10, self.back_rect.y + 6))

        s.set_clip(panel.inflate(-4, -4))
        x, y = panel.x + 12, panel.y + 40 - self.dbg_scroll

        def line(text, color, indent=0, font=None):
            nonlocal y
            font = font or self.f_small
            if panel.y - 20 <= y <= panel.bottom:
                s.blit(font.render(text, True, color), (x + indent, y))
            y += font.get_height() - 2

        line(label, ACCENT, font=self.f)
        y += 4
        for src in bd["sources"]:
            line(src["name"], TEXT)
            comp = src["components"]
            for key in ("positive", "negative", "increased", "reduced", "more", "less"):
                if key not in comp:
                    continue
                val = comp[key]
                if key == "positive":
                    txt, col = f"+{val:g} flat", GOOD
                elif key == "negative":
                    txt, col = f"-{val:g} flat", BAD
                elif key == "increased":
                    txt, col = f"+{val:g}% increased", GOOD if val >= 0 else BAD
                elif key == "reduced":
                    txt, col = f"-{val:g}% reduced", BAD
                elif key == "more":
                    txt, col = f"x{val:.3g} more", GOOD
                else:
                    txt, col = f"x{val:.3g} less", BAD
                line(txt, col, indent=22, font=self.f_tiny)
            y += 4
        if not bd["sources"]:
            line("(no contributions)", FAINT, indent=12)
        y += 6
        pygame.draw.line(s, PANEL_LIGHT, (x, y), (panel.right - 14, y))
        y += 10
        t = bd["totals"]
        line("Combined:", DIM)
        line(f"flat = {t['positive'] - t['negative']:g}", TEXT, 12, self.f_tiny)
        line(f"increased = {t['increased'] - t['reduced']:g}%", TEXT, 12, self.f_tiny)
        line(f"more/less = x{t['more'] / t['less']:.3g}", TEXT, 12, self.f_tiny)
        y += 6
        flat = t["positive"] - t["negative"]
        incmul = 1 + (t["increased"] - t["reduced"]) / 100
        line("(flat) x (1 + inc%) x more", FAINT, 0, self.f_tiny)
        line(f"= {flat:g} x {incmul:.3g} x {t['more'] / t['less']:.3g}", TEXT, 12, self.f_tiny)
        line(f"= {bd['computed_total']:g}", GOOD, 12)
        if bd["clamp"]:
            line(f"({bd['clamp']})", BAD, 12, self.f_tiny)
        y += 4
        match = abs(bd["computed_total"] - bd["actual_total"]) < 0.05
        line(f"engine total = {bd['actual_total']:g}  {'[match]' if match else '[MISMATCH]'}",
             GOOD if match else BAD, 0, self.f_tiny)
        s.set_clip(None)
        self._content_h = (y + self.dbg_scroll) - panel.y + 20
        self._clamp("dbg_scroll", panel.height)

    # ---- help / ghost ----------------------------------------------------
    def _draw_help(self, s):
        txt = ("Left-click = pick up / place item  •  Right-click item = equip/unequip  •  "
               "Right-click orb = ready it, then left-click items to apply  •  "
               "Alt = ranges/tiers  •  Esc = cancel/back")
        s.blit(self.f_small.render(txt, True, FAINT), (36, self.H - 32))

    def _draw_item_cursor(self, s, mouse_pos):
        item = self.cursor_item.obj
        w, h = self.cursor_item.w * 44, self.cursor_item.h * 44
        rect = pygame.Rect(0, 0, w, h)
        rect.center = mouse_pos
        ghost = pygame.Surface((w, h), pygame.SRCALPHA)
        ghost.fill((22, 22, 28, 220))
        color = RARITY_COLORS.get(item.rarity.rarity, TEXT)
        pygame.draw.rect(ghost, color, ghost.get_rect(), width=2, border_radius=6)
        label = self.f_tiny.render(item.itemClass, True, color)
        ghost.blit(label, label.get_rect(center=(w // 2, h // 2)))
        s.blit(ghost, rect)

    def _draw_orb_cursor(self, s, mouse_pos):
        cur = self.cursor_currency.obj
        cx, cy = mouse_pos[0] + 16, mouse_pos[1] + 16
        pygame.draw.circle(s, orb_color(cur.name), (cx, cy), 15)
        pygame.draw.circle(s, (240, 236, 222), (cx - 5, cy - 5), 4)
        abbr = self.f_tiny.render(orb_abbrev(cur.name), True, (20, 18, 14))
        s.blit(abbr, abbr.get_rect(center=(cx, cy + 1)))

    # ---- tooltip ---------------------------------------------------------
    def _wrap(self, text, color, max_w, font):
        out, words, cur = [], str(text).split(), ""
        for w in words:
            t = (cur + " " + w).strip()
            if font.size(t)[0] <= max_w:
                cur = t
            else:
                out.append((cur, color, font))
                cur = w
        out.append((cur, color, font))
        return out

    def _tooltip_lines(self, item, show_ranges, max_w):
        lines = []

        def push(text, color, font):
            lines.extend(self._wrap(text, color, max_w, font))

        def sep():
            lines.append(("sep", None, None))

        push(item.name or "Item", RARITY_COLORS.get(item.rarity.rarity, TEXT), self.f_small)
        sub = f"{item.itemClass}  ·  {item.rarity.rarity.name}"
        if getattr(item, "quality", 0):
            sub += f"  ·  Quality +{item.quality}%"
        push(sub, DIM, self.f_tiny)
        if item.itemLevel is not None:
            push(f"Item Level: {item.itemLevel}", DIM, self.f_tiny)
        req = self._requirement_text(item)
        if req:
            push(req, DIM, self.f_tiny)
        for line in self._property_lines(item):
            push(line, FAINT, self.f_tiny)

        def add_block(mods, color, kind):
            if not mods:
                return
            sep()
            for mod in mods:
                for ln in mod.lines:
                    push(ln, color, self.f_small)
                tag = kind
                if kind != "Implicit" and mod.name:
                    tag += f": {mod.name}"
                if show_ranges:
                    tier, total = mod_tier(mod.id, item.tags)
                    tag += f"  ·  Tier {tier}/{total}"
                push(tag, FAINT, self.f_tiny)
                if show_ranges:
                    ranges = []
                    for st in mod.stats:
                        if "dummy" in st["id"] or "display_nothing" in st["id"]:
                            continue
                        rng = (f"{st['min']}–{st['max']}" if st["min"] != st["max"]
                               else f"{st['min']}")
                        ranges.append(f"{prettify(st['id'])} [{rng}]")
                    if ranges:
                        push("    " + ",  ".join(ranges), FAINT, self.f_tiny)
                lines.append(("gap", None, None))

        if not item.identified:
            add_block(item.implicits, IMPLICIT_COLOR, "Implicit")
            sep()
            push("Unidentified", (235, 95, 95), self.f_small)
            push("Right-click a Scroll of Wisdom, then left-click this item.",
                 FAINT, self.f_tiny)
            return lines

        add_block(item.implicits, IMPLICIT_COLOR, "Implicit")
        add_block(item.prefixes, EXPLICIT_COLOR, "Prefix")
        add_block(item.suffixes, EXPLICIT_COLOR, "Suffix")
        if not item.implicits and not item.explicits:
            sep()
            push("(no modifiers)", SLOT_EMPTY, self.f_small)
        if not show_ranges:
            push("hold Alt for ranges, tiers & affixes", FAINT, self.f_tiny)
        return lines

    def _currency_tooltip_lines(self, cur):
        lines = self._wrap(cur.name, ACCENT, 320, self.f_small)
        lines.append((f"Stack: {cur.count} / {cur.max_stack}", DIM, self.f_tiny))
        lines.append(("sep", None, None))
        lines += self._wrap(cur.description, TEXT, 320, self.f_small)
        lines.append(("Drag onto an item to use it.", FAINT, self.f_tiny))
        return lines

    @staticmethod
    def _property_lines(item):
        """Readable, quality-adjusted base properties for the tooltip."""
        props = item.properties or {}
        q = 1 + item.quality / 100
        note = f"  (incl. {item.quality}% quality)" if item.quality else ""
        out = []

        def mid(v):
            return (v.get("min", 0) + v.get("max", 0)) / 2 if isinstance(v, dict) else v

        for key, label in (("armour", "Armour"), ("evasion", "Evasion"),
                           ("energy_shield", "Energy Shield")):
            if key in props:
                out.append(f"{label}: {round(mid(props[key]) * q)}{note}")
        if "physical_damage_min" in props and "physical_damage_max" in props:
            lo = props["physical_damage_min"] * q
            hi = props["physical_damage_max"] * q
            out.append(f"Physical Damage: {round(lo)}–{round(hi)}{note}")
        if props.get("attack_time"):
            out.append(f"Attacks per Second: {1000 / props['attack_time']:.2f}")
        if props.get("critical_strike_chance"):
            out.append(f"Critical Strike Chance: {props['critical_strike_chance'] / 100:.1f}%")
        if props.get("block"):
            out.append(f"Chance to Block: {props['block']}%")
        if props.get("movement_speed"):
            out.append(f"Movement Speed: {props['movement_speed']}%")
        return out

    @staticmethod
    def _requirement_text(item):
        req = item.requirements
        if isinstance(req, dict) and req:
            order = [("level", "Level"), ("strength", "Str"),
                     ("dexterity", "Dex"), ("intelligence", "Int")]
            parts = []
            for key, lbl in order:
                v = req.get(key)
                if v:
                    parts.append(f"Level {v}" if key == "level" else f"{v} {lbl}")
            if parts:
                return "Requires " + ", ".join(parts)
        if item.dropLevel:
            return f"Requires Level {item.dropLevel}"
        return None

    def _draw_tooltip(self, s, mouse_pos):
        entry = self._entry_at(mouse_pos)
        if entry is not None:
            if entry.currency:
                self._draw_tip_box(s, self._currency_tooltip_lines(entry.obj), mouse_pos, ACCENT)
                return
            item = entry.obj
        else:
            slot = self._slot_at(mouse_pos)
            item = getattr(self.character.equipments, slot) if slot else None
        if item is None:
            return
        show_ranges = bool(pygame.key.get_mods() & pygame.KMOD_ALT)
        lines = self._tooltip_lines(item, show_ranges, 430)
        self._draw_tip_box(s, lines, mouse_pos, RARITY_COLORS.get(item.rarity.rarity, TEXT))

    def _draw_tip_box(self, s, lines, mouse_pos, border):
        pad = 12
        width, height = 0, pad * 2
        for text, _c, font in lines:
            if text == "sep":
                height += 10
                continue
            if text == "gap":
                height += 6
                continue
            width = max(width, font.size(text)[0])
            height += font.get_height() + 1
        width += pad * 2
        mx, my = mouse_pos
        x = max(8, min(mx + 18, self.W - width - 8))
        y = max(8, min(my + 18, self.H - height - 8))
        box = pygame.Rect(x, y, width, height)
        shadow = box.move(4, 5)
        sh = pygame.Surface(shadow.size, pygame.SRCALPHA)
        sh.fill((0, 0, 0, 110))
        s.blit(sh, shadow)
        pygame.draw.rect(s, (12, 12, 16), box, border_radius=8)
        pygame.draw.rect(s, border, box, width=2, border_radius=8)
        s.set_clip(box)
        ty = y + pad
        for text, color, font in lines:
            if text == "sep":
                pygame.draw.line(s, PANEL_LIGHT, (x + pad, ty + 5), (x + width - pad, ty + 5))
                ty += 10
                continue
            if text == "gap":
                ty += 6
                continue
            s.blit(font.render(text, True, color), (x + pad, ty))
            ty += font.get_height() + 1
        s.set_clip(None)


# ------------------------------------------------------------------ main ----
def run(screen, item_count=20, selftest=False):
    pygame.display.set_caption("poe_engine — Inventory Test")
    clock = pygame.time.Clock()
    ui = InventoryTest(screen, item_count)

    running = True
    frames = 0
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE and not selftest:
                screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
                ui.screen = screen
                ui.on_resize(event.w, event.h)
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                if not ui.handle_escape():
                    running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                ui.on_left_down(event.pos)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                ui.on_right_down(event.pos)
            elif event.type == pygame.MOUSEWHEEL:
                ui.handle_scroll(event.y, pygame.mouse.get_pos())

        ui.draw(pygame.mouse.get_pos())
        pygame.display.flip()
        clock.tick(60)

        if selftest:
            frames += 1
            if frames == 2:  # left-click an item to pick it up, place it elsewhere
                items = [e for e in ui.entries if not e.currency]
                if items:
                    ui.on_left_down(ui._entry_rect(items[0]).center)
                    ox, oy = ui.inv_origin
                    ui.on_left_down((ox + (ui.inv_cols - 1) * ui.inv_cell + 4,
                                     oy + (ui.inv_rows - 1) * ui.inv_cell + 4))
            if frames == 3:  # right-click an identified item to equip
                for e in ui.entries:
                    if not e.currency and e.obj.identified and ui._equippable(e.obj):
                        ui.on_right_down(ui._entry_rect(e).center)
                        break
            if frames == 4:  # ready a Scroll of Wisdom, left-click an item to use it
                cur = next((e for e in ui.entries if e.currency), None)
                itm = next((e for e in ui.entries if not e.currency), None)
                if cur and itm:
                    ui.on_right_down(ui._entry_rect(cur).center)
                    ui.on_left_down(ui._entry_rect(itm).center)
                    ui.on_right_down((0, 0))  # cancel orb on cursor
            if frames == 5:
                ui.on_left_down(ui.buttons["levelup"].center)
            if frames == 6:
                ui.on_left_down(ui.buttons["class"].center)
            if frames == 7:
                ui.on_left_down(ui.buttons["debug"].center)
                if ui.dbg_rows:
                    ui.on_left_down(ui.dbg_rows[3][1].center)
            if frames == 8:
                ui.handle_escape()
                ui.on_resize(1280, 760)
            if frames == 9:
                ui.on_left_down(ui.buttons["reload"].center)
            if frames >= 11:
                running = False


def main():
    parser = argparse.ArgumentParser(description="poe_engine inventory test bench")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--items", type=int, default=20)
    parser.add_argument("--fullscreen", action="store_true")
    parser.add_argument("--selftest", action="store_true",
                        help="run headless for a few frames (smoke test)")
    args = parser.parse_args()

    if args.selftest:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    if args.seed is not None:
        rng_seed(args.seed)

    pygame.init()
    if args.selftest:
        screen = pygame.display.set_mode((1500, 900))
    elif args.fullscreen:
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    else:
        info = pygame.display.Info()
        size = (min(1600, info.current_w - 80), min(950, info.current_h - 120))
        screen = pygame.display.set_mode(size, pygame.RESIZABLE)

    run(screen, item_count=args.items, selftest=args.selftest)
    pygame.quit()
    if args.selftest:
        print("inventory_test selftest OK")


if __name__ == "__main__":
    main()
