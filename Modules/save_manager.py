import os
import json

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
SAVES_DIR = os.path.join(PROJECT_ROOT, "saves")

SAVE_VERSION = 8

HORDE_COUNT = 3
DEVIL_HORDE_COUNT = 3

EQUIP_ATTRS = (
    "equipped_helmet",
    "equipped_chestplate",
    "equipped_weapon",
    "equipped_weapon_off",
    "equipped_accessory",
)


def _normalize_horde_list(raw, count=HORDE_COUNT):
    if not isinstance(raw, (list, tuple)):
        raw = []
    out = [bool(x) for x in list(raw)[:count]]
    while len(out) < count:
        out.append(False)
    return out


def get_save_file_path(slot_id):
    if not os.path.exists(SAVES_DIR):
        os.makedirs(SAVES_DIR)
    return os.path.join(SAVES_DIR, f"slot_{slot_id}.json")


def load_save_data(slot_id):
    file_path = get_save_file_path(slot_id)
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None
    return None


def save_save_data(slot_id, data):
    file_path = get_save_file_path(slot_id)
    with open(file_path, "w") as f:
        json.dump(data, f, indent=4)


def delete_save_data(slot_id):
    file_path = get_save_file_path(slot_id)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            print(f"[Save Manager] Erased save slot {slot_id} from disk.")
        except OSError as error:
            print(f"[Save Manager] Error removing save slot {slot_id}: {error}")


def _unequip_all_for_save(player):
    if not hasattr(player, "inventory") or player.inventory is None:
        return
    inv = player.inventory
    for attr in EQUIP_ATTRS:
        item = getattr(inv, attr, None)
        if item is not None and hasattr(item, "unequip"):
            try:
                item.unequip(player)
            except Exception as e:
                print(f"[Save Manager] unequip() failed for {attr}: {e}")


def _restore_equipment(player):
    if not hasattr(player, "inventory") or player.inventory is None:
        return
    inv = player.inventory
    for attr in EQUIP_ATTRS:
        item = getattr(inv, attr, None)
        if item is not None and hasattr(item, "equip"):
            try:
                item.equip(player)
            except Exception as e:
                print(f"[Save Manager] equip() failed for {attr}: {e}")


def _reapply_equipment_passives(player):
    if not hasattr(player, "inventory") or player.inventory is None:
        return
    inv = player.inventory
    for attr in EQUIP_ATTRS:
        item = getattr(inv, attr, None)
        if item is not None and hasattr(item, "equip"):
            try:
                item.equip(player)
            except Exception as e:
                print(f"[Save Manager] re-equip() failed for {attr}: {e}")


def _serialize_inventory(inv):
    try:
        from classes.armory_item import ItemDatabase
    except ImportError:
        ItemDatabase = None

    out = []
    for item in inv.fixed_items:
        if item is None:
            out.append(None)
            continue
        entry = {
            "name": item.name,
            "count": int(getattr(item, "count", 1)),
        }
        if ItemDatabase is not None:
            rolled = ItemDatabase.get_save_data(item)
            if rolled:
                entry["rolled"] = rolled
        out.append(entry)
    return out


def _deserialize_inventory(raw_list, inv):
    try:
        from classes.armory_item import ItemDatabase
    except ImportError:
        ItemDatabase = None
    if ItemDatabase is None:
        return

    min_size = getattr(type(inv), "INVENTORY_SIZE", 45)
    page_size = getattr(type(inv), "PAGE_SIZE", 15)

    saved_len = len(raw_list) if raw_list else 0
    total = max(min_size, saved_len)
    if total % page_size != 0:
        total += page_size - (total % page_size)

    inv.fixed_items = [None] * total
    inv.items = inv.fixed_items
    seen_unique = set()

    for idx, entry in enumerate(raw_list[:total]):
        if entry is None:
            continue
        rolled = {}
        if isinstance(entry, str):
            name = entry
            count = 1
        elif isinstance(entry, dict):
            name = entry.get("name")
            count = entry.get("count", 1)
            rolled = entry.get("rolled") or {}
        else:
            continue
        if not name:
            continue

        item = ItemDatabase.get_item_by_name(name, rolled)
        if item is None:
            continue

        if getattr(item, "is_stackable", False):
            try:
                item.count = max(1, int(count))
            except (TypeError, ValueError):
                item.count = 1

        if getattr(item, "is_unique", False):
            if item.id_name in seen_unique:
                continue
            seen_unique.add(item.id_name)

        inv.fixed_items[idx] = item


def _serialize_equipment_slot(item):
    if item is None:
        return None
    entry = {"name": getattr(item, "name", None)}
    try:
        from classes.armory_item import ItemDatabase
        rolled = ItemDatabase.get_save_data(item)
        if rolled:
            entry["rolled"] = rolled
    except ImportError:
        pass
    return entry


def _deserialize_equipment_slot(raw, ItemDatabase):
    if raw is None or ItemDatabase is None:
        return None
    if isinstance(raw, dict):
        name = raw.get("name")
        rolled = raw.get("rolled") or {}
        return ItemDatabase.get_item_by_name(name, rolled)
    if isinstance(raw, str):
        return ItemDatabase.get_item_by_name(raw)
    return None


def save_full_game_state(slot_id, player=None, wizard=None, orc=None,
                         enemies=None, position_valid=True):
    existing_data = load_save_data(slot_id) or {}

    if player:
        max_hp = getattr(player, "max_hp", 100)
        player.hp = max_hp

    all_enemies = []
    if orc is not None:
        all_enemies.append(orc)
    if enemies:
        all_enemies.extend(enemies)

    for enemy in all_enemies:
        max_hp = getattr(enemy, "max_hp", None)
        if max_hp is None:
            continue
        is_dead = (getattr(enemy, "is_defeated", False)
                   or getattr(enemy, "hp", 0) <= 0)
        if not is_dead:
            enemy.hp = max_hp

    if wizard and player:
        player.wizard_dialogue_state = getattr(wizard, "dialogue_state", "PART_1")

    if player is not None:
        _unequip_all_for_save(player)

    save_data = {
        "save_version": SAVE_VERSION,
        "slot_id": slot_id,
        "player_name": existing_data.get("player_name",
                                          getattr(player, "name", "Solaris")),
        "prologue_completed": True,
    }

    if player:
        chest_opened_list = _normalize_horde_list(
            getattr(player, "outskirts_horde_chest_opened_list", None),
            HORDE_COUNT)
        legacy_chest_opened = bool(
            getattr(player, "outskirts_horde_chest_opened", False)
            or all(chest_opened_list)
        )

        deeper_defeated_list = _normalize_horde_list(
            getattr(player, "deeper_horde_defeated_list", None),
            DEVIL_HORDE_COUNT)
        deeper_chest_list = _normalize_horde_list(
            getattr(player, "deeper_horde_chest_opened_list", None),
            DEVIL_HORDE_COUNT)
        legacy_deeper_defeated = bool(
            getattr(player, "deeper_devils_defeated", False)
            or all(deeper_defeated_list)
        )
        legacy_deeper_chest = bool(
            getattr(player, "deeper_devils_chest_opened", False)
            or all(deeper_chest_list)
        )

        p_dict = {
            "name": getattr(player, "name", "Solaris"),
            "x": getattr(player, "x", 0),
            "y": getattr(player, "y", 0),
            "spawn_x": getattr(player, "spawn_x", getattr(player, "x", 0)),
            "spawn_y": getattr(player, "spawn_y", getattr(player, "y", 0)),
            "hp": getattr(player, "hp", 100),
            "max_hp": getattr(player, "max_hp", 100),
            "atk": getattr(player, "atk", 15),
            "defense": getattr(player, "defense", 5),

            "wizard_dialogue_state": getattr(player, "wizard_dialogue_state", "PART_1"),
            "village_orc_defeated": getattr(player, "village_orc_defeated", False),
            "village_orc_reward_done": getattr(player, "village_orc_reward_done", False),
            "village_orc_chest_opened": getattr(player, "village_orc_chest_opened", False),

            "outskirts_wizard_state": getattr(player, "outskirts_wizard_state", "NEW"),
            "outskirts_horde_defeated": getattr(player, "outskirts_horde_defeated", False),
            "outskirts_horde_defeated_list": _normalize_horde_list(
                getattr(player, "outskirts_horde_defeated_list", None),
                HORDE_COUNT),
            "outskirts_horde_chest_opened": legacy_chest_opened,
            "outskirts_horde_chest_opened_list": chest_opened_list,
            "outskirts_dual_rapier_given": getattr(player, "outskirts_dual_rapier_given", False),

            "has_seen_castle_intro": getattr(player, "has_seen_castle_intro", False),
            "has_seen_village_intro": getattr(player, "has_seen_village_intro", False),
            "has_seen_outskirts_intro": getattr(player, "has_seen_outskirts_intro", False),
            "has_seen_mystic_intro": getattr(player, "has_seen_mystic_intro", False),
            "has_seen_deeper_intro": getattr(player, "has_seen_deeper_intro", False),
            "has_seen_deeper_cutscene": getattr(
                player, "has_seen_deeper_cutscene", False),
            "has_seen_curse_intro": getattr(player, "has_seen_curse_intro", False),
            "has_seen_wizardoz_intro": getattr(player, "has_seen_wizardoz_intro", False),
            "wizardoz_reward_given": getattr(player, "wizardoz_reward_given", False),

            "has_seen_kitsune_intro": getattr(player, "has_seen_kitsune_intro", False),
            "has_seen_kitsune_dialogue": getattr(player, "has_seen_kitsune_dialogue", False),
            "kitsune_defeated": getattr(player, "kitsune_defeated", False),
            "has_seen_wizard3_intro": getattr(player, "has_seen_wizard3_intro", False),
            "wizard3_reward_given": getattr(player, "wizard3_reward_given", False),

            "has_seen_final_intro": getattr(player, "has_seen_final_intro", False),
            "final_horde_1_defeated": getattr(player, "final_horde_1_defeated", False),
            "final_horde_2_defeated": getattr(player, "final_horde_2_defeated", False),
            "gorgona_defeated": getattr(player, "gorgona_defeated", False),

            "deeper_devils_defeated": legacy_deeper_defeated,
            "deeper_devils_chest_opened": legacy_deeper_chest,
            "deeper_horde_defeated_list": deeper_defeated_list,
            "deeper_horde_chest_opened_list": deeper_chest_list,

            "position_valid": position_valid,
            "last_scene": getattr(player, "last_scene", "castle"),

            "game_completed": bool(getattr(player, "game_completed", False)),
        }

        if hasattr(player, "inventory") and player.inventory:
            inv = player.inventory
            if not hasattr(inv, "fixed_items") or inv.fixed_items is None:
                inv.fixed_items = [None] * 45
            inv.items = inv.fixed_items

            p_dict["inventory_items"] = _serialize_inventory(inv)
            p_dict["current_page"] = getattr(inv, "current_page", 0)

            for attr in EQUIP_ATTRS:
                item = getattr(inv, attr, None)
                p_dict[attr] = _serialize_equipment_slot(item)

        save_data["player"] = p_dict

    if wizard:
        save_data["wizard"] = {
            "dialogue_state": getattr(wizard, "dialogue_state", "PART_1")
        }

    save_save_data(slot_id, save_data)

    if player is not None:
        _restore_equipment(player)

    return save_data


def load_full_game_state(slot_id, player=None, wizard=None, orc=None):
    data = load_save_data(slot_id)
    if not data:
        return False

    version = data.get("save_version", 1)
    if version < SAVE_VERSION:
        print(f"[Save Manager] Loading v{version} save (current v{SAVE_VERSION}). "
              f"Missing fields default to False.")

    p_data = data.get("player", {})
    if player and p_data:
        if p_data.get("position_valid", False):
            player.x = p_data.get("x", player.x)
            player.y = p_data.get("y", player.y)
            player._position_loaded_from_save = True

        player.hp = p_data.get("hp", player.hp)
        if "max_hp" in p_data:
            player.max_hp = p_data["max_hp"]
        if "atk" in p_data:
            player.atk = p_data["atk"]
        if "defense" in p_data:
            player.defense = p_data["defense"]
        if "name" in p_data:
            player.name = p_data["name"]

        player.wizard_dialogue_state = p_data.get("wizard_dialogue_state", "PART_1")
        player.village_orc_defeated = p_data.get("village_orc_defeated", False)
        player.village_orc_reward_done = p_data.get("village_orc_reward_done", False)
        player.village_orc_chest_opened = p_data.get("village_orc_chest_opened", False)

        player.outskirts_wizard_state = p_data.get("outskirts_wizard_state", "NEW")
        player.outskirts_horde_defeated = p_data.get("outskirts_horde_defeated", False)
        player.outskirts_horde_defeated_list = _normalize_horde_list(
            p_data.get("outskirts_horde_defeated_list"), HORDE_COUNT)

        legacy_chest_opened = p_data.get("outskirts_horde_chest_opened", False)
        raw_chest_list = p_data.get("outskirts_horde_chest_opened_list")
        if raw_chest_list is None:
            if legacy_chest_opened:
                player.outskirts_horde_chest_opened_list = [True] * HORDE_COUNT
            else:
                player.outskirts_horde_chest_opened_list = [False] * HORDE_COUNT
        else:
            player.outskirts_horde_chest_opened_list = _normalize_horde_list(
                raw_chest_list, HORDE_COUNT)

        player.outskirts_horde_chest_opened = bool(
            legacy_chest_opened
            or all(player.outskirts_horde_chest_opened_list)
        )

        player.outskirts_dual_rapier_given = p_data.get("outskirts_dual_rapier_given", False)

        player.has_seen_castle_intro = p_data.get("has_seen_castle_intro", False)
        player.has_seen_village_intro = p_data.get("has_seen_village_intro", False)
        player.has_seen_outskirts_intro = p_data.get("has_seen_outskirts_intro", False)
        player.has_seen_mystic_intro = p_data.get("has_seen_mystic_intro", False)
        player.has_seen_deeper_intro = p_data.get("has_seen_deeper_intro", False)
        player.has_seen_deeper_cutscene = p_data.get(
            "has_seen_deeper_cutscene", False)
        player.has_seen_curse_intro = p_data.get("has_seen_curse_intro", False)
        player.has_seen_wizardoz_intro = p_data.get("has_seen_wizardoz_intro", False)
        player.wizardoz_reward_given = p_data.get("wizardoz_reward_given", False)

        player.has_seen_kitsune_intro = p_data.get("has_seen_kitsune_intro", False)
        player.has_seen_kitsune_dialogue = p_data.get("has_seen_kitsune_dialogue", False)
        player.kitsune_defeated = p_data.get("kitsune_defeated", False)
        player.has_seen_wizard3_intro = p_data.get("has_seen_wizard3_intro", False)
        player.wizard3_reward_given = p_data.get("wizard3_reward_given", False)

        player.has_seen_final_intro = p_data.get("has_seen_final_intro", False)
        player.final_horde_1_defeated = p_data.get("final_horde_1_defeated", False)
        player.final_horde_2_defeated = p_data.get("final_horde_2_defeated", False)
        player.gorgona_defeated = p_data.get("gorgona_defeated", False)

        legacy_deeper_defeated = p_data.get("deeper_devils_defeated", False)
        legacy_deeper_chest = p_data.get("deeper_devils_chest_opened", False)

        raw_defeated_list = p_data.get("deeper_horde_defeated_list")
        if raw_defeated_list is None:
            if legacy_deeper_defeated:
                player.deeper_horde_defeated_list = [True] * DEVIL_HORDE_COUNT
            else:
                player.deeper_horde_defeated_list = [False] * DEVIL_HORDE_COUNT
        else:
            player.deeper_horde_defeated_list = _normalize_horde_list(
                raw_defeated_list, DEVIL_HORDE_COUNT)

        raw_chest_list = p_data.get("deeper_horde_chest_opened_list")
        if raw_chest_list is None:
            if legacy_deeper_chest:
                player.deeper_horde_chest_opened_list = [True] * DEVIL_HORDE_COUNT
            else:
                player.deeper_horde_chest_opened_list = [False] * DEVIL_HORDE_COUNT
        else:
            player.deeper_horde_chest_opened_list = _normalize_horde_list(
                raw_chest_list, DEVIL_HORDE_COUNT)

        player.deeper_devils_defeated = bool(
            legacy_deeper_defeated
            or all(player.deeper_horde_defeated_list)
        )
        player.deeper_devils_chest_opened = bool(
            legacy_deeper_chest
            or all(player.deeper_horde_chest_opened_list)
        )

        player.last_scene = p_data.get("last_scene", "castle")

        player.game_completed = bool(p_data.get("game_completed", False))

        if hasattr(player, "inventory") and player.inventory:
            inv = player.inventory
            try:
                from classes.armory_item import ItemDatabase
            except ImportError:
                ItemDatabase = None

            saved_items = p_data.get("inventory_items", [])
            if saved_items and ItemDatabase is not None:
                _deserialize_inventory(saved_items, inv)

            inv.current_page = p_data.get("current_page", 0)

            for attr in EQUIP_ATTRS:
                if hasattr(inv, attr):
                    raw = p_data.get(attr)
                    setattr(inv, attr,
                            _deserialize_equipment_slot(raw, ItemDatabase))

            _reapply_equipment_passives(player)

    w_data = data.get("wizard", {})
    if wizard:
        if w_data:
            wizard.dialogue_state = w_data.get("dialogue_state", "PART_1")
        elif player:
            wizard.dialogue_state = getattr(player, "wizard_dialogue_state", "PART_1")

    orc_data = data.get("orc", {})
    if orc:
        if orc_data:
            orc.hp = orc_data.get("hp", orc.hp)
            if orc_data.get("defeated", False) or orc.hp <= 0:
                orc.hp = 0
                orc.is_defeated = True
    return True