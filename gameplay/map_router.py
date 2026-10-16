
import os
import importlib.util

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


_run_castle_gameplay = None
_run_village_gameplay = None
_run_outskirts_gameplay = None
_run_mystic_gameplay = None
_run_deeper_gameplay = None
_run_curse_gameplay = None
_run_wizardoz_gameplay = None
_run_kitsune_gameplay = None
_run_wizard3_gameplay = None
_run_final_gameplay = None


def _reset_player_movement_sfx(player):

    if player is None:
        return
    try:
        player.walk_sfx_name   = "walk.mp3"
        player.run_sfx_name    = "running.mp3"
        player.walk_sfx_volume = 0.40
        player.run_sfx_volume  = 1.00
    except Exception:
        pass

    try:
        from Modules.sound_manager import game_manager
        game_manager.stop_sfx("walk")
        game_manager.stop_sfx("run")
    except Exception:
        pass


def _load_gameplay_module(module_name, relative_path):
    full_path = os.path.join(PROJECT_ROOT, relative_path)
    spec = importlib.util.spec_from_file_location(module_name, full_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _ensure_modules_loaded():
    global _run_castle_gameplay, _run_village_gameplay, _run_outskirts_gameplay
    global _run_mystic_gameplay, _run_deeper_gameplay, _run_curse_gameplay
    global _run_wizardoz_gameplay, _run_kitsune_gameplay, _run_wizard3_gameplay
    global _run_final_gameplay

    if _run_castle_gameplay is None:
        m = _load_gameplay_module("gameplay_1_castle",
                                  "gameplay/1_gameplay.py")
        _run_castle_gameplay = m.run_test_gameplay

    if _run_village_gameplay is None:
        m = _load_gameplay_module("gameplay_1_village",
                                  "gameplay/1_village_gameplay.py")
        _run_village_gameplay = m.run_test_gameplay

    if _run_outskirts_gameplay is None:
        m = _load_gameplay_module("gameplay_1_outskirts",
                                  "gameplay/1_outskirts_gameplay.py")
        _run_outskirts_gameplay = m.run_test_gameplay

    if _run_mystic_gameplay is None:
        m = _load_gameplay_module("gameplay_2_mystic",
                                  "gameplay/2_mystic_gameplay.py")
        _run_mystic_gameplay = m.run_test_gameplay

    if _run_deeper_gameplay is None:
        m = _load_gameplay_module("gameplay_2_deeper",
                                  "gameplay/2_deeper_gameplay.py")
        _run_deeper_gameplay = m.run_test_gameplay

    if _run_curse_gameplay is None:
        m = _load_gameplay_module("gameplay_2_curse",
                                  "gameplay/2_curse_gameplay.py")
        _run_curse_gameplay = m.run_test_gameplay

    if _run_wizardoz_gameplay is None:
        m = _load_gameplay_module("gameplay_2_wizardoz",
                                  "gameplay/2_wizardoz_gameplay.py")
        _run_wizardoz_gameplay = m.run_test_gameplay

    if _run_kitsune_gameplay is None:
        m = _load_gameplay_module("gameplay_2_kitsune",
                                  "gameplay/2_kitsune_gameplay.py")
        _run_kitsune_gameplay = m.run_test_gameplay

    if _run_wizard3_gameplay is None:
        m = _load_gameplay_module("gameplay_3_wizard",
                                  "gameplay/3_wizard_gameplay.py")
        _run_wizard3_gameplay = m.run_test_gameplay

    if _run_final_gameplay is None:
        m = _load_gameplay_module("gameplay_3_final",
                                  "gameplay/3_final_gameplay.py")
        _run_final_gameplay = m.run_test_gameplay


def run_gameplay_with_map_switching(screen, slot_id=1, player=None,
                                    cinematic_intro=False):
    _ensure_modules_loaded()

    start_scene = "castle"
    if player is not None:
        try:
            from Modules.save_manager import load_full_game_state
            load_full_game_state(slot_id, player=player, wizard=None, orc=None)
            start_scene = getattr(player, "last_scene", "castle")
        except Exception as e:
            print(f"[MAP ROUTER] load_full_game_state failed: {e}")

    if start_scene not in ("castle", "village", "outskirts",
                           "mystic", "deeper", "curse", "wizardoz",
                           "kitsune", "wizard3", "final"):
        start_scene = "castle"

    _reset_player_movement_sfx(player)

    if start_scene == "village":
        print("[MAP ROUTER] starting village")
        result = _run_village_gameplay(
            screen, slot_id=slot_id, player=player,
            entry_from="castle", cinematic_intro=False,
        )
    elif start_scene == "outskirts":
        print("[MAP ROUTER] starting outskirts")
        result = _run_outskirts_gameplay(
            screen, slot_id=slot_id, player=player,
            entry_from="castle", cinematic_intro=False,
        )
    elif start_scene == "mystic":
        print("[MAP ROUTER] starting mystic")
        result = _run_mystic_gameplay(
            screen, slot_id=slot_id, player=player,
            entry_from="outskirts", cinematic_intro=False,
        )
    elif start_scene == "deeper":
        print("[MAP ROUTER] starting deeper forest")
        result = _run_deeper_gameplay(
            screen, slot_id=slot_id, player=player,
            entry_from="mystic", cinematic_intro=False,
        )
    elif start_scene == "curse":
        print("[MAP ROUTER] starting curse zone")
        result = _run_curse_gameplay(
            screen, slot_id=slot_id, player=player,
            entry_from="deeper", cinematic_intro=False,
        )
    elif start_scene == "wizardoz":
        print("[MAP ROUTER] starting wizard oz clearing")
        result = _run_wizardoz_gameplay(
            screen, slot_id=slot_id, player=player,
            entry_from="curse", cinematic_intro=False,
        )
    elif start_scene == "kitsune":
        print("[MAP ROUTER] starting kitsune shrine")
        result = _run_kitsune_gameplay(
            screen, slot_id=slot_id, player=player,
            entry_from="wizardoz", cinematic_intro=False,
        )
    elif start_scene == "wizard3":
        print("[MAP ROUTER] starting wizard oz's workshop")
        result = _run_wizard3_gameplay(
            screen, slot_id=slot_id, player=player,
            entry_from="kitsune", cinematic_intro=False,
        )
    elif start_scene == "final":
        print("[MAP ROUTER] starting gorgona's throne")
        result = _run_final_gameplay(
            screen, slot_id=slot_id, player=player,
            entry_from="wizard3", cinematic_intro=False,
        )
    else:
        print("[MAP ROUTER] starting castle")
        result = _run_castle_gameplay(
            screen, slot_id=slot_id, player=player,
            entry_from="default", cinematic_intro=cinematic_intro,
        )

    print(f"[MAP ROUTER] {start_scene} returned: {result!r}")

    while result in ("GO_TO_VILLAGE", "GO_TO_CASTLE",
                     "GO_TO_OUTSKIRTS", "GO_TO_MYSTIC",
                     "GO_TO_DEEPER_MYSTIC", "GO_TO_CURSE",
                     "GO_TO_WIZARDOZ", "GO_TO_KITSUNE",
                     "GO_TO_WIZARD3", "GO_TO_FINAL"):

        _reset_player_movement_sfx(player)

        if result == "GO_TO_VILLAGE":
            print("[MAP ROUTER] -> village")
            result = _run_village_gameplay(
                screen, slot_id=slot_id, player=player,
                entry_from="castle", cinematic_intro=False,
            )

        elif result == "GO_TO_CASTLE":
            origin = getattr(player, "last_scene", "village")
            if origin not in ("village", "outskirts"):
                origin = "village"
            print(f"[MAP ROUTER] -> castle (entry_from='{origin}')")
            result = _run_castle_gameplay(
                screen, slot_id=slot_id, player=player,
                entry_from=origin, cinematic_intro=False,
            )

        elif result == "GO_TO_OUTSKIRTS":
            origin = getattr(player, "last_scene", "castle")
            if origin not in ("castle", "mystic"):
                origin = "castle"
            print(f"[MAP ROUTER] -> outskirts (entry_from='{origin}')")
            result = _run_outskirts_gameplay(
                screen, slot_id=slot_id, player=player,
                entry_from=origin, cinematic_intro=False,
            )

        elif result == "GO_TO_MYSTIC":
            origin = getattr(player, "last_scene", "outskirts")
            if origin not in ("outskirts", "deeper"):
                origin = "outskirts"
            print(f"[MAP ROUTER] -> mystic (entry_from='{origin}')")
            result = _run_mystic_gameplay(
                screen, slot_id=slot_id, player=player,
                entry_from=origin, cinematic_intro=False,
            )

        elif result == "GO_TO_DEEPER_MYSTIC":
            origin = getattr(player, "last_scene", "mystic")
            if origin not in ("mystic", "curse"):
                origin = "mystic"
            print(f"[MAP ROUTER] -> deeper forest (entry_from='{origin}')")
            result = _run_deeper_gameplay(
                screen, slot_id=slot_id, player=player,
                entry_from=origin, cinematic_intro=False,
            )

        elif result == "GO_TO_CURSE":
            origin = getattr(player, "last_scene", "deeper")
            if origin not in ("deeper", "wizardoz"):
                origin = "deeper"
            print(f"[MAP ROUTER] -> curse zone (entry_from='{origin}')")
            result = _run_curse_gameplay(
                screen, slot_id=slot_id, player=player,
                entry_from=origin, cinematic_intro=False,
            )

        elif result == "GO_TO_WIZARDOZ":
            origin = getattr(player, "last_scene", "curse")
            if origin not in ("curse", "kitsune"):
                origin = "curse"
            print(f"[MAP ROUTER] -> wizard oz clearing (entry_from='{origin}')")
            result = _run_wizardoz_gameplay(
                screen, slot_id=slot_id, player=player,
                entry_from=origin, cinematic_intro=False,
            )

        elif result == "GO_TO_KITSUNE":
            origin = getattr(player, "last_scene", "wizardoz")
            if origin not in ("wizardoz", "wizard3"):
                origin = "wizardoz"
            print(f"[MAP ROUTER] -> kitsune shrine (entry_from='{origin}')")
            result = _run_kitsune_gameplay(
                screen, slot_id=slot_id, player=player,
                entry_from=origin, cinematic_intro=False,
            )

        elif result == "GO_TO_WIZARD3":
            origin = getattr(player, "last_scene", "kitsune")
            if origin not in ("kitsune", "final"):
                origin = "kitsune"
            print(f"[MAP ROUTER] -> wizard oz's workshop (entry_from='{origin}')")
            result = _run_wizard3_gameplay(
                screen, slot_id=slot_id, player=player,
                entry_from=origin, cinematic_intro=False,
            )

        elif result == "GO_TO_FINAL":
            print("[MAP ROUTER] -> gorgona's throne (entry_from='wizard3')")
            result = _run_final_gameplay(
                screen, slot_id=slot_id, player=player,
                entry_from="wizard3", cinematic_intro=False,
            )

    return result