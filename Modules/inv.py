
import os
import sys
import random
import pygame

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from Modules.button import Button

_image_cache = {}
selected_slot_index = None
selected_equipped_slot = None


POTION_POOL = ["heal_pot", "def_pot", "attk_pot"]
POTION_SLOT_KEYS = ["heal_pot", "def_pot", "attk_pot"]

ARMOR_RING_POOL = ["chestplate_1", "helmet_1", "golden_ring"]

STEEL_FEATHER_CHANCE = 0.75

EQUIP_ATTR_MAP = {
    "helmet":     "equipped_helmet",
    "chestplate": "equipped_chestplate",
    "weapon":     "equipped_weapon",
    "weapon_off": "equipped_weapon_off",
    "accessory":  "equipped_accessory",
}

EQUIP_SLOT_ORDER = [
    ("helmet",     "equipped_helmet"),
    ("chestplate", "equipped_chestplate"),
    ("weapon",     "equipped_weapon"),
    ("weapon_off", "equipped_weapon_off"),
    ("accessory",  "equipped_accessory"),
]


def roll_chest_potions(min_count=2, max_count=3):
    n = random.randint(min_count, max_count)
    return [random.choice(POTION_POOL) for _ in range(n)]


def roll_chest_loot():

    loot = []
    for _ in range(2):
        loot.append(random.choice(POTION_POOL))
    loot.append(random.choice(ARMOR_RING_POOL))

    if random.random() < STEEL_FEATHER_CHANCE:
        loot.append("steel_feather")

    return loot


ENEMY_DROP_TABLE = {
    "slime":          "thorny_vines",
    "tiny_orc:Earth": "dinosaur_tooth",
    "tiny_orc:Water": "water_bearer",
    "tiny_orc:Wind":  "broken_feather",
    "tiny_devil":     "demon_blade",
}


def get_enemy_drop(enemy):
    try:
        from enemies.slime import Slime
    except ImportError:
        Slime = None
    try:
        from enemies.tiny_orc import TinyOrc
    except ImportError:
        TinyOrc = None
    try:
        from enemies.tiny_devil import TinyDevil
    except ImportError:
        TinyDevil = None

    if Slime is not None and isinstance(enemy, Slime):
        return ENEMY_DROP_TABLE["slime"]

    if TinyOrc is not None and isinstance(enemy, TinyOrc):
        elem = getattr(getattr(enemy, "element", None), "element_type", None)
        if elem:
            key = f"tiny_orc:{elem}"
            return ENEMY_DROP_TABLE.get(key)

    if TinyDevil is not None and isinstance(enemy, TinyDevil):
        return ENEMY_DROP_TABLE["tiny_devil"]

    return None


def get_item_image(image_path, size=(44, 44)):
    try:
        size = (max(1, int(size[0])), max(1, int(size[1])))
    except (TypeError, ValueError, IndexError):
        size = (44, 44)

    key = (image_path, size)
    if key in _image_cache:
        return _image_cache[key]

    canvas = pygame.Surface(size, pygame.SRCALPHA)

    if image_path and os.path.exists(image_path):
        try:
            raw = pygame.image.load(image_path).convert_alpha()
            raw_w, raw_h = raw.get_size()
            if raw_w > 0 and raw_h > 0:
                scale_factor = min(size[0] / raw_w, size[1] / raw_h)
                new_w = max(1, int(raw_w * scale_factor))
                new_h = max(1, int(raw_h * scale_factor))
                scaled = pygame.transform.scale(raw, (new_w, new_h))
                canvas.blit(scaled, scaled.get_rect(
                    center=(size[0] // 2, size[1] // 2)))
                _image_cache[key] = canvas
                return canvas
        except Exception as e:
            print(f"[inv] Failed to load image {image_path}: {e}")

    pygame.draw.rect(canvas, (60, 50, 40), (0, 0, size[0], size[1]),
                     border_radius=4)
    _image_cache[key] = canvas
    return canvas


def wrap_text(text, font, max_width):
    words = text.split()
    lines = []
    current = ""
    for word in words:
        test = (current + " " + word).strip()
        if font.size(test)[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]


def ensure_fixed_inventory_size(player, total_slots=45):
    if not hasattr(player, "inventory") or player.inventory is None:
        return
    inv = player.inventory
    if not hasattr(inv, "fixed_items") or inv.fixed_items is None:
        inv.fixed_items = [None] * total_slots
        if hasattr(inv, "items") and inv.items:
            for idx, item in enumerate(inv.items[:total_slots]):
                inv.fixed_items[idx] = item
    inv.items = inv.fixed_items


def player_has_item(player, id_name):
    if not hasattr(player, "inventory") or player.inventory is None:
        return False
    inv = player.inventory
    for item in getattr(inv, "fixed_items", []):
        if item is not None and getattr(item, "id_name", None) == id_name:
            return True
    for attr in EQUIP_ATTR_MAP.values():
        item = getattr(inv, attr, None)
        if item is not None and getattr(item, "id_name", None) == id_name:
            return True
    return False


def _find_stack_index(inv, id_name):
    for idx, item in enumerate(inv.fixed_items):
        if item is None:
            continue
        if getattr(item, "id_name", None) != id_name:
            continue
        if not getattr(item, "is_stackable", False):
            continue
        if getattr(item, "count", 1) < getattr(item, "max_stack", 99):
            return idx
    return None


def _first_empty_index(inv):
    for idx, item in enumerate(inv.fixed_items):
        if item is None:
            return idx
    return None


def _ensure_slot_available(inv, page_size=None):
    if page_size is None:
        page_size = getattr(type(inv), "PAGE_SIZE", 15)

    empty = _first_empty_index(inv)
    if empty is not None:
        return empty

    inv.fixed_items.extend([None] * page_size)
    inv.items = inv.fixed_items
    return len(inv.fixed_items) - page_size


def give_item_by_id(player, item_id):
    if not hasattr(player, "inventory") or player.inventory is None:
        return None
    ensure_fixed_inventory_size(player)
    inv = player.inventory

    try:
        from classes.armory_item import ItemDatabase
    except ImportError:
        return None

    item = ItemDatabase.get_item(item_id)
    if item is None:
        return None

    if getattr(item, "is_unique", False):
        if player_has_item(player, item_id):
            return None
        empty_idx = _ensure_slot_available(inv)
        inv.fixed_items[empty_idx] = item
        return item

    if getattr(item, "is_stackable", False):
        stack_idx = _find_stack_index(inv, item_id)
        if stack_idx is not None:
            inv.fixed_items[stack_idx].count += 1
            return inv.fixed_items[stack_idx]
        empty_idx = _ensure_slot_available(inv)
        item.count = 1
        inv.fixed_items[empty_idx] = item
        return item

    empty_idx = _ensure_slot_available(inv)
    inv.fixed_items[empty_idx] = item
    return item


def give_all_oz_reward_items(player):
    for item_id in ("earth_sword", "flaming_saber", "water_spike"):
        give_item_by_id(player, item_id)


def give_outskirts_reward(player):
    return give_item_by_id(player, "dual_rapier")


def get_pagination_rects(game_frame):
    if not hasattr(game_frame, "inventory_slots") or not game_frame.inventory_slots:
        return None, None, None
    last_left = game_frame.inventory_slots[12] if len(game_frame.inventory_slots) > 12 else game_frame.inventory_slots[-1]
    last_right = game_frame.inventory_slots[14] if len(game_frame.inventory_slots) > 14 else game_frame.inventory_slots[-1]
    btn_y = last_left.bottom + 10
    left_btn = pygame.Rect(last_left.left, btn_y, 32, 24)
    right_btn = pygame.Rect(last_right.right - 32, btn_y, 32, 24)
    center_pos = ((last_left.left + last_right.right) // 2, btn_y + 12)
    return left_btn, right_btn, center_pos


def _draw_count_badge(surface, slot_rect, count):
    font = pygame.font.SysFont("Arial", 14, bold=True)
    text = font.render(f"x{count}", True, (255, 255, 255))
    pad = 2
    bw = text.get_width() + pad * 2
    bh = text.get_height() + pad * 2
    rect = pygame.Rect(0, 0, bw, bh)
    rect.bottomright = (slot_rect.right - 3, slot_rect.bottom - 2)
    bg = pygame.Surface((bw, bh), pygame.SRCALPHA)
    bg.fill((0, 0, 0, 190))
    surface.blit(bg, rect.topleft)
    pygame.draw.rect(surface, (255, 215, 0), rect, width=1, border_radius=3)
    surface.blit(text, (rect.x + pad, rect.y + pad))


def _ensure_tab_state(inv):
    if not hasattr(inv, "_active_tab"):
        inv._active_tab = "weapon"
    if not hasattr(inv, "_page_weapon"):
        inv._page_weapon = 0
    if not hasattr(inv, "_page_armor"):
        inv._page_armor = 0


def _get_filtered_inventory(inv, tab_key):
    try:
        from classes.armory_item import Weapon, Armor, Accessory
    except ImportError:
        return []

    out = []
    for idx, item in enumerate(inv.fixed_items):
        if item is None:
            continue
        if tab_key == "weapon":
            if isinstance(item, Weapon):
                out.append((idx, item))
        else:
            if isinstance(item, (Armor, Accessory)):
                out.append((idx, item))
    return out


def _get_tab_page_attr(tab_key):
    return "_page_weapon" if tab_key == "weapon" else "_page_armor"


def draw_inventory_and_equipment(screen, player, game_frame):
    global selected_slot_index, selected_equipped_slot

    ensure_fixed_inventory_size(player)
    inv = player.inventory
    if not inv:
        return

    _ensure_tab_state(inv)

    if hasattr(game_frame, "equip_slots"):
        for slot_key, attr_name in EQUIP_SLOT_ORDER:
            slot_rect = game_frame.equip_slots.get(slot_key)
            item = getattr(inv, attr_name, None)
            if slot_rect and item:
                img = get_item_image(getattr(item, "image_path", ""),
                                     size=(36, 36))
                screen.blit(img, img.get_rect(center=slot_rect.center))

    potion_indices = {}
    for idx, item in enumerate(inv.fixed_items):
        if item is None:
            continue
        iid = getattr(item, "id_name", None)
        if iid in POTION_SLOT_KEYS and iid not in potion_indices:
            potion_indices[iid] = idx

    try:
        from classes.armory_item import ItemDatabase as _ItemDB
    except ImportError:
        _ItemDB = None

    if hasattr(game_frame, "potion_slots"):
        for slot_i, potion_key in enumerate(POTION_SLOT_KEYS):
            if slot_i >= len(game_frame.potion_slots):
                break
            slot_rect = game_frame.potion_slots[slot_i]
            real_idx = potion_indices.get(potion_key)

            if real_idx is not None:
                potion_item = inv.fixed_items[real_idx]
                img = get_item_image(getattr(potion_item, "image_path", ""),
                                     size=(40, 40))
                screen.blit(img, img.get_rect(center=slot_rect.center))
                count = getattr(potion_item, "count", 1)
                if count > 1:
                    _draw_count_badge(screen, slot_rect, count)
            else:
                if _ItemDB is not None:
                    proto = _ItemDB.get_item(potion_key)
                    if proto is not None:
                        path = getattr(proto, "image_path", "")
                        base = get_item_image(path, size=(40, 40))
                        faded = base.copy()
                        faded.set_alpha(60)
                        screen.blit(faded, faded.get_rect(center=slot_rect.center))

    if hasattr(game_frame, "tab_armor_rect") and hasattr(game_frame, "tab_weapon_rect"):
        font_tab = pygame.font.SysFont("Georgia", 15, bold=True)
        for tab_key, tab_rect, label in (
            ("armor",  game_frame.tab_armor_rect,  "ARMORS"),
            ("weapon", game_frame.tab_weapon_rect, "WEAPONS"),
        ):
            is_active = (inv._active_tab == tab_key)
            if is_active:
                bg_col     = (45, 38, 70)
                border_col = (255, 215, 0)
                text_col   = (255, 215, 0)
            else:
                bg_col     = (22, 22, 40)
                border_col = (90, 75, 45)
                text_col   = (150, 150, 170)

            pygame.draw.rect(screen, bg_col, tab_rect, border_radius=6)
            pygame.draw.rect(screen, border_col, tab_rect, width=2, border_radius=6)

            lbl = font_tab.render(label, True, text_col)
            screen.blit(lbl, lbl.get_rect(center=tab_rect.center))

            if is_active:
                pygame.draw.line(
                    screen, (255, 215, 0),
                    (tab_rect.left + 8, tab_rect.bottom - 4),
                    (tab_rect.right - 8, tab_rect.bottom - 4),
                    2,
                )

    filtered = _get_filtered_inventory(inv, inv._active_tab)
    page_attr = _get_tab_page_attr(inv._active_tab)
    current_page = getattr(inv, page_attr, 0)
    max_pages = max(1, (len(filtered) + 14) // 15)
    current_page = max(0, min(current_page, max_pages - 1))
    setattr(inv, page_attr, current_page)

    start_i = current_page * 15
    page_entries = filtered[start_i : start_i + 15]

    if hasattr(game_frame, "inventory_slots"):
        for slot_i, slot_rect in enumerate(game_frame.inventory_slots):
            if slot_i >= len(page_entries):
                break
            _real_idx, item = page_entries[slot_i]
            img = get_item_image(getattr(item, "image_path", ""))
            screen.blit(img, img.get_rect(center=slot_rect.center))
            if getattr(item, "is_stackable", False) and getattr(item, "count", 1) > 1:
                _draw_count_badge(screen, slot_rect, item.count)

    left_btn, right_btn, text_center = get_pagination_rects(game_frame)
    if left_btn and right_btn:
        font_nav = pygame.font.SysFont("Georgia", 14, bold=True)
        can_prev = current_page > 0
        can_next = current_page < max_pages - 1

        pygame.draw.rect(screen, (30, 35, 45), left_btn, border_radius=4)
        pygame.draw.rect(screen,
                         (255, 215, 0) if can_prev else (80, 80, 80),
                         left_btn, width=1, border_radius=4)
        lbl_left = font_nav.render("<", True,
                                   (255, 215, 0) if can_prev else (100, 100, 100))
        screen.blit(lbl_left, lbl_left.get_rect(center=left_btn.center))

        pygame.draw.rect(screen, (30, 35, 45), right_btn, border_radius=4)
        pygame.draw.rect(screen,
                         (255, 215, 0) if can_next else (80, 80, 80),
                         right_btn, width=1, border_radius=4)
        lbl_right = font_nav.render(">", True,
                                    (255, 215, 0) if can_next else (100, 100, 100))
        screen.blit(lbl_right, lbl_right.get_rect(center=right_btn.center))

        lbl_page = font_nav.render(
            f"Page {current_page + 1}/{max_pages}", True, (255, 215, 0))
        screen.blit(lbl_page, lbl_page.get_rect(center=text_center))

    if selected_equipped_slot is not None:
        attr_name = EQUIP_ATTR_MAP.get(selected_equipped_slot)
        item = getattr(inv, attr_name, None) if attr_name else None
        if item is not None:
            draw_item_modal(screen, item, mode="equipped")
        else:
            selected_equipped_slot = None

    if selected_slot_index is not None and 0 <= selected_slot_index < len(inv.fixed_items):
        item = inv.fixed_items[selected_slot_index]
        if item is not None:
            draw_item_modal(screen, item, mode="inventory")
        else:
            selected_slot_index = None


def _make_buttons(modal_rect, button_specs):
    font_btn = pygame.font.SysFont("Georgia", 15, bold=True)
    btn_w, btn_h = 118, 40
    spacing = 12
    btn_y = modal_rect.bottom - btn_h - 22

    total_w = (btn_w * len(button_specs)) + (spacing * (len(button_specs) - 1))
    start_x = modal_rect.x + (modal_rect.width - total_w) // 2

    result = {}
    for i, (label, key) in enumerate(button_specs):
        rect = pygame.Rect(start_x + i * (btn_w + spacing),
                           btn_y, btn_w, btn_h)
        btn = Button(rect.x, rect.y, btn_w, btn_h, text=label, font=font_btn)
        result[key] = (btn, rect)
    return result


def get_modal_buttons(modal_rect, action_text, is_weapon=False,
                      show_delete=True, allow_off_hand=True):
    specs = []
    if is_weapon:
        specs.append((action_text, "equip_main"))
        if allow_off_hand:
            specs.append(("OFF-HAND", "equip_off"))
    else:
        specs.append((action_text, "equip_main"))

    if show_delete:
        specs.append(("DELETE", "delete"))
    specs.append(("CANCEL", "cancel"))

    result = _make_buttons(modal_rect, specs)
    return (
        result.get("equip_main", (None, None)),
        result.get("equip_off",  (None, None)),
        result.get("delete",     (None, None)),
        result.get("cancel",     (None, None)),
    )


def get_equipped_modal_buttons(modal_rect, show_delete=True):
    specs = [("UNEQUIP", "unequip")]
    if show_delete:
        specs.append(("DELETE", "delete"))
    specs.append(("CANCEL", "cancel"))

    result = _make_buttons(modal_rect, specs)
    return (
        result.get("unequip", (None, None)),
        result.get("delete",  (None, None)),
        result.get("cancel",  (None, None)),
    )


SPECIAL_EFFECT_DESCRIPTIONS = {
    "permanent_poison": lambda v: "Poison inflicted by this weapon is permanent.",
    "permanent_poison_off_hand": lambda v: "Poison is permanent when equipped in the OFF-HAND slot.",
    "ignore_earth_immunity": lambda v: "Ignores Earth Immunity.",
    "inflict_poison": lambda v: "Inflicts Poison on hit.",
    "first_strike": lambda v: "Guarantees you move first each turn.",
    "scaling_evade": lambda v: f"Boosts evade up to {int(v * 100)}% the longer the fight goes.",
    "ignore_def_chance": lambda v: f"{int(v * 100)}% chance to ignore enemy Defense.",
    "inflict_bleed": lambda v: "Inflicts Bleed on hit.",
    "inflict_burn": lambda v: f"Inflicts {v} Burn per turn.",
    "transform_blue_flame": lambda v: "Transforms existing Burn stacks into Blue Flame.",
    "trigger_burn_instantly": lambda v: "Instantly triggers Burn damage on hit.",
    "burn_scaling": lambda v: f"Deals Burn damage equal to {int(v * 100)}% of Attack.",
    "inflict_slow": lambda v: "Inflicts Slow on hit.",
    "inflict_weak": lambda v: f"Inflicts {v} Weak (target deals -5 dmg per stack).",
    "stun_chance": lambda v: f"{int(v * 100)}% chance to stun the enemy.",
    "ignore_water_immunity": lambda v: "Ignores Water Immunity.",
    "true_damage": lambda v: "Deals True Damage, ignoring all Defense.",
    "moon_damage": lambda v: ("MOON DAMAGE: ignores DEF and enemy element, "
                              "always deals 100%+ damage. Deals DOUBLE damage "
                              "to Gorgona on BASIC, ELEMENTAL SLASH, and BURST."),
}


def describe_special_effects(special_effects):
    lines = []
    for effect_name, effect_value in special_effects.items():
        fn = SPECIAL_EFFECT_DESCRIPTIONS.get(effect_name)
        lines.append(fn(effect_value) if fn
                     else f"Special: {effect_name} ({effect_value})")
    return lines


def build_stat_lines_for_item(item):
    try:
        from classes.armory_item import Weapon, Armor, Consumable, Accessory
    except ImportError:
        Weapon = Armor = Consumable = Accessory = type(None)

    stats_lines = []

    if isinstance(item, Weapon):
        stats_lines.append(f"Physical Attack: {item.min_atk} - {item.max_atk}")
        if item.max_elem_atk > 0:
            stats_lines.append(f"Elemental Attack: {item.min_elem_atk} - {item.max_elem_atk}")
        if item.element and item.element != "Neutral":
            stats_lines.append(f"Element: {item.element}")
        if getattr(item, "off_hand_only", False):
            stats_lines.append("Slot: OFF-HAND only")

        if item.special_effects:
            stats_lines.extend(describe_special_effects(item.special_effects))

        passive = getattr(item, "passive", None) or {}

        if "defense" in passive:
            stats_lines.append(f"Passive: +{passive['defense']} DEF")
        if "atk_mult" in passive:
            stats_lines.append(f"Passive: +{int(passive['atk_mult'] * 100)}% ATK")
        if "elem_atk_mult" in passive:
            stats_lines.append(f"Passive: +{int(passive['elem_atk_mult'] * 100)}% Elemental ATK")
        if "elem_dmg_bonus" in passive:
            for elem, amt in passive["elem_dmg_bonus"].items():
                stats_lines.append(f"Passive: +{int(amt * 100)}% {elem} damage")

        if "status_dmg_bonus" in passive:
            for status_key, amt in passive["status_dmg_bonus"].items():
                pretty = status_key.replace("_", " ").capitalize()
                stats_lines.append(f"Passive: +{int(amt * 100)}% {pretty} damage")

        burst = getattr(item, "burst", None)
        if burst:
            stats_lines.append(
                f"Burst: {burst.get('name', '?')} ({burst.get('type', 'aoe')})")

            burst_status = burst.get("status")
            if burst_status:
                try:
                    s_key, s_stacks = burst_status
                    pretty = s_key.replace("_", " ").capitalize()
                    stats_lines.append(f"Burst Effect: {pretty} x{s_stacks}")
                except (TypeError, ValueError):
                    pass

    elif isinstance(item, Armor):
        if item.def_boost:
            stats_lines.append(f"Defense: +{item.def_boost}")
        if getattr(item, "hp_bonus", 0):
            stats_lines.append(f"HP: +{item.hp_bonus}")

    elif isinstance(item, Consumable):
        if item.effect_type == "heal_percent":
            stats_lines.append(f"Restores {item.effect_value}% of MISSING HP")
        elif item.effect_type == "boost_def":
            stats_lines.append(f"Boosts Defense by {item.effect_value} for the current battle")
        elif item.effect_type == "boost_atk":
            stats_lines.append(f"Boosts Attack by {item.effect_value} for the current battle")
        elif item.effect_type == "boost_elem_atk":
            stats_lines.append(f"Boosts Elemental Attack by {item.effect_value}")
        else:
            stats_lines.append(f"Effect: {item.effect_type} ({item.effect_value})")
        if getattr(item, "count", 1) > 1:
            stats_lines.append(f"Count: {item.count}")

    elif isinstance(item, Accessory):
        if getattr(item, "hp_bonus", 0):
            stats_lines.append(f"HP: +{item.hp_bonus}")
        if getattr(item, "atk_bonus", 0):
            stats_lines.append(f"Attack: +{item.atk_bonus}")
        if getattr(item, "elem_atk_bonus", 0):
            stats_lines.append(f"Elemental Attack: +{item.elem_atk_bonus}")
        if getattr(item, "id_name", "") == "golden_ring" and item._roll_key:
            label = {"hp": "HP", "atk": "Attack",
                     "elem_atk": "Elemental Attack"}.get(item._roll_key, item._roll_key)
            stats_lines.append(f"Rolled: +{item._roll_amount} {label}")
        if not stats_lines:
            stats_lines.append("Effect applied when equipped.")

    if getattr(item, "is_permanent", False):
        stats_lines.append("Permanent - cannot be dropped.")
    if not stats_lines:
        stats_lines.append("Standard adventure equipment.")
    return stats_lines


MODAL_W = 580
MODAL_H = 440
ICON_BOX = 110
HEADER_H = 62
DESC_BOTTOM_PAD = 78


def get_modal_size(item):
    return (MODAL_W, MODAL_H)


def _compute_modal_rect(item):
    modal_width, modal_height = get_modal_size(item)
    return pygame.Rect(
        (1920 - modal_width) // 2,
        (1080 - modal_height) // 2,
        modal_width, modal_height,
    )


def draw_item_modal(screen, item, mode="inventory"):
    modal_rect = _compute_modal_rect(item)

    overlay = pygame.Surface((1920, 1080), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 170))
    screen.blit(overlay, (0, 0))

    pygame.draw.rect(screen, (22, 20, 38), modal_rect, border_radius=10)
    pygame.draw.rect(screen, (212, 175, 55), modal_rect,
                     width=3, border_radius=10)

    try:
        from Modules.button import draw_corner_brackets
        draw_corner_brackets(screen, modal_rect, (212, 175, 55),
                             length=22, thickness=3, offset=6)
    except Exception:
        pass

    font_title  = pygame.font.SysFont("Georgia", 26, bold=True)
    font_stats  = pygame.font.SysFont("Georgia", 17)
    font_desc   = pygame.font.SysFont("Georgia", 15)

    title_text = getattr(item, "name", "Unknown Item")
    title_surf = font_title.render(title_text, True, (255, 215, 0))
    title_rect = title_surf.get_rect(
        center=(modal_rect.centerx, modal_rect.top + 34))
    screen.blit(title_surf, title_rect)

    pygame.draw.line(
        screen, (212, 175, 55),
        (modal_rect.left + 30, modal_rect.top + HEADER_H),
        (modal_rect.right - 30, modal_rect.top + HEADER_H),
        2,
    )

    icon_x = modal_rect.left + 30
    icon_y = modal_rect.top + HEADER_H + 20
    icon_box = pygame.Rect(icon_x, icon_y, ICON_BOX, ICON_BOX)

    pygame.draw.rect(screen, (30, 28, 50), icon_box, border_radius=8)
    pygame.draw.rect(screen, (90, 75, 45), icon_box, width=2, border_radius=8)

    img = get_item_image(getattr(item, "image_path", ""),
                         size=(ICON_BOX - 18, ICON_BOX - 18))
    screen.blit(img, img.get_rect(center=icon_box.center))

    stats_lines = build_stat_lines_for_item(item)
    stats_x = icon_box.right + 20
    stats_y = icon_box.top + 2
    stats_max_w = modal_rect.right - stats_x - 30
    line_h = 22

    max_stat_lines = (ICON_BOX // line_h) + 1
    for line in stats_lines[:max_stat_lines]:
        if font_stats.size(line)[0] > stats_max_w:
            trimmed = line
            while trimmed and font_stats.size(trimmed + "...")[0] > stats_max_w:
                trimmed = trimmed[:-1]
            line = (trimmed + "...") if trimmed else line
        line_surf = font_stats.render(line, True, (230, 225, 200))
        screen.blit(line_surf, (stats_x, stats_y))
        stats_y += line_h

    desc_divider_y = icon_box.bottom + 18
    pygame.draw.line(
        screen, (60, 55, 85),
        (modal_rect.left + 30, desc_divider_y),
        (modal_rect.right - 30, desc_divider_y),
        1,
    )

    description = getattr(item, "description", "") or ""
    burst = getattr(item, "burst", None)
    if burst and burst.get("desc"):
        prefix = f"Burst ({burst.get('name')}): {burst.get('desc')}  "
    else:
        prefix = "Info: "

    desc_x = modal_rect.left + 30
    desc_y = desc_divider_y + 12
    desc_max_w = modal_rect.width - 60
    desc_bottom_limit = modal_rect.bottom - DESC_BOTTOM_PAD

    for line in wrap_text(f"{prefix}{description}", font_desc, desc_max_w):
        if desc_y + 18 > desc_bottom_limit:
            break
        line_surf = font_desc.render(line, True, (180, 178, 200))
        screen.blit(line_surf, (desc_x, desc_y))
        desc_y += 18

    try:
        from classes.armory_item import Consumable, Weapon
        is_consumable = isinstance(item, Consumable)
        is_weapon = isinstance(item, Weapon)
    except ImportError:
        is_consumable = False
        is_weapon = False

    if mode == "equipped":
        show_delete = (not is_weapon) and (
            not getattr(item, "is_permanent", False))
        (btn_unequip, _), (btn_delete, _), (btn_cancel, _) = \
            get_equipped_modal_buttons(modal_rect, show_delete=show_delete)

        btn_unequip.draw(screen)
        if btn_delete is not None:
            btn_delete.draw(screen)
        btn_cancel.draw(screen)
        return

    btn_action_text = "USE" if is_consumable else "EQUIP"
    if is_weapon and getattr(item, "off_hand_only", False):
        btn_action_text = "MAIN (NO)"

    show_delete = not getattr(item, "is_permanent", False)

    (btn_equip, _), (btn_off, _), (btn_delete, _), (btn_cancel, _) = \
        get_modal_buttons(modal_rect, btn_action_text,
                          is_weapon=is_weapon, show_delete=show_delete)

    btn_equip.draw(screen)
    if btn_off is not None:
        btn_off.draw(screen)
    if btn_delete is not None:
        btn_delete.draw(screen)
    btn_cancel.draw(screen)


def handle_inventory_click(pos, player, game_frame):
    global selected_slot_index, selected_equipped_slot

    ensure_fixed_inventory_size(player)
    inv = player.inventory
    if not inv:
        return None

    _ensure_tab_state(inv)

    try:
        from classes.armory_item import Consumable, Accessory, Armor, Weapon
    except ImportError:
        Consumable = Accessory = Armor = Weapon = type(None)

    if selected_equipped_slot is not None:
        attr_name = EQUIP_ATTR_MAP.get(selected_equipped_slot)
        item = getattr(inv, attr_name, None) if attr_name else None

        if item is None:
            selected_equipped_slot = None
        else:
            modal_rect = _compute_modal_rect(item)
            is_weapon = isinstance(item, Weapon)
            show_delete = (not is_weapon) and (
                not getattr(item, "is_permanent", False))

            (_, rect_unequip), (_, rect_delete), (_, rect_cancel) = \
                get_equipped_modal_buttons(modal_rect, show_delete=show_delete)

            if modal_rect.collidepoint(pos):
                if rect_unequip.collidepoint(pos):
                    empty_idx = _ensure_slot_available(inv)
                    if hasattr(item, "unequip"):
                        item.unequip(player)
                    inv.fixed_items[empty_idx] = item
                    setattr(inv, attr_name, None)
                    inv._active_tab = "weapon" if is_weapon else "armor"
                    selected_equipped_slot = None
                    return f"Unequipped {item.name}!"

                elif rect_delete is not None and rect_delete.collidepoint(pos):
                    del_name = getattr(item, "name", "Item")
                    if hasattr(item, "unequip"):
                        item.unequip(player)
                    setattr(inv, attr_name, None)
                    selected_equipped_slot = None
                    return f"Deleted {del_name}."

                elif rect_cancel.collidepoint(pos):
                    selected_equipped_slot = None
                    return None
            else:
                selected_equipped_slot = None
                return None

    if selected_slot_index is not None and 0 <= selected_slot_index < len(inv.fixed_items):
        item = inv.fixed_items[selected_slot_index]
        if item is None:
            selected_slot_index = None
        else:
            modal_rect = _compute_modal_rect(item)
            is_weapon = isinstance(item, Weapon)
            is_consumable = isinstance(item, Consumable)

            btn_action_text = "USE" if is_consumable else "EQUIP"
            if is_weapon and getattr(item, "off_hand_only", False):
                btn_action_text = "MAIN (NO)"

            show_delete = not getattr(item, "is_permanent", False)

            (_, rect_equip), (_, rect_off), (_, rect_delete), (_, rect_cancel) = \
                get_modal_buttons(modal_rect, btn_action_text,
                                  is_weapon=is_weapon, show_delete=show_delete)

            if modal_rect.collidepoint(pos):
                if rect_equip.collidepoint(pos):
                    if is_weapon and getattr(item, "off_hand_only", False):
                        return f"{item.name} can only be equipped in the OFF-HAND slot."

                    msg = None

                    if is_consumable:
                        result = item.use(player) if hasattr(item, "use") \
                            else (True, f"Used {item.name}")

                        if isinstance(result, tuple):
                            consumed, msg = result
                        else:
                            consumed, msg = True, str(result)

                        if consumed:
                            item.count -= 1
                            if item.count <= 0:
                                inv.fixed_items[selected_slot_index] = None

                            if getattr(item, "effect_type", "") == "heal_percent":
                                cb = getattr(player, "_on_heal_consumable_used", None)
                                if callable(cb):
                                    try:
                                        cb()
                                    except Exception as e:
                                        print(f"[inv] heal consumable callback failed: {e}")

                    elif isinstance(item, Armor):
                        item_id = (getattr(item, "id_name", "") or
                                   getattr(item, "name", "")).lower()
                        if "helmet" in item_id:
                            old_eq = getattr(inv, "equipped_helmet", None)
                            if old_eq and hasattr(old_eq, "unequip"):
                                old_eq.unequip(player)
                            inv.equipped_helmet = item
                            if hasattr(item, "equip"):
                                item.equip(player)
                            inv.fixed_items[selected_slot_index] = old_eq
                        else:
                            old_eq = getattr(inv, "equipped_chestplate", None)
                            if old_eq and hasattr(old_eq, "unequip"):
                                old_eq.unequip(player)
                            inv.equipped_chestplate = item
                            if hasattr(item, "equip"):
                                item.equip(player)
                            inv.fixed_items[selected_slot_index] = old_eq
                        msg = f"Equipped {item.name}!"

                    elif is_weapon:
                        old_eq = getattr(inv, "equipped_weapon", None)
                        if old_eq and hasattr(old_eq, "unequip"):
                            old_eq.unequip(player)
                        inv.equipped_weapon = item
                        if hasattr(item, "equip"):
                            item.equip(player)
                        inv.fixed_items[selected_slot_index] = old_eq
                        msg = f"Equipped {item.name} to main hand!"

                    elif isinstance(item, Accessory):
                        old_eq = getattr(inv, "equipped_accessory", None)
                        if old_eq and hasattr(old_eq, "unequip"):
                            old_eq.unequip(player)
                        inv.equipped_accessory = item
                        if hasattr(item, "equip"):
                            item.equip(player)
                        inv.fixed_items[selected_slot_index] = old_eq
                        msg = f"Equipped {item.name}!"

                    selected_slot_index = None
                    return msg

                elif rect_off is not None and rect_off.collidepoint(pos):
                    if is_weapon:
                        old_eq = getattr(inv, "equipped_weapon_off", None)
                        if old_eq and hasattr(old_eq, "unequip"):
                            old_eq.unequip(player)
                        inv.equipped_weapon_off = item
                        if hasattr(item, "equip"):
                            item.equip(player)
                        inv.fixed_items[selected_slot_index] = old_eq
                        selected_slot_index = None
                        return f"Equipped {item.name} to off-hand!"

                elif rect_delete is not None and rect_delete.collidepoint(pos):
                    if getattr(item, "is_permanent", False):
                        return f"{item.name} cannot be dropped."
                    del_name = getattr(item, "name", "Item")
                    inv.fixed_items[selected_slot_index] = None
                    selected_slot_index = None
                    return f"Deleted {del_name}."

                elif rect_cancel.collidepoint(pos):
                    selected_slot_index = None
                    return None
            else:
                selected_slot_index = None
                return None

    if hasattr(game_frame, "tab_armor_rect") and \
            game_frame.tab_armor_rect.collidepoint(pos):
        inv._active_tab = "armor"
        return None
    if hasattr(game_frame, "tab_weapon_rect") and \
            game_frame.tab_weapon_rect.collidepoint(pos):
        inv._active_tab = "weapon"
        return None

    if hasattr(game_frame, "potion_slots"):
        for slot_i, potion_key in enumerate(POTION_SLOT_KEYS):
            if slot_i >= len(game_frame.potion_slots):
                break
            if game_frame.potion_slots[slot_i].collidepoint(pos):
                for idx, item in enumerate(inv.fixed_items):
                    if item is None:
                        continue
                    if getattr(item, "id_name", None) == potion_key:
                        selected_slot_index = idx
                        return None
                return None

    left_btn, right_btn, _ = get_pagination_rects(game_frame)
    if left_btn and right_btn:
        page_attr = _get_tab_page_attr(inv._active_tab)
        current_page = getattr(inv, page_attr, 0)
        filtered = _get_filtered_inventory(inv, inv._active_tab)
        max_pages = max(1, (len(filtered) + 14) // 15)

        if left_btn.collidepoint(pos) and current_page > 0:
            setattr(inv, page_attr, current_page - 1)
            return None
        elif right_btn.collidepoint(pos) and current_page < max_pages - 1:
            setattr(inv, page_attr, current_page + 1)
            return None

    if hasattr(game_frame, "inventory_slots"):
        page_attr = _get_tab_page_attr(inv._active_tab)
        current_page = getattr(inv, page_attr, 0)
        filtered = _get_filtered_inventory(inv, inv._active_tab)
        start_i = current_page * 15
        page_entries = filtered[start_i : start_i + 15]

        for slot_i, slot_rect in enumerate(game_frame.inventory_slots):
            if slot_rect.collidepoint(pos):
                if slot_i < len(page_entries):
                    real_idx, _item = page_entries[slot_i]
                    selected_slot_index = real_idx
                return None

    if hasattr(game_frame, "equip_slots"):
        for slot_key, attr_name in EQUIP_SLOT_ORDER:
            slot_rect = game_frame.equip_slots.get(slot_key)
            if slot_rect and slot_rect.collidepoint(pos):
                item = getattr(inv, attr_name, None)
                if item:
                    selected_equipped_slot = slot_key
                return None

    return None