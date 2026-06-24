#!/usr/bin/env python3
"""A graphical inventory & character screen for poe_engine (pygame).

No combat -- this is the "stash & paper-doll" screen:

* See your equipped items on a character paper-doll.
* See a grid inventory of loot (items take up space by their size).
* Left-click an inventory item to equip it; left-click an equipped item to
  put it back in your bag.
* Hover any item to see a Path-of-Exile-style tooltip with its mods.
* The stats panel updates live as you change gear.

Run it::

    python gui.py            # random loot
    python gui.py --seed 1   # reproducible loot
"""

import argparse
import os
import sys

import pygame

from poe_engine import Character, seed
from poe_engine.items import Item, SLOTS
from poe_engine.rarity import Rarities


# ---------------------------------------------------------------- layout ----
WIDTH, HEIGHT = 1280, 760
FPS = 60

BG = (18, 18, 22)
PANEL = (30, 30, 38)
PANEL_LIGHT = (44, 44, 56)
SLOT_BG = (40, 40, 52)
SLOT_EMPTY_TEXT = (90, 90, 105)
TEXT = (220, 220, 225)
DIM = (150, 150, 160)
ACCENT = (200, 170, 90)

RARITY_COLORS = {
    Rarities.NORMAL: (200, 200, 205),
    Rarities.MAGIC: (120, 150, 255),
    Rarities.RARE: (240, 220, 90),
    Rarities.UNIQUE: (210, 120, 45),
}
IMPLICIT_COLOR = (120, 200, 255)
EXPLICIT_COLOR = (150, 160, 255)

# Equipment paper-doll: slot -> (column, row) in a 3x4 mini grid.
DOLL_LAYOUT = {
    "helmet": (1, 0),
    "amulet": (2, 0),
    "weapon": (0, 1),
    "bodyArmour": (1, 1),
    "offhand": (2, 1),
    "gloves": (0, 2),
    "belt": (1, 2),
    "ring1": (2, 2),
    "boots": (0, 3),
    "ring2": (2, 3),
}
SLOT_LABELS = {
    "weapon": "Weapon", "offhand": "Off-hand", "helmet": "Helmet",
    "bodyArmour": "Body", "gloves": "Gloves", "boots": "Boots",
    "amulet": "Amulet", "belt": "Belt", "ring1": "Ring", "ring2": "Ring",
}

DOLL_ORIGIN = (40, 90)
DOLL_CELL = 96
DOLL_GAP = 10

INV_ORIGIN = (730, 90)
INV_COLS, INV_ROWS = 10, 9
INV_CELL = 50

STATS_ORIGIN = (380, 90)
STATS_WIDTH = 320


# ----------------------------------------------------------- demo content ----
def make_demo_character(item_count=18, drop_level=72):
    """Build a hero with a bag of random loot to play with."""
    hero = Character("Exile", level=20)
    classes = ["Helmet", "Body Armour", "Gloves", "Boots", "Amulet", "Ring",
               "Ring", "Belt", "One Hand Sword", "Two Hand Axe", "Shield",
               "Bow", "Wand", "Sceptre"]
    for i in range(item_count):
        item_class = classes[i % len(classes)]
        item = Item.generate(drop_level=drop_level, item_class=item_class,
                             rarity_bonus=45)
        hero.inventory.addItem(item)
    return hero


# ------------------------------------------------------------ the screen ----
class InventoryUI:
    def __init__(self, character):
        self.character = character
        self.font = pygame.font.Font(None, 24)
        self.font_small = pygame.font.Font(None, 20)
        self.font_big = pygame.font.Font(None, 32)

        self.slot_rects = {}      # slot name -> pygame.Rect
        self.inv_rects = []       # list of (item, pygame.Rect)
        self._build_slot_rects()
        self._repack()

    # -- geometry ----------------------------------------------------------
    def _build_slot_rects(self):
        ox, oy = DOLL_ORIGIN
        for slot, (col, row) in DOLL_LAYOUT.items():
            x = ox + col * (DOLL_CELL + DOLL_GAP)
            y = oy + row * (DOLL_CELL + DOLL_GAP)
            self.slot_rects[slot] = pygame.Rect(x, y, DOLL_CELL, DOLL_CELL)

    def _repack(self):
        """First-fit pack the inventory items onto the grid."""
        occ = [[False] * INV_COLS for _ in range(INV_ROWS)]
        self.inv_rects = []
        ox, oy = INV_ORIGIN
        for item in self.character.inventory.items:
            w = min(item.inventoryWidth, INV_COLS)
            h = min(item.inventoryHeight, INV_ROWS)
            spot = self._find_spot(occ, w, h)
            if spot is None:
                continue
            gx, gy = spot
            for dy in range(h):
                for dx in range(w):
                    occ[gy + dy][gx + dx] = True
            rect = pygame.Rect(ox + gx * INV_CELL + 2, oy + gy * INV_CELL + 2,
                               w * INV_CELL - 4, h * INV_CELL - 4)
            self.inv_rects.append((item, rect))

    @staticmethod
    def _find_spot(occ, w, h):
        for y in range(INV_ROWS - h + 1):
            for x in range(INV_COLS - w + 1):
                if all(not occ[y + dy][x + dx]
                       for dy in range(h) for dx in range(w)):
                    return x, y
        return None

    # -- interaction -------------------------------------------------------
    def item_at(self, pos):
        """Return ('inv', item) or ('slot', slot_name) under the cursor."""
        for item, rect in self.inv_rects:
            if rect.collidepoint(pos):
                return ("inv", item)
        for slot, rect in self.slot_rects.items():
            if rect.collidepoint(pos):
                return ("slot", slot)
        return None

    def handle_click(self, pos):
        target = self.item_at(pos)
        if target is None:
            return
        kind, value = target
        if kind == "inv":
            self._equip_from_bag(value)
        elif kind == "slot":
            self._unequip_to_bag(value)

    def _equip_from_bag(self, item):
        inv = self.character.inventory
        if item not in inv.items:
            return
        inv.items.remove(item)
        replaced = self.character.equip(item)  # equips + recalibrates
        if replaced is not None and not inv.addItem(replaced):
            # No room for the swapped-out item: undo the swap.
            self.character.equip(replaced)
            inv.items.remove(item)
            inv.addItem(item)
        self._repack()

    def _unequip_to_bag(self, slot):
        item = getattr(self.character.equipments, slot)
        if item is None:
            return
        if self.character.inventory.currentSize + item.inventorySize > \
                self.character.inventory.size:
            return  # bag full
        self.character.unequip(slot)  # unequips + recalibrates
        self.character.inventory.addItem(item)
        self._repack()

    # -- drawing -----------------------------------------------------------
    def draw(self, screen, mouse_pos):
        screen.fill(BG)
        self._draw_title(screen)
        self._draw_doll(screen)
        self._draw_stats(screen)
        self._draw_inventory(screen)
        self._draw_help(screen)
        self._draw_tooltip(screen, mouse_pos)

    def _draw_title(self, screen):
        title = self.font_big.render(
            f"{self.character.name}  —  Level {self.character.level}", True, ACCENT)
        screen.blit(title, (40, 36))

    def _section(self, screen, label, x, y):
        screen.blit(self.font.render(label, True, DIM), (x, y - 28))

    def _draw_doll(self, screen):
        self._section(screen, "EQUIPMENT", DOLL_ORIGIN[0], DOLL_ORIGIN[1])
        for slot, rect in self.slot_rects.items():
            pygame.draw.rect(screen, SLOT_BG, rect, border_radius=6)
            pygame.draw.rect(screen, PANEL_LIGHT, rect, width=2, border_radius=6)
            item = getattr(self.character.equipments, slot)
            if item is None:
                label = self.font_small.render(SLOT_LABELS[slot], True, SLOT_EMPTY_TEXT)
                screen.blit(label, label.get_rect(center=rect.center))
            else:
                self._draw_item_box(screen, item, rect)

    def _draw_inventory(self, screen):
        ox, oy = INV_ORIGIN
        self._section(screen, "INVENTORY", ox, oy)
        grid = pygame.Rect(ox, oy, INV_COLS * INV_CELL, INV_ROWS * INV_CELL)
        pygame.draw.rect(screen, PANEL, grid, border_radius=6)
        for c in range(INV_COLS + 1):
            x = ox + c * INV_CELL
            pygame.draw.line(screen, PANEL_LIGHT, (x, oy), (x, oy + INV_ROWS * INV_CELL))
        for r in range(INV_ROWS + 1):
            y = oy + r * INV_CELL
            pygame.draw.line(screen, PANEL_LIGHT, (ox, y), (ox + INV_COLS * INV_CELL, y))
        for item, rect in self.inv_rects:
            self._draw_item_box(screen, item, rect)

    def _draw_item_box(self, screen, item, rect):
        color = RARITY_COLORS.get(item.rarity.rarity, TEXT)
        pygame.draw.rect(screen, (26, 26, 32), rect, border_radius=5)
        pygame.draw.rect(screen, color, rect, width=2, border_radius=5)
        # Item name, wrapped to the box.
        words = (item.name or "Item").split()
        lines, current = [], ""
        for word in words:
            trial = (current + " " + word).strip()
            if self.font_small.size(trial)[0] <= rect.width - 8:
                current = trial
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        total_h = len(lines) * 16
        y = rect.centery - total_h // 2
        for line in lines[:max(1, rect.height // 16)]:
            surf = self.font_small.render(line, True, color)
            screen.blit(surf, surf.get_rect(centerx=rect.centerx, y=y))
            y += 16

    def _draw_stats(self, screen):
        x, y = STATS_ORIGIN
        self._section(screen, "CHARACTER", x, y)
        panel = pygame.Rect(x, y, STATS_WIDTH, INV_ROWS * INV_CELL)
        pygame.draw.rect(screen, PANEL, panel, border_radius=6)
        s = self.character.stats
        rows = [
            ("Strength", s.attributes.strength.totalStat),
            ("Dexterity", s.attributes.dexterity.totalStat),
            ("Intelligence", s.attributes.intelligence.totalStat),
            (None, None),
            ("Life", s.life.totalStat),
            ("Mana", s.mana.totalStat),
            ("Energy Shield", s.energyShield.totalStat),
            (None, None),
            ("Armour", s.armour.totalStat),
            ("Evasion", s.evasion.totalStat),
            ("Accuracy", s.accuracy.totalStat),
            (None, None),
            ("Physical Dmg", s.physicalDamage.totalStat),
            ("Fire Dmg", s.fireDamage.totalStat),
            ("Cold Dmg", s.coldDamage.totalStat),
            ("Lightning Dmg", s.lightningDamage.totalStat),
            ("Chaos Dmg", s.chaosDamage.totalStat),
            (None, None),
            ("Fire Res", f"{s.fireResistance.totalStat:.0f}%"),
            ("Cold Res", f"{s.coldResistance.totalStat:.0f}%"),
            ("Lightning Res", f"{s.lightningResistance.totalStat:.0f}%"),
            ("Chaos Res", f"{s.chaosResistance.totalStat:.0f}%"),
            (None, None),
            ("Crit Chance", f"{s.criticalStrikeChance.totalStat:.1f}%"),
            ("Crit Multi", f"+{s.criticalStrikeDamage.totalStat:.0f}%"),
            ("Attack Speed", s.attackSpeed.totalStat),
        ]
        ry = y + 12
        for label, value in rows:
            if label is None:
                pygame.draw.line(screen, PANEL_LIGHT, (x + 12, ry + 4),
                                 (x + STATS_WIDTH - 12, ry + 4))
                ry += 10
                continue
            screen.blit(self.font_small.render(label, True, DIM), (x + 14, ry))
            if isinstance(value, float):
                value = f"{value:.1f}".rstrip("0").rstrip(".")
            vsurf = self.font_small.render(str(value), True, TEXT)
            screen.blit(vsurf, vsurf.get_rect(right=x + STATS_WIDTH - 14, y=ry))
            ry += 20

    def _draw_help(self, screen):
        help_text = ("Left-click a bag item to equip  •  left-click an equipped "
                     "item to unequip  •  hover for details  •  Esc to quit")
        surf = self.font_small.render(help_text, True, DIM)
        screen.blit(surf, (40, HEIGHT - 30))

    # -- tooltip -----------------------------------------------------------
    def _tooltip_lines(self, item):
        lines = [(item.name or "Item", RARITY_COLORS.get(item.rarity.rarity, TEXT))]
        lines.append((f"{item.itemClass}  ·  {item.rarity.rarity.name}", DIM))
        implicits = [ln for m in item.implicits for ln in m.lines]
        explicits = [ln for m in item.explicits for ln in m.lines]
        if implicits:
            lines.append(("sep", None))
            lines += [(ln, IMPLICIT_COLOR) for ln in implicits]
        if explicits:
            lines.append(("sep", None))
            lines += [(ln, EXPLICIT_COLOR) for ln in explicits]
        if not implicits and not explicits:
            lines.append(("(no modifiers)", SLOT_EMPTY_TEXT))
        return lines

    def _draw_tooltip(self, screen, mouse_pos):
        target = self.item_at(mouse_pos)
        if target is None:
            return
        kind, value = target
        item = value if kind == "inv" else getattr(self.character.equipments, value)
        if item is None:
            return

        lines = self._tooltip_lines(item)
        pad = 10
        line_h = 22
        width = 0
        for text, _ in lines:
            if text == "sep":
                continue
            width = max(width, self.font_small.size(text)[0])
        width += pad * 2
        height = pad * 2 + len(lines) * line_h

        mx, my = mouse_pos
        x = min(mx + 18, WIDTH - width - 8)
        y = min(my + 18, HEIGHT - height - 8)
        box = pygame.Rect(x, y, width, height)
        pygame.draw.rect(screen, (12, 12, 16), box, border_radius=8)
        border = RARITY_COLORS.get(item.rarity.rarity, TEXT)
        pygame.draw.rect(screen, border, box, width=2, border_radius=8)

        ty = y + pad
        for text, color in lines:
            if text == "sep":
                pygame.draw.line(screen, PANEL_LIGHT, (x + pad, ty + line_h // 2),
                                 (x + width - pad, ty + line_h // 2))
            else:
                screen.blit(self.font_small.render(text, True, color), (x + pad, ty))
            ty += line_h


# ------------------------------------------------------------------ main ----
def run(character, selftest=False):
    pygame.init()
    pygame.display.set_caption("poe_engine — Inventory")
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
    ui = InventoryUI(character)

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

        ui.draw(screen, pygame.mouse.get_pos())
        pygame.display.flip()
        clock.tick(FPS)

        if selftest:
            frames += 1
            # Exercise equip + unequip paths headlessly.
            if frames == 2 and ui.inv_rects:
                ui.handle_click(ui.inv_rects[0][1].center)
            if frames == 4:
                for slot, rect in ui.slot_rects.items():
                    if getattr(character.equipments, slot):
                        ui.handle_click(rect.center)
                        break
            if frames >= 6:
                running = False

    pygame.quit()


def main():
    parser = argparse.ArgumentParser(description="poe_engine inventory screen")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--items", type=int, default=18)
    parser.add_argument("--selftest", action="store_true",
                        help="run headless for a few frames (CI smoke test)")
    args = parser.parse_args()

    if args.selftest:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    if args.seed is not None:
        seed(args.seed)

    hero = make_demo_character(item_count=args.items)
    run(hero, selftest=args.selftest)
    if args.selftest:
        print("gui selftest OK")


if __name__ == "__main__":
    main()
