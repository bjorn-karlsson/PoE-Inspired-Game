#!/usr/bin/env python3
"""Inventory Test -- a graphical inventory / character bench for poe_engine.

A no-combat sandbox to inspect items and the stat system:

* Equipment paper-doll + grid inventory (items show their *type*; the full name
  is in the tooltip).
* Left-click a bag item to equip it; left-click equipped gear to unequip.
* Hover an item for a PoE-style tooltip (item level, requirements, mods).
  Hold **Alt** while hovering to also see each mod's value range and tier.
* Stats panel with selectable tabs (Defense / Offense / Attributes / All) and
  mouse-wheel scrolling.
* **New Loot** button rerolls everything with a fresh random seed.
* **Debug** mode: pick a stat and see exactly how it is built -- every source
  item's flat / increased / more contribution and the final calculation.

Run it::

    python inventory_test.py            # fullscreen, random loot
    python inventory_test.py --seed 1   # reproducible loot
    python inventory_test.py --windowed
"""

import argparse
import os
import random as _random

import pygame

from poe_engine import Character
from poe_engine.analysis import mod_tier, resolve_stat, stat_breakdown
from poe_engine.items import SLOTS, Item
from poe_engine.rarity import Rarities
from poe_engine.rng import seed as rng_seed


# ---------------------------------------------------------------- colours ----
BG = (17, 17, 21)
PANEL = (28, 28, 36)
PANEL_LIGHT = (46, 46, 58)
SLOT_BG = (38, 38, 50)
SLOT_EMPTY_TEXT = (95, 95, 112)
TEXT = (222, 222, 228)
DIM = (150, 150, 162)
FAINT = (110, 110, 124)
ACCENT = (205, 172, 92)
BTN = (52, 52, 66)
BTN_HOT = (72, 72, 90)
BTN_ON = (70, 100, 70)

RARITY_COLORS = {
    Rarities.NORMAL: (200, 200, 205),
    Rarities.MAGIC: (120, 150, 255),
    Rarities.RARE: (240, 220, 90),
    Rarities.UNIQUE: (210, 120, 45),
}
IMPLICIT_COLOR = (120, 200, 255)
EXPLICIT_COLOR = (160, 170, 255)
POS_COLOR = (130, 220, 140)
NEG_COLOR = (230, 120, 120)

# Equipment paper-doll: slot -> (column, row) in a 3x4 mini grid.
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

# Stat registry: (path, label, category, format)
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


# ----------------------------------------------------------- demo content ----
def make_demo_character(item_count=22, drop_level=74):
    hero = Character("Exile", level=20)
    classes = ["Helmet", "Body Armour", "Gloves", "Boots", "Amulet", "Ring",
               "Ring", "Belt", "One Hand Sword", "Two Hand Axe", "Shield",
               "Bow", "Wand", "Sceptre", "Staff"]
    for i in range(item_count):
        item = Item.generate(drop_level=drop_level, item_class=classes[i % len(classes)],
                             rarity_bonus=45)
        hero.inventory.addItem(item)
    return hero


# ------------------------------------------------------------- the screen ----
class InventoryTest:
    def __init__(self, screen, item_count=22):
        self.screen = screen
        self.item_count = item_count
        self.W, self.H = screen.get_size()

        self.f_tiny = pygame.font.Font(None, 19)
        self.f_small = pygame.font.Font(None, 22)
        self.f = pygame.font.Font(None, 26)
        self.f_big = pygame.font.Font(None, 36)

        self.character = make_demo_character(item_count)

        # UI state
        self.tab = "def"
        self.scroll = 0
        self.debug_mode = False
        self.debug_stat = None
        self.dbg_scroll = 0
        self._content_h = 0       # measured each frame for scroll clamping
        self._bd_cache = None
        self._bd_sig = None

        self.slot_rects = {}
        self.inv_rects = []
        self.buttons = {}
        self.tab_rects = []
        self.dbg_rows = []        # clickable (path, rect) in debug list

        self._build_layout()
        self._repack()

    # -- geometry ----------------------------------------------------------
    def _build_layout(self):
        margin = 40
        self.doll_origin = (margin, 150)
        self.doll_cell = max(78, min(110, (self.H - 260) // 4 - 10))
        self.doll_gap = 10

        doll_w = 3 * (self.doll_cell + self.doll_gap)
        self.stats_x = margin + doll_w + 40
        self.stats_w = 380
        self.panel_top = 150
        self.panel_bottom = self.H - 60
        self.panel_h = self.panel_bottom - self.panel_top

        self.inv_origin = (self.stats_x + self.stats_w + 40, self.panel_top)
        self.inv_cell = 52
        avail_w = self.W - margin - self.inv_origin[0]
        self.inv_cols = max(6, avail_w // self.inv_cell)
        self.inv_rows = max(6, self.panel_h // self.inv_cell)

        ox, oy = self.doll_origin
        for slot, (col, row) in DOLL_LAYOUT.items():
            x = ox + col * (self.doll_cell + self.doll_gap)
            y = oy + row * (self.doll_cell + self.doll_gap)
            self.slot_rects[slot] = pygame.Rect(x, y, self.doll_cell, self.doll_cell)

        # Toolbar buttons (top right area).
        self.buttons = {}
        bx = self.inv_origin[0]
        reload_w = self.f_small.size("New Loot (reseed)")[0] + 28
        self.buttons["reload"] = pygame.Rect(bx, 96, reload_w, 34)
        debug_w = self.f_small.size("Debug: OFF")[0] + 28
        self.buttons["debug"] = pygame.Rect(bx + reload_w + 12, 96, debug_w, 34)

        # Stats tabs.
        self.tab_rects = []
        tx = self.stats_x
        for label, key in TABS:
            w = self.f_small.size(label)[0] + 22
            self.tab_rects.append((key, label, pygame.Rect(tx, 110, w, 30)))
            tx += w + 8

    def _repack(self):
        occ = [[False] * self.inv_cols for _ in range(self.inv_rows)]
        self.inv_rects = []
        ox, oy = self.inv_origin
        for item in self.character.inventory.items:
            w = min(item.inventoryWidth, self.inv_cols)
            h = min(item.inventoryHeight, self.inv_rows)
            spot = self._find_spot(occ, w, h)
            if spot is None:
                continue
            gx, gy = spot
            for dy in range(h):
                for dx in range(w):
                    occ[gy + dy][gx + dx] = True
            rect = pygame.Rect(ox + gx * self.inv_cell + 2, oy + gy * self.inv_cell + 2,
                               w * self.inv_cell - 4, h * self.inv_cell - 4)
            self.inv_rects.append((item, rect))

    def _find_spot(self, occ, w, h):
        for y in range(self.inv_rows - h + 1):
            for x in range(self.inv_cols - w + 1):
                if all(not occ[y + dy][x + dx]
                       for dy in range(h) for dx in range(w)):
                    return x, y
        return None

    # -- interaction -------------------------------------------------------
    def item_at(self, pos):
        for item, rect in self.inv_rects:
            if rect.collidepoint(pos):
                return ("inv", item)
        for slot, rect in self.slot_rects.items():
            if rect.collidepoint(pos):
                return ("slot", slot)
        return None

    def handle_click(self, pos):
        if self.buttons["reload"].collidepoint(pos):
            return self.reload_loot()
        if self.buttons["debug"].collidepoint(pos):
            self.debug_mode = not self.debug_mode
            self.debug_stat = None
            self.scroll = self.dbg_scroll = 0
            return
        for key, _, rect in self.tab_rects:
            if rect.collidepoint(pos):
                self.tab, self.scroll = key, 0
                return
        if self.debug_mode:
            for path, rect in self.dbg_rows:
                if rect.collidepoint(pos):
                    self.debug_stat = None if self.debug_stat == path else path
                    self.dbg_scroll = 0
                    return
        target = self.item_at(pos)
        if target is None:
            return
        kind, value = target
        if kind == "inv":
            self._equip_from_bag(value)
        else:
            self._unequip_to_bag(value)

    def handle_scroll(self, dy, pos):
        if pos[0] < self.inv_origin[0]:  # over the stats column
            step = 36
            if self.debug_mode and self.debug_stat:
                self.dbg_scroll = max(0, self.dbg_scroll - dy * step)
            else:
                self.scroll = max(0, self.scroll - dy * step)

    def _equip_from_bag(self, item):
        inv = self.character.inventory
        if item not in inv.items:
            return
        inv.items.remove(item)
        replaced = self.character.equip(item)
        if replaced is not None and not inv.addItem(replaced):
            self.character.equip(replaced)
            if item in inv.items:
                inv.items.remove(item)
            inv.addItem(item)
        self._repack()

    def _unequip_to_bag(self, slot):
        item = getattr(self.character.equipments, slot)
        if item is None:
            return
        inv = self.character.inventory
        if inv.currentSize + item.inventorySize > inv.size:
            return
        self.character.unequip(slot)
        inv.addItem(item)
        self._repack()

    def reload_loot(self):
        rng_seed(_random.randrange(1 << 30))
        self.character = make_demo_character(self.item_count)
        self.debug_stat = None
        self.scroll = self.dbg_scroll = 0
        self._repack()

    # -- drawing -----------------------------------------------------------
    def draw(self, mouse_pos):
        s = self.screen
        s.fill(BG)
        title = self.f_big.render(
            f"{self.character.name}  —  Level {self.character.level}", True, ACCENT)
        s.blit(title, (40, 40))
        s.blit(self.f_small.render("INVENTORY TEST", True, FAINT), (40, 82))

        self._draw_toolbar(mouse_pos)
        self._draw_doll(s)
        if self.debug_mode:
            self._draw_debug(s)
        else:
            self._draw_stats(s)
        self._draw_inventory(s)
        self._draw_help(s)
        self._draw_tooltip(s, mouse_pos)

    def _button(self, rect, label, hot, on=False):
        color = BTN_ON if on else (BTN_HOT if hot else BTN)
        pygame.draw.rect(self.screen, color, rect, border_radius=6)
        pygame.draw.rect(self.screen, PANEL_LIGHT, rect, width=1, border_radius=6)
        surf = self.f_small.render(label, True, TEXT)
        self.screen.blit(surf, surf.get_rect(center=rect.center))

    def _draw_toolbar(self, mouse_pos):
        r = self.buttons["reload"]
        self._button(r, "New Loot (reseed)", r.collidepoint(mouse_pos))
        d = self.buttons["debug"]
        self._button(d, f"Debug: {'ON' if self.debug_mode else 'OFF'}",
                     d.collidepoint(mouse_pos), on=self.debug_mode)

    def _draw_doll(self, s):
        s.blit(self.f_small.render("EQUIPMENT", True, DIM),
               (self.doll_origin[0], self.doll_origin[1] - 26))
        for slot, rect in self.slot_rects.items():
            pygame.draw.rect(s, SLOT_BG, rect, border_radius=6)
            pygame.draw.rect(s, PANEL_LIGHT, rect, width=2, border_radius=6)
            item = getattr(self.character.equipments, slot)
            if item is None:
                lbl = self.f_small.render(SLOT_LABELS[slot], True, SLOT_EMPTY_TEXT)
                s.blit(lbl, lbl.get_rect(center=rect.center))
            else:
                self._draw_item_box(s, item, rect)

    def _draw_inventory(self, s):
        ox, oy = self.inv_origin
        s.blit(self.f_small.render("INVENTORY", True, DIM), (ox, oy - 26))
        grid = pygame.Rect(ox, oy, self.inv_cols * self.inv_cell,
                           self.inv_rows * self.inv_cell)
        pygame.draw.rect(s, PANEL, grid, border_radius=6)
        for c in range(self.inv_cols + 1):
            x = ox + c * self.inv_cell
            pygame.draw.line(s, PANEL_LIGHT, (x, oy), (x, grid.bottom))
        for r in range(self.inv_rows + 1):
            y = oy + r * self.inv_cell
            pygame.draw.line(s, PANEL_LIGHT, (ox, y), (grid.right, y))
        for item, rect in self.inv_rects:
            self._draw_item_box(s, item, rect)

    def _draw_item_box(self, s, item, rect):
        color = RARITY_COLORS.get(item.rarity.rarity, TEXT)
        inner = rect.inflate(-2, -2)
        pygame.draw.rect(s, (24, 24, 30), inner, border_radius=5)
        pygame.draw.rect(s, color, rect, width=2, border_radius=5)
        # Show the item *type* on the box (name lives in the tooltip).
        self._blit_wrapped_centered(s, item.itemClass, color, rect)

    def _blit_wrapped_centered(self, s, text, color, rect):
        words = str(text).split()
        lines, current = [], ""
        for word in words:
            trial = (current + " " + word).strip()
            if self.f_tiny.size(trial)[0] <= rect.width - 8:
                current = trial
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        y = rect.centery - len(lines) * 8
        for line in lines[: max(1, rect.height // 16)]:
            surf = self.f_tiny.render(line, True, color)
            s.blit(surf, surf.get_rect(centerx=rect.centerx, y=y))
            y += 16

    def _stats_panel_rect(self):
        return pygame.Rect(self.stats_x, self.panel_top, self.stats_w, self.panel_h)

    def _draw_tabs(self, s, mouse_pos):
        for key, label, rect in self.tab_rects:
            self._button(rect, label, rect.collidepoint(mouse_pos), on=(self.tab == key))

    def _draw_stats(self, s):
        s.blit(self.f_small.render("CHARACTER", True, DIM), (self.stats_x, self.panel_top - 26))
        self._draw_tabs(s, pygame.mouse.get_pos())
        panel = self._stats_panel_rect()
        pygame.draw.rect(s, PANEL, panel, border_radius=6)

        entries = [e for e in STAT_REGISTRY if self.tab in (e[2], "all")]
        s.set_clip(panel)
        x = panel.x + 14
        y = panel.y + 12 - self.scroll
        for path, label, _cat, fmt in entries:
            stat = resolve_stat(self.character.stats, path)
            if panel.y - 24 <= y <= panel.bottom:
                s.blit(self.f_small.render(label, True, DIM), (x, y))
                vsurf = self.f_small.render(fmt_stat(stat, fmt), True, TEXT)
                s.blit(vsurf, vsurf.get_rect(right=panel.right - 14, y=y))
            y += 26
        s.set_clip(None)
        self._content_h = len(entries) * 26 + 24
        self._clamp_scroll("scroll", panel.height)

    def _clamp_scroll(self, attr, view_h):
        max_scroll = max(0, self._content_h - view_h)
        setattr(self, attr, min(getattr(self, attr), max_scroll))

    # -- debug breakdown ---------------------------------------------------
    def _draw_debug(self, s):
        s.blit(self.f_small.render("DEBUG — STAT BREAKDOWN", True, ACCENT),
               (self.stats_x, self.panel_top - 26))
        panel = self._stats_panel_rect()
        pygame.draw.rect(s, PANEL, panel, border_radius=6)
        if self.debug_stat is None:
            self._draw_debug_list(s, panel)
        else:
            self._draw_debug_detail(s, panel)

    def _draw_debug_list(self, s, panel):
        s.set_clip(panel)
        self.dbg_rows = []
        x, y = panel.x + 12, panel.y + 12 - self.scroll
        hint = self.f_tiny.render("click a stat to inspect", True, FAINT)
        s.blit(hint, (x, y))
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
        self._content_h = len(STAT_REGISTRY) * 26 + 48
        self._clamp_scroll("scroll", panel.height)

    def _breakdown(self):
        eq = self.character.equipments
        sig = (self.debug_stat, tuple(id(getattr(eq, slot)) for slot in SLOTS))
        if sig != self._bd_sig:
            self._bd_cache = stat_breakdown(self.character, self.debug_stat)
            self._bd_sig = sig
        return self._bd_cache

    def _draw_debug_detail(self, s, panel):
        bd = self._breakdown()
        label = next((e[1] for e in STAT_REGISTRY if e[0] == self.debug_stat),
                     self.debug_stat)
        s.set_clip(panel)
        x, y = panel.x + 12, panel.y + 10 - self.dbg_scroll

        def line(text, color, indent=0, font=None):
            nonlocal y
            font = font or self.f_small
            if panel.y - 20 <= y <= panel.bottom:
                s.blit(font.render(text, True, color), (x + indent, y))
            y += font.get_height() - 2

        line("‹ back to list", FAINT, font=self.f_tiny)
        y += 6
        line(label, ACCENT, font=self.f)
        y += 4
        for src in bd["sources"]:
            line(src["name"], TEXT)
            comp = src["components"]
            for key in ("positive", "negative", "increased", "reduced", "more", "less"):
                if key not in comp:
                    continue
                val = comp[key]
                if key in ("positive",):
                    text, col = f"+{val:g} flat", POS_COLOR
                elif key == "negative":
                    text, col = f"-{val:g} flat", NEG_COLOR
                elif key == "increased":
                    text, col = f"+{val:g}% increased", POS_COLOR if val >= 0 else NEG_COLOR
                elif key == "reduced":
                    text, col = f"-{val:g}% reduced", NEG_COLOR
                elif key == "more":
                    text, col = f"x{val:.3g} more", POS_COLOR
                else:
                    text, col = f"x{val:.3g} less", NEG_COLOR
                line(text, col, indent=22, font=self.f_tiny)
            y += 4
        if not bd["sources"]:
            line("(no contributions)", FAINT, indent=12)

        y += 6
        pygame.draw.line(s, PANEL_LIGHT, (x, y), (panel.right - 14, y))
        y += 10
        t = bd["totals"]
        line("Combined:", DIM)
        line(f"flat = {t['positive'] - t['negative']:g}", TEXT, indent=12, font=self.f_tiny)
        line(f"increased = {t['increased'] - t['reduced']:g}%", TEXT, indent=12, font=self.f_tiny)
        line(f"more/less = x{t['more'] / t['less']:.3g}", TEXT, indent=12, font=self.f_tiny)
        y += 6
        line("(flat) x (1 + inc%) x more", FAINT, font=self.f_tiny)
        flat = t["positive"] - t["negative"]
        incmul = 1 + (t["increased"] - t["reduced"]) / 100
        line(f"= {flat:g} x {incmul:.3g} x {t['more'] / t['less']:.3g}", TEXT,
             indent=12, font=self.f_tiny)
        line(f"= {bd['computed_total']:g}", POS_COLOR, indent=12)
        if bd["clamp"]:
            line(f"({bd['clamp']})", NEG_COLOR, indent=12, font=self.f_tiny)
        y += 4
        match = abs(bd["computed_total"] - bd["actual_total"]) < 0.05
        line(f"engine total = {bd['actual_total']:g}  "
             f"{'[match]' if match else '[MISMATCH]'}",
             POS_COLOR if match else NEG_COLOR, font=self.f_tiny)
        s.set_clip(None)
        self._content_h = (y + self.dbg_scroll) - panel.y + 20
        self._clamp_scroll("dbg_scroll", panel.height)

    def _draw_help(self, s):
        help_text = ("Left-click bag item = equip  •  left-click equipped = unequip  •  "
                     "hover = details  •  hold Alt = ranges & tiers  •  scroll stats  •  Esc = quit")
        s.blit(self.f_small.render(help_text, True, DIM), (40, self.H - 34))

    # -- tooltip -----------------------------------------------------------
    def _wrap(self, text, color, max_w, font):
        out, words, current = [], str(text).split(), ""
        for word in words:
            trial = (current + " " + word).strip()
            if font.size(trial)[0] <= max_w:
                current = trial
            else:
                out.append((current, color, font))
                current = word
        out.append((current, color, font))
        return out

    def _tooltip_lines(self, item, show_ranges, max_w):
        lines = []
        lines += self._wrap(item.name or "Item", RARITY_COLORS.get(item.rarity.rarity, TEXT),
                            max_w, self.f_small)
        lines.append((f"{item.itemClass}  ·  {item.rarity.rarity.name}", DIM, self.f_tiny))
        if item.itemLevel is not None:
            lines.append((f"Item Level: {item.itemLevel}", DIM, self.f_tiny))
        req = self._requirement_text(item)
        if req:
            lines.append((req, DIM, self.f_tiny))
        for key, val in (item.properties or {}).items():
            lines.append((f"{prettify(str(key)).title()}: {self._fmt_prop(val)}",
                          FAINT, self.f_tiny))

        def add_mods(mods, color):
            if not mods:
                return
            lines.append(("sep", None, None))
            for mod in mods:
                for ln in mod.lines:
                    lines.extend(self._wrap(ln, color, max_w, self.f_small))
                if show_ranges:
                    tier, total = mod_tier(mod.id)
                    ranges = []
                    for st in mod.stats:
                        rng = (f"{st['min']}–{st['max']}" if st["min"] != st["max"]
                               else f"{st['min']}")
                        ranges.append(f"{prettify(st['id'])} [{rng}]")
                    detail = f"Tier {tier}/{total}  ·  " + ",  ".join(ranges)
                    lines.extend(self._wrap(detail, FAINT, max_w, self.f_tiny))

        add_mods(item.implicits, IMPLICIT_COLOR)
        add_mods(item.explicits, EXPLICIT_COLOR)
        if not item.implicits and not item.explicits:
            lines.append(("sep", None, None))
            lines.append(("(no modifiers)", SLOT_EMPTY_TEXT, self.f_small))
        if not show_ranges:
            lines.append(("hold Alt for ranges & tiers", FAINT, self.f_tiny))
        return lines

    @staticmethod
    def _fmt_prop(val):
        if isinstance(val, dict):
            lo, hi = val.get("min"), val.get("max")
            if lo is not None and hi is not None:
                return f"{lo}–{hi}" if lo != hi else f"{lo}"
            return ", ".join(f"{k} {v}" for k, v in val.items())
        return str(val)

    @staticmethod
    def _requirement_text(item):
        req = item.requirements
        if isinstance(req, dict) and req:
            order = [("level", "Level"), ("strength", "Str"),
                     ("dexterity", "Dex"), ("intelligence", "Int")]
            parts = []
            for key, label in order:
                v = req.get(key)
                if v:
                    parts.append(f"Level {v}" if key == "level" else f"{v} {label}")
            if parts:
                return "Requires " + ", ".join(parts)
        if item.dropLevel:
            return f"Requires Level {item.dropLevel}"
        return None

    def _draw_tooltip(self, s, mouse_pos):
        target = self.item_at(mouse_pos)
        if target is None:
            return
        kind, value = target
        item = value if kind == "inv" else getattr(self.character.equipments, value)
        if item is None:
            return

        show_ranges = bool(pygame.key.get_mods() & pygame.KMOD_ALT)
        max_w = 460
        lines = self._tooltip_lines(item, show_ranges, max_w)

        pad = 10
        width = 0
        height = pad * 2
        for text, _color, font in lines:
            if text == "sep":
                height += 8
                continue
            width = max(width, font.size(text)[0])
            height += font.get_height() - 2
        width = min(max_w, width) + pad * 2

        mx, my = mouse_pos
        x = min(mx + 18, self.W - width - 8)
        y = min(my + 18, self.H - height - 8)
        y = max(8, y)
        box = pygame.Rect(x, y, width, height)
        pygame.draw.rect(s, (10, 10, 14), box, border_radius=8)
        pygame.draw.rect(s, RARITY_COLORS.get(item.rarity.rarity, TEXT), box,
                         width=2, border_radius=8)

        ty = y + pad
        for text, color, font in lines:
            if text == "sep":
                pygame.draw.line(s, PANEL_LIGHT, (x + pad, ty + 4),
                                 (x + width - pad, ty + 4))
                ty += 8
                continue
            s.blit(font.render(text, True, color), (x + pad, ty))
            ty += font.get_height() - 2


# ------------------------------------------------------------------ main ----
def run(screen, item_count=22, selftest=False):
    pygame.display.set_caption("poe_engine — Inventory Test")
    clock = pygame.time.Clock()
    ui = InventoryTest(screen, item_count)

    running = True
    frames = 0
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                ui.handle_click(event.pos)
            elif event.type == pygame.MOUSEWHEEL:
                ui.handle_scroll(event.y, pygame.mouse.get_pos())

        ui.draw(pygame.mouse.get_pos())
        pygame.display.flip()
        clock.tick(60)

        if selftest:
            frames += 1
            if frames == 2 and ui.inv_rects:
                ui.handle_click(ui.inv_rects[0][1].center)
            if frames == 3:
                ui.handle_click(ui.buttons["debug"].center)
            if frames == 4 and ui.dbg_rows:
                ui.handle_click(ui.dbg_rows[4][1].center)  # inspect a stat
            if frames == 5:
                ui.handle_click(ui.buttons["reload"].center)
            if frames >= 7:
                running = False


def main():
    parser = argparse.ArgumentParser(description="poe_engine inventory test bench")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--items", type=int, default=22)
    parser.add_argument("--windowed", action="store_true")
    parser.add_argument("--selftest", action="store_true",
                        help="run headless for a few frames (smoke test)")
    args = parser.parse_args()

    if args.selftest:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    if args.seed is not None:
        rng_seed(args.seed)

    pygame.init()
    if args.selftest or args.windowed:
        screen = pygame.display.set_mode((1366, 768))
    else:
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)

    run(screen, item_count=args.items, selftest=args.selftest)
    pygame.quit()
    if args.selftest:
        print("inventory_test selftest OK")


if __name__ == "__main__":
    main()
