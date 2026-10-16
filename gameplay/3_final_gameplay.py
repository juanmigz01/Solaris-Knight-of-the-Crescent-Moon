import os
import sys
import math
import importlib.util
import pygame

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

from player.player import Player
from Modules.game_frame import GameFrame
from Modules.pause_menu import run_pause_menu
from Modules.stats_menu import run_stats_menu
from Modules.sound_manager import game_manager
from Modules.particles import (
    ParticleBundle, FireflySystem, RedFallSystem, make_midnight_overlay,
)
from Modules.mystic_effects import RainbowOutlinePulse
from Modules.quest import get_quests
from Modules.inv import (
    draw_inventory_and_equipment,
    handle_inventory_click,
)
from Modules.cinematics import (
    get_cam_y, smooth_camera_y, play_zoom_intro,
)
from floor.catacombs import CatacombsFloor

from enemies.tiny_devil import TinyDevil
from enemies.gorgona import Gorgona
from battle.multi_battle import run_multi_battle
from battle.final_battle import run_final_battle, _play_letterbox_dialogue
from battle.battle_func import play_warning_sfx

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


final_map = load_module_from_path(
    "map_3_final", os.path.join(PROJECT_ROOT, "map", "3_final.py"))
border = load_module_from_path(
    "map_border", os.path.join(PROJECT_ROOT, "map", "border.py"))

CELL_SIZE = final_map.CELL_SIZE
build_objects_from_grid = final_map.build_objects_from_grid
get_mob_spawns = final_map.get_mob_spawns

BORDER_WALLS = border.BORDER_WALLS
draw_borders = border.draw_borders

TRANSFER_ZONES      = final_map.TRANSFER_ZONES
LOCKED_DOORS        = final_map.LOCKED_DOORS
SPAWN_ZONES         = final_map.SPAWN_ZONES
draw_transfer_zones = final_map.draw_transfer_zones
draw_spawn_zones    = final_map.draw_spawn_zones
zone_rect           = final_map.zone_rect
zone_spawn_point    = final_map.zone_spawn_point

GORGONA_POS                  = final_map.GORGONA_POS
GORGONA_TRIGGER_RADIUS       = final_map.GORGONA_TRIGGER_RADIUS
GORGONA_FLEE_RELEASE_RADIUS  = final_map.GORGONA_FLEE_RELEASE_RADIUS

PLAYER_HITBOX_CENTER_TO_FEET = final_map.PLAYER_HITBOX_CENTER_TO_FEET

WORLD_HEIGHT = final_map.MAP_ROWS * final_map.CELL_SIZE
VIEWPORT_H   = 720

ZONE_3_WALK_SFX    = "zone_3_walk.mp3"
ZONE_3_RUN_SFX     = "zone_3_run.mp3"
ZONE_3_WALK_VOLUME = 0.40
ZONE_3_RUN_VOLUME  = 1.00


def _stop_player_move_sfx():
    try:
        game_manager.stop_sfx("walk")
        game_manager.stop_sfx("run")
    except Exception:
        pass


def _play_intro_cutscene(screen, player_name):
    lines = [
        ("NARRATOR", "The trees end. A black throne rises from the earth."),
        ("NARRATOR", "At its peak sits a shape wreathed in dim light."),
        ("Gorgona", "So... the little knight."),
        ("Gorgona", "You've come at last. I wondered how long it would take."),
        (player_name, "Gorgona."),
        (player_name, "Where is Lunaire?"),
        ("Gorgona", "Lunaire? Lunaire, Lunaire..."),
        ("Gorgona", "You speak her name like it belongs to you."),
        (player_name, "It does."),
        ("Gorgona", "Hahaha... how charming."),
        ("Gorgona", "The princess is MINE now. Her beauty feeds my eternity."),
        ("Gorgona", "You are far too late, boy."),
        (player_name, "Then I'll tear her out of you."),
        ("Gorgona", "Try."),
        ("Gorgona", "But first - my pets will tenderize you."),
        ("NARRATOR", "Two hordes of tiny devils crawl out of the dark."),
    ]
    _play_letterbox_dialogue(screen, lines)


def _play_gorgona_arrival_cutscene(screen, player_name):
    lines = [
        ("NARRATOR", "The last of her pets falls."),
        ("NARRATOR", "And then - SHE stirs."),
        ("Gorgona", "Enough of this."),
        ("Gorgona", "Very well, little knight."),
        ("Gorgona", "Come. Meet your Empress."),
        ("NARRATOR", "Gorgona descends from her throne. Her gaze burns through you."),
        ("Gorgona", f"Let me see the face of the boy who thinks he can save a princess."),
    ]
    _play_letterbox_dialogue(screen, lines)


def _play_pre_battle_cutscene(screen, player_name):
    lines = [
        ("NARRATOR", "You step forward."),
        ("Gorgona", "Fool. Do you truly believe you can-"),
        (player_name, "I don't need to believe. I need to END you."),
        ("Gorgona", "...then come, knight."),
        ("Gorgona", "Let us see how long you last."),
    ]
    _play_letterbox_dialogue(screen, lines)


def _build_final_horde():
    return [
        {"enemies": [TinyDevil(x=0, y=0) for _ in range(3)], "attackers": 2},
        {"enemies": [TinyDevil(x=0, y=0) for _ in range(3)], "attackers": 2},
    ]


def run_test_gameplay(screen, slot_id=1, player=None,
                      entry_from="default", cinematic_intro=False):
    game_manager.play_ambient("zone_3.mp3", volume=0.25, fade_ms=800)

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

    intensity = getattr(game_manager, "particle_intensity", "medium")

    fireflies = FireflySystem(
        world_w=1280, world_h=WORLD_HEIGHT,
        intensity=intensity,
    )
    red_fall = RedFallSystem(
        world_w=1280, world_h=WORLD_HEIGHT,
        intensity=intensity,
    )
    particles = ParticleBundle(fireflies, red_fall)

    outline_pulse = RainbowOutlinePulse(cycle_sec=12.0)

    MIDNIGHT_OVERLAY = make_midnight_overlay(1280, 720)

    world_surface = pygame.Surface((1280, WORLD_HEIGHT))

    floor = CatacombsFloor(viewport_width=1280, viewport_height=720)
    if getattr(floor, "floor_images", None):
        floor.current_floor = floor.floor_images[0]

    if player is None:
        player = Player(x=0, y=0, name="Solaris")

    player.last_scene = "final"

    player.walk_sfx_name   = ZONE_3_WALK_SFX
    player.run_sfx_name    = ZONE_3_RUN_SFX
    player.walk_sfx_volume = ZONE_3_WALK_VOLUME
    player.run_sfx_volume  = ZONE_3_RUN_VOLUME

    for flag in ("has_seen_final_intro",
                 "final_horde_1_defeated",
                 "final_horde_2_defeated",
                 "gorgona_defeated"):
        if not hasattr(player, flag):
            setattr(player, flag, False)
    if not hasattr(player, "_gorgona_flee_cooldown"):
        player._gorgona_flee_cooldown = False
    if not hasattr(player, "game_completed"):
        player.game_completed = False

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

    on = getattr(game_manager, "hitbox_visible", False)
    player.show_hitbox = on
    for obj in all_deco_objects:
        obj.show_hitbox = on

    player_name = getattr(player, "name", "Solaris")
    frame.title_text = f"{player_name}: Knight of the Crescent Moon"

    static_obstacles = []
    for obj in all_deco_objects:
        if hasattr(obj, "hitbox"):
            static_obstacles.append(obj.hitbox)
    for wall_rect in BORDER_WALLS:
        static_obstacles.append(wall_rect)

    COLOR_GRASS = (30, 25, 45)
    COLOR_GOLD = (255, 215, 0)
    COLOR_WARN = (255, 170, 90)

    warn_timer = 0.0
    warn_message = "..."

    horde_positions = []
    for mob_type, mx, my in get_mob_spawns():
        if mob_type == "tiny_devil":
            horde_positions.append((mx, my))

    while len(horde_positions) < 2:
        horde_positions.append((0, 0))
    horde_positions = horde_positions[:2]

    horde_markers = {}
    for idx in range(2):
        already_defeated = (
            (idx == 0 and player.final_horde_1_defeated) or
            (idx == 1 and player.final_horde_2_defeated)
        )
        if already_defeated:
            continue
        mx, my = horde_positions[idx]
        marker = TinyDevil(x=mx, y=my)
        marker.show_hitbox = on
        horde_markers[idx] = marker

    gorgona = None
    if (player.final_horde_1_defeated and player.final_horde_2_defeated
            and not player.gorgona_defeated):
        gorgona = Gorgona(x=GORGONA_POS[0], y=GORGONA_POS[1], scale=1.0)
        gorgona.show_hitbox = on

    def _draw_world():
        world_surface.fill(COLOR_GRASS)
        floor.draw(world_surface)
        if WORLD_HEIGHT > 720:
            extra_h = WORLD_HEIGHT - 720
            tile = world_surface.subsurface(
                pygame.Rect(0, 0, 1280, extra_h)).copy()
            world_surface.blit(tile, (0, 720))

    def _populate_world():
        player_hitbox = player.get_hitbox()
        draw_queue = []
        for obj in all_deco_objects:
            draw_y = (obj.hitbox.bottom if hasattr(obj, "hitbox")
                      else obj.rect.bottom)
            if (hasattr(obj, "layer_hitbox") and obj.layer_hitbox
                    and obj.layer_hitbox.colliderect(player_hitbox)):
                draw_y = player.y + 9999
            draw_queue.append((draw_y, obj))

        for marker in horde_markers.values():
            draw_queue.append((marker.rect.bottom, marker))
        if gorgona is not None:
            draw_queue.append((gorgona.rect.bottom, gorgona))

        draw_queue.append((player.y, player))
        draw_queue.sort(key=lambda item: item[0])

        for _, entity in draw_queue:
            entity.draw(world_surface, **outline_pulse.draw_kwargs(entity))

        draw_borders(world_surface)
        zones_on = getattr(game_manager, "zones_visible", False)
        draw_transfer_zones(world_surface, force_show=zones_on)
        draw_spawn_zones(world_surface, force_show=zones_on)

    if not getattr(player, "has_seen_final_intro", False):
        _draw_world()
        _populate_world()
        viewport = frame.get_viewport()
        viewport.blit(world_surface, (0, 0),
                      pygame.Rect(0, 0, 1280, VIEWPORT_H))
        pygame.display.flip()

        _stop_player_move_sfx()

        _play_intro_cutscene(screen, player_name)
        player.has_seen_final_intro = True

        _draw_world(); _populate_world()
        viewport = frame.get_viewport()
        viewport.blit(world_surface, (0, 0),
                      pygame.Rect(0, 0, 1280, VIEWPORT_H))
        play_zoom_intro(screen, frame, player, world_surface, WORLD_HEIGHT,
                        duration_sec=2.0, start_zoom=2.2, hold_peak_sec=0.2,
                        particles=particles)

    running = True
    gameplay_signal = None
    smooth_cam_y = None

    while running:
        dt = clock.tick(60) / 1000.0
        dt = min(dt, 0.05)

        if warn_timer > 0:
            warn_timer = max(0.0, warn_timer - dt)

        current_particles = getattr(game_manager, "particle_intensity", "medium")
        if current_particles != particles.intensity:
            particles.set_intensity(current_particles)

        particles.update(dt)
        outline_pulse.update(dt)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                gameplay_signal = "QUIT_TO_MENU"

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                handle_inventory_click(event.pos, player, frame)

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    _stop_player_move_sfx()
                    pause_result = run_pause_menu(
                        screen, frame, slot_id=slot_id,
                        player=player, wizard=None,
                        orc=None, enemies=None)
                    if pause_result == "QUIT_TO_MENU":
                        running = False
                        gameplay_signal = "QUIT_TO_MENU"

                elif event.key == pygame.K_z:
                    game_manager.cycle_zoom()

                elif event.key == pygame.K_m:
                    if show_world_map is not None:
                        show_world_map(screen, player, player.last_scene)

        player.update(viewport_width=1280, viewport_height=WORLD_HEIGHT,
                      obstacles=static_obstacles)

        for marker in horde_markers.values():
            marker.update(delta_time=dt, player=player)

        if gorgona is not None:
            gorgona.update(delta_time=dt, player=player)

        triggered_idx = None
        for idx, marker in horde_markers.items():
            if marker.triggered_battle:
                triggered_idx = idx
                break

        if triggered_idx is not None:
            marker = horde_markers[triggered_idx]
            marker.triggered_battle = False

            _stop_player_move_sfx()

            play_warning_sfx()

            waves = _build_final_horde()
            result = run_multi_battle(screen, player, waves, slot_id=slot_id)

            if result == "VICTORY":
                if triggered_idx == 0:
                    player.final_horde_1_defeated = True
                else:
                    player.final_horde_2_defeated = True
                del horde_markers[triggered_idx]

                if (player.final_horde_1_defeated
                        and player.final_horde_2_defeated
                        and gorgona is None
                        and not player.gorgona_defeated):
                    _draw_world(); _populate_world()
                    viewport = frame.get_viewport()
                    viewport.blit(world_surface, (0, 0),
                                  pygame.Rect(0, 0, 1280, VIEWPORT_H))
                    pygame.display.flip()

                    _stop_player_move_sfx()

                    _play_gorgona_arrival_cutscene(screen, player_name)
                    gorgona = Gorgona(x=GORGONA_POS[0], y=GORGONA_POS[1],
                                      scale=1.0)
                    gorgona.show_hitbox = on

            elif result == "FLED":
                marker.start_flee_cooldown()

        if gorgona is not None and not player.gorgona_defeated:
            dx = player.x - gorgona.x
            dy = player.y - gorgona.y
            dist = math.hypot(dx, dy)

            if getattr(player, "_gorgona_flee_cooldown", False):
                if dist > GORGONA_FLEE_RELEASE_RADIUS:
                    player._gorgona_flee_cooldown = False
            elif dist < GORGONA_TRIGGER_RADIUS:
                _draw_world(); _populate_world()
                viewport = frame.get_viewport()
                viewport.blit(world_surface, (0, 0),
                              pygame.Rect(0, 0, 1280, VIEWPORT_H))
                pygame.display.flip()

                _stop_player_move_sfx()

                _play_pre_battle_cutscene(screen, player_name)

                play_warning_sfx()

                result = run_final_battle(screen, player, slot_id=slot_id)

                if result in ("VICTORY_NEW", "BAD_ENDING_NEW"):
                    player.gorgona_defeated = (result == "VICTORY_NEW")
                    player.game_completed = True

                    try:
                        from Modules.save_manager import save_full_game_state
                        save_full_game_state(slot_id, player=player,
                                             position_valid=True)
                    except Exception as e:
                        print(f"[Final] autosave failed: {e}")

                    gorgona = None
                    running = False
                    gameplay_signal = "QUIT_TO_MENU"

                elif result in ("VICTORY_RESTART", "BAD_ENDING_RESTART"):
                    try:
                        from Modules.save_manager import delete_save_data
                        delete_save_data(slot_id)
                    except Exception as e:
                        print(f"[Final] delete_save_data failed: {e}")

                    try:
                        player.game_completed = False
                    except Exception:
                        pass

                    try:
                        from Fmain_menu.prologue import run_prologue
                        run_prologue(screen, slot_id)
                    except Exception as e:
                        print(f"[Final] restart -> prologue failed: {e}")

                    gorgona = None
                    running = False
                    gameplay_signal = "QUIT_TO_MENU"

                elif result == "VICTORY":
                    player.gorgona_defeated = True
                    gorgona = None
                    running = False
                    gameplay_signal = "QUIT_TO_MENU"

                elif result == "BAD_ENDING":
                    player.gorgona_defeated = False
                    running = False
                    gameplay_signal = "QUIT_TO_MENU"

        player_center = (player.x, player.y - PLAYER_HITBOX_CENTER_TO_FEET)

        for zone_data in TRANSFER_ZONES.values():
            zr = zone_rect(zone_data)
            if zr.collidepoint(player_center):
                _stop_player_move_sfx()
                running = False
                gameplay_signal = zone_data["target"]
                break

        if running:
            for door_data in LOCKED_DOORS.values():
                zr = zone_rect(door_data)
                if zr.collidepoint(player_center):
                    warn_timer = 2.5
                    warn_message = door_data.get("message", "...")

        _draw_world()
        _populate_world()

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

        viewport.blit(MIDNIGHT_OVERLAY, (0, 0))

        frame.zoom_focus = (int(player.x), int(player.y - cam_y))
        frame.quests = get_quests(player)

        frame_action = frame.draw(screen)

        if frame_action == "PAUSE":
            _stop_player_move_sfx()
            pause_result = run_pause_menu(
                screen, frame, slot_id=slot_id,
                player=player, wizard=None,
                orc=None, enemies=None)
            if pause_result == "QUIT_TO_MENU":
                running = False
                gameplay_signal = "QUIT_TO_MENU"
        elif frame_action == "STATS":
            _stop_player_move_sfx()
            run_stats_menu(screen, frame, player)

        if warn_timer > 0:
            warn_surf = font_cmd.render(warn_message, True, COLOR_WARN)
            warn_rect = warn_surf.get_rect(center=(960, 540))
            banner = pygame.Rect(warn_rect.left - 20, warn_rect.top - 8,
                                 warn_rect.width + 40, warn_rect.height + 16)
            pygame.draw.rect(screen, (20, 15, 25), banner, border_radius=6)
            pygame.draw.rect(screen, COLOR_WARN, banner, width=2,
                             border_radius=6)
            screen.blit(warn_surf, warn_rect)

        draw_inventory_and_equipment(screen, player, frame)
        pygame.display.flip()

    return gameplay_signal