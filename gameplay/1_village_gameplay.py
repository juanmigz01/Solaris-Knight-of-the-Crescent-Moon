import os
import sys
import importlib.util
import pygame

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

from battle.battle import run_battle
from battle.battle_func import play_warning_sfx
from player.player import Player
from enemies.tiny_orc import TinyOrc
from enemies.wizard import Wizard
from Modules.game_frame import GameFrame
from Modules.pause_menu import run_pause_menu
from Modules.stats_menu import run_stats_menu
from Modules.dialogue_box import run_dialogue
from Modules.sound_manager import game_manager
from Modules.chest import Chest
from Modules.particles import ParticleSystem
from Modules.quest import get_quests
from Modules.inv import (
    draw_inventory_and_equipment,
    handle_inventory_click,
    give_all_oz_reward_items,
    give_item_by_id,
    roll_chest_loot,
)
from Modules.cinematics import (
    get_cam_y, smooth_camera_y, play_zoom_intro,
)
from floor.castle import CastleFloor


try:
    from map.map import show_map as show_world_map
except ImportError as _wm_err:
    print(f"[Gameplay] world map import failed: {_wm_err}")
    show_world_map = None


VIEWPORT_SCREEN_RECT = pygame.Rect(320, 180, 1280, 720)
VIEWPORT_OFFSET = (320, 180)


def load_module_from_path(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


village_map = load_module_from_path(
    "map_1_village", os.path.join(PROJECT_ROOT, "map", "1_village.py"))
border = load_module_from_path(
    "map_border", os.path.join(PROJECT_ROOT, "map", "border.py"))

CELL_SIZE = village_map.CELL_SIZE
build_objects_from_grid = village_map.build_objects_from_grid
get_mob_spawns = village_map.get_mob_spawns

BORDER_WALLS = border.BORDER_WALLS
draw_borders = border.draw_borders

TRANSFER_ZONES      = village_map.TRANSFER_ZONES
SPAWN_ZONES         = village_map.SPAWN_ZONES
draw_transfer_zones = village_map.draw_transfer_zones
draw_spawn_zones    = village_map.draw_spawn_zones
zone_rect           = village_map.zone_rect
zone_spawn_point    = village_map.zone_spawn_point

PLAYER_HITBOX_CENTER_TO_FEET = village_map.PLAYER_HITBOX_CENTER_TO_FEET

WORLD_HEIGHT = village_map.MAP_ROWS * village_map.CELL_SIZE
VIEWPORT_H   = 720


def grid_to_pixel(col, row):
    return (col * CELL_SIZE, row * CELL_SIZE)


def _reload_character_sprites(player, wizard, orcs=None):
    player.load_animations()
    if wizard is not None:
        wizard.load_spritesheet_and_json(
            os.path.join("asset", "enemy_img", "Wizard", "Wizard.png"),
            os.path.join("asset", "enemy_img", "Wizard", "Wizard.json"),
        )
        if "idledown" in wizard.animations and "idle" not in wizard.animations:
            wizard.animations["idle"] = wizard.animations["idledown"]
        wizard.set_animation("idle")

    if orcs:
        for orc in orcs:
            if orc is None:
                continue
            orc.load_spritesheet_and_json(
                os.path.join("asset", "enemy_img", "tiny orc", "Tiny_Orc.png"),
                os.path.join("asset", "enemy_img", "tiny orc", "Tiny_Orc.json"),
            )
            orc.set_animation("idle")


def _spawn_mobs_from_grid():
    wizard = None
    orcs = []
    for mob_type, mx, my in get_mob_spawns():
        if mob_type == "wizard_oz":
            if wizard is None:
                wizard = Wizard(x=mx, y=my)
        elif mob_type == "tiny_orc":
            orc = TinyOrc(x=mx, y=my)
            orc.name = "Village Orc"
            orcs.append(orc)
    return wizard, orcs


def _get_orc_spawn_positions():
    positions = []
    for mob_type, mx, my in get_mob_spawns():
        if mob_type == "tiny_orc":
            positions.append((mx, my))
    return positions


def _orcs_active(wizard, player):
    if getattr(player, "village_orc_defeated", False):
        return False
    return True


def _apply_hitbox_setting(player, wizard, deco_objects, orcs=None, chests=None):
    on = getattr(game_manager, "hitbox_visible", False)
    player.show_hitbox = on
    if wizard:
        wizard.show_hitbox = on
    for obj in deco_objects:
        obj.show_hitbox = on
    if orcs:
        for orc in orcs:
            orc.show_hitbox = on
    if chests:
        for chest in chests:
            chest.show_hitbox = on


def run_test_gameplay(screen, slot_id=1, player=None,
                      entry_from="default", cinematic_intro=False):
    game_manager.play_ambient("zone_1.mp3", volume=0.45, fade_ms=800)

    clock = pygame.time.Clock()

    font_path = os.path.join(PROJECT_ROOT, "asset", "font", "TheGothicRite.otf")
    if os.path.exists(font_path):
        font_title = pygame.font.Font(font_path, 36)
        font_debug = pygame.font.Font(font_path, 20)
        font_cmd = pygame.font.Font(font_path, 18)
    else:
        font_title = pygame.font.SysFont("Georgia", 36)
        font_debug = pygame.font.SysFont("Georgia", 20)
        font_cmd = pygame.font.SysFont("Georgia", 18, bold=True)

    frame = GameFrame(font_large=font_title, font_small=font_debug)

    particles = ParticleSystem(
        world_w=1280, world_h=WORLD_HEIGHT,
        intensity=getattr(game_manager, "particle_intensity", "medium"),
        sprite_names=("mparticle",),
    )

    world_surface = pygame.Surface((1280, WORLD_HEIGHT))

    castle_floor = CastleFloor(viewport_width=1280, viewport_height=720)
    if hasattr(castle_floor, "current_index"):
        castle_floor.current_index = 0

    if player is None:
        player = Player(x=0, y=0, name="Solaris")

    wizard, orcs = _spawn_mobs_from_grid()
    if wizard is None:
        wizard = Wizard(x=11 * CELL_SIZE, y=8 * CELL_SIZE)

    wizard.dialogue_state = getattr(player, "wizard_dialogue_state", "COMPLETED")
    player.last_scene = "village"

    chests = []

    if getattr(player, "village_orc_defeated", False):
        for orc in orcs:
            orc.hp = 0
            orc.is_defeated = True

        if not getattr(player, "village_orc_chest_opened", False):
            for (mx, my) in _get_orc_spawn_positions():
                chests.append(Chest(x=mx, y=my,
                                    loot=roll_chest_loot(),
                                    label="Orc's Cache"))

    spawn_zone = SPAWN_ZONES.get(entry_from, SPAWN_ZONES["default"])
    spawn_x, spawn_y = zone_spawn_point(spawn_zone)

    if getattr(player, "_position_loaded_from_save", False):
        player._position_loaded_from_save = False
    else:
        player.x = spawn_x
        player.y = spawn_y

    player.spawn_x = spawn_x
    player.spawn_y = spawn_y
    player.can_move = True

    all_deco_objects = build_objects_from_grid()
    _apply_hitbox_setting(player, wizard, all_deco_objects, orcs, chests)

    player_name = getattr(player, "name", "Solaris")
    frame.title_text = f"{player_name}: Knight of the Crescent Moon"

    dialogue_meet_oz = [
        {"speaker": "Wizard Oz",
         "text": f"The orc, {player_name}. The one north-east of us."},
        {"speaker": "Wizard Oz",
         "text": "Slay it first. Then I will teach you what you need."},
    ]

    dialogue_tutorial = [
        {"speaker": "Wizard Oz",
         "text": f"One orc down. You carry yourself well, {player_name}."},
        {"speaker": "Wizard Oz",
         "text": "Now - let me teach you what you'll need."},
        {"speaker": "Wizard Oz",
         "text": "First - armor. Your body is one line of defense."},
        {"speaker": "TUTORIAL",
         "text": "[ARMOR]\nHelmet + Chestplate\nEach piece adds Defense and Elemental Defense."},
        {"speaker": "Wizard Oz",
         "text": "Second - the elements. Fire. Wind. Earth. Water."},
        {"speaker": "TUTORIAL",
         "text": "[ELEMENTAL WHEEL]\nFIRE  >  WIND  >  EARTH  >  WATER  >  FIRE"},
        {"speaker": "Wizard Oz",
         "text": "Fire burns Wind. Wind scatters Earth."},
        {"speaker": "Wizard Oz",
         "text": "Earth drinks Water. Water quenches Fire."},
        {"speaker": "Wizard Oz",
         "text": "Third - battle. Turn-based. You act, then your foe acts."},
        {"speaker": "TUTORIAL",
         "text": "[COMBAT]\nATTACK   - hit one enemy. Infinite uses.\nELEM     - hits all. Half dmg. 10 uses.\nBURST    - hits all. Full dmg. 5 uses.\nRUN AWAY - retreat (may fail)."},
        {"speaker": "Wizard Oz",
         "text": "And take these - three blades, one per element."},
        {"speaker": "SYSTEM",
         "text": "[Gained Earth Sword, Flaming Saber, and Water Spike!]"},
        {"speaker": "Wizard Oz",
         "text": "Equip two at once - a main hand and an off-hand."},
        {"speaker": "Wizard Oz",
         "text": "The blue slot drives your attack. The red slot feeds its passive."},
        {"speaker": "Wizard Oz",
         "text": "Now return to the castle. The road west is open."},
        {"speaker": player_name, "text": "Then I'll take it."},
    ]

    dialogue_completed = [
        {"speaker": "Wizard Oz",
         "text": f"Keep moving, {player_name}. Return to the castle and head west."},
    ]

    static_obstacles = []
    for obj in all_deco_objects:
        if hasattr(obj, "hitbox"):
            static_obstacles.append(obj.hitbox)
    if wizard:
        static_obstacles.append(wizard.hitbox)
    for wall_rect in BORDER_WALLS:
        static_obstacles.append(wall_rect)

    COLOR_GRASS = (80, 120, 60)
    COLOR_GOLD = (255, 215, 0)

    last_outline_state = getattr(game_manager, "outline_enabled", True)

    world_surface.fill(COLOR_GRASS)
    castle_floor.draw(world_surface)
    if WORLD_HEIGHT > 720:
        extra_h = WORLD_HEIGHT - 720
        tile = world_surface.subsurface(pygame.Rect(0, 0, 1280, extra_h)).copy()
        world_surface.blit(tile, (0, 720))

    for obj in sorted(all_deco_objects,
                      key=lambda o: o.hitbox.bottom if hasattr(o, "hitbox") else o.rect.bottom):
        obj.draw(world_surface)
    if wizard:
        wizard.draw(world_surface)

    if _orcs_active(wizard, player):
        for orc in orcs:
            if getattr(orc, "hp", 0) > 0:
                orc.draw(world_surface)

    for chest in chests:
        chest.draw(world_surface)
    player.draw(world_surface)
    draw_borders(world_surface)

    viewport = frame.get_viewport()
    viewport.blit(world_surface, (0, 0), pygame.Rect(0, 0, 1280, VIEWPORT_H))

    if entry_from == "castle" and not getattr(player, "has_seen_village_intro", False):
        play_zoom_intro(screen, frame, player, world_surface, WORLD_HEIGHT,
                        duration_sec=2.0, start_zoom=2.0, hold_peak_sec=0.2,
                        particles=particles)
        player.has_seen_village_intro = True

    running = True
    gameplay_signal = None
    smooth_cam_y = None

    while running:
        dt = clock.tick(60) / 1000.0
        dt = min(dt, 0.05)

        current_particles = getattr(game_manager, "particle_intensity", "medium")
        if current_particles != particles.intensity:
            particles.set_intensity(current_particles)
        particles.update(dt)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                gameplay_signal = "QUIT_TO_MENU"

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                handle_inventory_click(event.pos, player, frame)

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pause_result = run_pause_menu(
                        screen, frame, slot_id=slot_id,
                        player=player, wizard=wizard,
                        orc=None, enemies=orcs)
                    if pause_result == "QUIT_TO_MENU":
                        running = False
                        gameplay_signal = "QUIT_TO_MENU"

                elif event.key == pygame.K_z:
                    game_manager.cycle_zoom()

                elif event.key == pygame.K_m:
                    if show_world_map is not None:
                        show_world_map(screen, player, player.last_scene)

                elif event.key == pygame.K_e:
                    handled = False
                    for chest in chests:
                        if chest.can_interact(player):
                            chest.open()
                            chest.looted = True
                            bg_snapshot = screen.copy()

                            names = []
                            for item_id in chest.loot:
                                item = give_item_by_id(player, item_id)
                                if item:
                                    names.append(item.name)

                            player.village_orc_chest_opened = True

                            if names:
                                msg = [{"speaker": "SYSTEM",
                                        "text": "You found: " + ", ".join(names) + "!"}]
                            else:
                                msg = [{"speaker": "SYSTEM",
                                        "text": "The chest is empty."}]
                            run_dialogue(screen, msg, bg_snapshot)
                            handled = True
                            break

                    if not handled and wizard and wizard.can_interact(player):
                        bg_snapshot = screen.copy()
                        any_alive = any(getattr(o, "hp", 0) > 0 for o in orcs)
                        reward_done = getattr(player, "village_orc_reward_done", False)

                        if reward_done:
                            run_dialogue(screen, dialogue_completed, bg_snapshot)
                        elif any_alive:
                            run_dialogue(screen, dialogue_meet_oz, bg_snapshot)
                        else:
                            give_all_oz_reward_items(player)
                            player.village_orc_reward_done = True
                            player.wizard_dialogue_state = "COMPLETED"
                            run_dialogue(screen, dialogue_tutorial, bg_snapshot)

        current_outline_state = getattr(game_manager, "outline_enabled", True)
        if current_outline_state != last_outline_state:
            last_outline_state = current_outline_state
            _reload_character_sprites(player, wizard, orcs)

        _apply_hitbox_setting(player, wizard, all_deco_objects, orcs, chests)

        chests_to_remove = []
        for chest in chests:
            chest.update(dt)
            if getattr(chest, "looted", False) and chest.is_opened():
                chests_to_remove.append(chest)
        for chest in chests_to_remove:
            chests.remove(chest)

        orcs_active = _orcs_active(wizard, player)

        frame_obstacles = list(static_obstacles)
        for chest in chests:
            if not chest.is_opened():
                frame_obstacles.append(chest.get_hitbox())

        player.update(viewport_width=1280, viewport_height=WORLD_HEIGHT,
                      obstacles=frame_obstacles)
        if wizard:
            wizard.update(delta_time=dt, player=player)

        player_hitbox = player.get_hitbox()

        if orcs_active:
            for orc in orcs:
                if getattr(orc, "hp", 0) <= 0:
                    continue

                orc.update(delta_time=dt, player=player)

                in_range = player_hitbox.colliderect(orc.hitbox)
                detected = getattr(orc, "is_detected", False)

                if (in_range or detected) and not getattr(orc, "flee_cooldown", False):
                    play_warning_sfx()

                    battle_result = run_battle(screen, player, orc, slot_id=slot_id)

                    if battle_result == "VICTORY":
                        orc.hp = 0
                        orc.is_defeated = True
                        player.village_orc_defeated = True

                        if not getattr(player, "village_orc_chest_opened", False):
                            chests.append(Chest(x=orc.x, y=orc.y,
                                                loot=roll_chest_loot(),
                                                label="Orc's Cache"))

                        if not getattr(player, "village_orc_reward_done", False):
                            bg_post = screen.copy()
                            msg = [{"speaker": "SYSTEM",
                                    "text": "[The Orc is defeated! Return to Wizard Oz.]"}]
                            run_dialogue(screen, msg, bg_post)

                    elif battle_result == "DEFEAT":
                        pass

                    if hasattr(orc, "reset_battle_trigger"):
                        orc.reset_battle_trigger()

        player_center = (player.x, player.y - PLAYER_HITBOX_CENTER_TO_FEET)
        for zone_name, zone_data in TRANSFER_ZONES.items():
            zr = zone_rect(zone_data)
            if zr.collidepoint(player_center):
                running = False
                gameplay_signal = zone_data["target"]
                break

        world_surface.fill(COLOR_GRASS)
        castle_floor.draw(world_surface)

        if WORLD_HEIGHT > 720:
            extra_h = WORLD_HEIGHT - 720
            tile = world_surface.subsurface(pygame.Rect(0, 0, 1280, extra_h)).copy()
            world_surface.blit(tile, (0, 720))

        draw_queue = []
        for obj in all_deco_objects:
            draw_y = obj.hitbox.bottom if hasattr(obj, "hitbox") else obj.rect.bottom
            if (hasattr(obj, "layer_hitbox") and obj.layer_hitbox
                    and obj.layer_hitbox.colliderect(player_hitbox)):
                draw_y = player.y + 9999
            draw_queue.append((draw_y, obj))

        if wizard:
            draw_queue.append((wizard.rect.bottom, wizard))
        if orcs_active:
            for orc in orcs:
                if getattr(orc, "hp", 0) > 0:
                    draw_queue.append((orc.rect.bottom, orc))
        for chest in chests:
            draw_queue.append((chest.rect.bottom, chest))
        draw_queue.append((player.y, player))
        draw_queue.sort(key=lambda item: item[0])

        for _, entity in draw_queue:
            entity.draw(world_surface)

        draw_borders(world_surface)
        zones_on = getattr(game_manager, "zones_visible", False)
        draw_transfer_zones(world_surface, force_show=zones_on)
        draw_spawn_zones(world_surface, force_show=zones_on)

        zoom = float(getattr(game_manager, "zoom_level", 1.0) or 1.0)
        target_cam_y = get_cam_y(player.y, zoom, WORLD_HEIGHT, VIEWPORT_H)

        if zoom <= 1.0:
            smooth_cam_y = 0.0
        else:
            smooth_cam_y = smooth_camera_y(smooth_cam_y, target_cam_y)

        cam_y = smooth_cam_y
        view_rect = pygame.Rect(0, int(cam_y), 1280, VIEWPORT_H)

        particles.draw(world_surface, view_rect=view_rect)

        viewport = frame.get_viewport()
        viewport.blit(world_surface, (0, 0), view_rect)

        frame.zoom_focus = (int(player.x), int(player.y - cam_y))
        frame.quests = get_quests(player)
        frame_action = frame.draw(screen)

        if frame_action == "PAUSE":
            pause_result = run_pause_menu(
                screen, frame, slot_id=slot_id,
                player=player, wizard=wizard,
                orc=None, enemies=orcs)
            if pause_result == "QUIT_TO_MENU":
                running = False
                gameplay_signal = "QUIT_TO_MENU"
        elif frame_action == "STATS":
            run_stats_menu(screen, frame, player)

        prompt_drawn = False
        for chest in chests:
            if chest.can_interact(player):
                cmd_box = pygame.Rect(40, 250, 240, 46)
                pygame.draw.rect(screen, (20, 25, 35), cmd_box, border_radius=6)
                pygame.draw.rect(screen, COLOR_GOLD, cmd_box, width=2, border_radius=6)
                prompt_surf = font_cmd.render("[E] Open Chest", True, COLOR_GOLD)
                screen.blit(prompt_surf, prompt_surf.get_rect(center=cmd_box.center))
                prompt_drawn = True
                break

        if not prompt_drawn and wizard and wizard.can_interact(player):
            cmd_box = pygame.Rect(40, 250, 240, 46)
            pygame.draw.rect(screen, (20, 25, 35), cmd_box, border_radius=6)
            pygame.draw.rect(screen, COLOR_GOLD, cmd_box, width=2, border_radius=6)
            prompt_surf = font_cmd.render("[E] Talk to Wizard Oz", True, COLOR_GOLD)
            screen.blit(prompt_surf, prompt_surf.get_rect(center=cmd_box.center))

        draw_inventory_and_equipment(screen, player, frame)
        pygame.display.flip()

    return gameplay_signal