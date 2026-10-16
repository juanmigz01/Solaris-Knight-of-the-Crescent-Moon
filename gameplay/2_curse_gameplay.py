import os
import sys
import random
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
from Modules.particles import ParticleSystem, FireflySystem
from Modules.mystic_effects import RainbowOutlinePulse
from Modules.chest import Chest
from Modules.quest import get_quests
from Modules.inv import (
    draw_inventory_and_equipment,
    handle_inventory_click,
    give_item_by_id,
    roll_chest_loot,
)
from Modules.cinematics import (
    get_cam_y, smooth_camera_y, play_zoom_intro,
)
from floor.mystic import MysticFloor

from enemies.slime import Slime
from enemies.tiny_orc import TinyOrc
from enemies.tiny_devil import TinyDevil
from battle.multi_battle import run_multi_battle
from battle.battle_func import play_warning_sfx

try:
    from map.map import show_map as show_world_map
except ImportError as _wm_err:
    print(f"[Gameplay] world map import failed: {_wm_err}")
    show_world_map = None


VIEWPORT_SCREEN_RECT = pygame.Rect(320, 180, 1280, 720)
VIEWPORT_OFFSET = (320, 180)

CURSE_SPAWN_COUNT = 4

CURSE_ENEMY_WEIGHTS = (
    ("slime",      0.30),
    ("tiny_orc",   0.30),
    ("tiny_devil", 0.40),
)


def load_module_from_path(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


curse_map = load_module_from_path(
    "map_2_curse", os.path.join(PROJECT_ROOT, "map", "2_curse.py"))
border = load_module_from_path(
    "map_border", os.path.join(PROJECT_ROOT, "map", "border.py"))

CELL_SIZE = curse_map.CELL_SIZE
build_objects_from_grid = curse_map.build_objects_from_grid
get_mob_spawns = curse_map.get_mob_spawns

BORDER_WALLS = border.BORDER_WALLS
draw_borders = border.draw_borders

TRANSFER_ZONES      = curse_map.TRANSFER_ZONES
LOCKED_DOORS        = curse_map.LOCKED_DOORS
SPAWN_ZONES         = curse_map.SPAWN_ZONES
draw_transfer_zones = curse_map.draw_transfer_zones
draw_spawn_zones    = curse_map.draw_spawn_zones
zone_rect           = curse_map.zone_rect
zone_spawn_point    = curse_map.zone_spawn_point

PLAYER_HITBOX_CENTER_TO_FEET = curse_map.PLAYER_HITBOX_CENTER_TO_FEET

WORLD_HEIGHT = curse_map.MAP_ROWS * curse_map.CELL_SIZE
VIEWPORT_H   = 720


def _roll_curse_kind():
    roll = random.random()
    cum = 0.0
    for kind, weight in CURSE_ENEMY_WEIGHTS:
        cum += weight
        if roll <= cum:
            return kind
    return "slime"


def _roll_curse_wave_kinds():
    return [_roll_curse_kind() for _ in range(2)]


def _make_enemy_from_kind(kind):
    if kind == "tiny_orc":
        return TinyOrc(x=0, y=0)
    if kind == "tiny_devil":
        return TinyDevil(x=0, y=0)
    return Slime(x=0, y=0)


def _make_marker_from_kind(kind, mx, my):
    if kind == "tiny_orc":
        return TinyOrc(x=mx, y=my)
    if kind == "tiny_devil":
        return TinyDevil(x=mx, y=my)
    return Slime(x=mx, y=my)


def _spawn_marker_and_wave(idx, mx, my, curse_waves, flee_cooldown=False):
    kinds = _roll_curse_wave_kinds()
    curse_waves[idx] = kinds
    marker = _make_marker_from_kind(kinds[0], mx, my)
    if flee_cooldown:
        marker.start_flee_cooldown()
    return marker


def run_test_gameplay(screen, slot_id=1, player=None,
                      entry_from="default", cinematic_intro=False):
    game_manager.play_ambient("zone_2.mp3", volume=0.45, fade_ms=800)

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

    particles = ParticleSystem(
        world_w=1280, world_h=WORLD_HEIGHT,
        intensity=intensity,
        sprite_names=("oparticle",),
    )

    fireflies = FireflySystem(
        world_w=1280, world_h=WORLD_HEIGHT,
        intensity=intensity,
    )

    outline_pulse = RainbowOutlinePulse(cycle_sec=12.0)

    world_surface = pygame.Surface((1280, WORLD_HEIGHT))

    floor = MysticFloor(viewport_width=1280, viewport_height=720)
    if getattr(floor, "floor_images", None):
        floor.current_floor = floor.floor_images[0]

    if player is None:
        player = Player(x=0, y=0, name="Solaris")

    player.last_scene = "curse"

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

    COLOR_GRASS = (40, 70, 55)
    COLOR_GOLD = (255, 215, 0)
    COLOR_WARN = (255, 170, 90)

    warn_timer = 0.0
    warn_message = "Nothing but silence beyond."

    curse_positions = []
    for mob_type, mx, my in get_mob_spawns():
        if mob_type == "curse_spawn":
            curse_positions.append((mx, my))
    while len(curse_positions) < CURSE_SPAWN_COUNT:
        curse_positions.append((0, 0))
    curse_positions = curse_positions[:CURSE_SPAWN_COUNT]

    if not hasattr(player, "curse_spawn_defeated_list"):
        player.curse_spawn_defeated_list = [False] * CURSE_SPAWN_COUNT
    while len(player.curse_spawn_defeated_list) < CURSE_SPAWN_COUNT:
        player.curse_spawn_defeated_list.append(False)
    player.curse_spawn_defeated_list = \
        player.curse_spawn_defeated_list[:CURSE_SPAWN_COUNT]

    if not hasattr(player, "curse_spawn_chest_opened_list"):
        player.curse_spawn_chest_opened_list = [False] * CURSE_SPAWN_COUNT
    while len(player.curse_spawn_chest_opened_list) < CURSE_SPAWN_COUNT:
        player.curse_spawn_chest_opened_list.append(False)
    player.curse_spawn_chest_opened_list = \
        player.curse_spawn_chest_opened_list[:CURSE_SPAWN_COUNT]

    curse_markers = {}
    curse_waves = {}

    for idx in range(CURSE_SPAWN_COUNT):
        if player.curse_spawn_defeated_list[idx]:
            continue
        mx, my = curse_positions[idx]
        curse_markers[idx] = _spawn_marker_and_wave(
            idx, mx, my, curse_waves, flee_cooldown=False)

    curse_chests = {}
    for idx in range(CURSE_SPAWN_COUNT):
        if (player.curse_spawn_defeated_list[idx]
                and not player.curse_spawn_chest_opened_list[idx]):
            cx, cy = curse_positions[idx]
            curse_chests[idx] = Chest(
                x=cx, y=cy,
                loot=roll_chest_loot(),
                label=f"Cursed Cache {idx + 1}",
            )

    print("[Curse] Initial waves:")
    for idx in range(CURSE_SPAWN_COUNT):
        print(f"  Spawn {idx + 1}: {curse_waves.get(idx, 'defeated')}")

    def _reset_curse_spawns():
        player.curse_spawn_defeated_list = [False] * CURSE_SPAWN_COUNT
        player.curse_spawn_chest_opened_list = [False] * CURSE_SPAWN_COUNT

        curse_markers.clear()
        curse_waves.clear()
        for idx in range(CURSE_SPAWN_COUNT):
            mx, my = curse_positions[idx]
            curse_markers[idx] = _spawn_marker_and_wave(
                idx, mx, my, curse_waves, flee_cooldown=True)

        curse_chests.clear()

        print("[Curse] Reset - new waves:")
        for idx in range(CURSE_SPAWN_COUNT):
            print(f"  Spawn {idx + 1}: {curse_waves.get(idx)}")

    player._on_heal_consumable_used = _reset_curse_spawns

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

        for marker in curse_markers.values():
            draw_queue.append((marker.rect.bottom, marker))
        for chest in curse_chests.values():
            draw_queue.append((chest.rect.bottom, chest))

        draw_queue.append((player.y, player))
        draw_queue.sort(key=lambda item: item[0])

        for _, entity in draw_queue:
            entity.draw(world_surface, **outline_pulse.draw_kwargs(entity))

        draw_borders(world_surface)
        zones_on = getattr(game_manager, "zones_visible", False)
        draw_transfer_zones(world_surface, force_show=zones_on)
        draw_spawn_zones(world_surface, force_show=zones_on)

    if not getattr(player, "has_seen_curse_intro", False):
        _draw_world()
        _populate_world()

        viewport = frame.get_viewport()
        viewport.blit(world_surface, (0, 0),
                      pygame.Rect(0, 0, 1280, VIEWPORT_H))

        play_zoom_intro(screen, frame, player, world_surface, WORLD_HEIGHT,
                        duration_sec=2.0, start_zoom=2.2, hold_peak_sec=0.2,
                        particles=particles)
        player.has_seen_curse_intro = True

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
            fireflies.set_intensity(current_particles)

        particles.update(dt)
        fireflies.update(dt)
        outline_pulse.update(dt)

        for idx, chest in list(curse_chests.items()):
            chest.update(dt)
            if getattr(chest, "looted", False) and chest.is_opened():
                del curse_chests[idx]

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
                        player=player, wizard=None,
                        orc=None, enemies=None,
                        on_save=_reset_curse_spawns)
                    if pause_result == "QUIT_TO_MENU":
                        running = False
                        gameplay_signal = "QUIT_TO_MENU"

                elif event.key == pygame.K_z:
                    game_manager.cycle_zoom()

                elif event.key == pygame.K_m:
                    if show_world_map is not None:
                        show_world_map(screen, player, player.last_scene)

                elif event.key == pygame.K_e:
                    for idx, chest in list(curse_chests.items()):
                        if chest is None:
                            continue
                        if not chest.can_interact(player):
                            continue
                        if player.curse_spawn_chest_opened_list[idx]:
                            continue
                        chest.open()
                        chest.looted = True
                        for item_id in chest.loot:
                            give_item_by_id(player, item_id)
                        player.curse_spawn_chest_opened_list[idx] = True
                        break

        player.update(viewport_width=1280, viewport_height=WORLD_HEIGHT,
                      obstacles=static_obstacles)

        for marker in curse_markers.values():
            marker.update(delta_time=dt, player=player)

        triggered_idx = None
        for idx, marker in curse_markers.items():
            if marker.triggered_battle:
                triggered_idx = idx
                break

        if triggered_idx is not None:
            marker = curse_markers[triggered_idx]
            marker.triggered_battle = False

            play_warning_sfx()

            kinds = curse_waves.get(triggered_idx)
            if not kinds:
                kinds = _roll_curse_wave_kinds()
            enemies = [_make_enemy_from_kind(k) for k in kinds]
            waves = [{"enemies": enemies, "attackers": None}]

            print(f"[Curse] Triggered spawn {triggered_idx + 1}: {kinds}")

            result = run_multi_battle(screen, player, waves, slot_id=slot_id)

            if result == "VICTORY":
                player.curse_spawn_defeated_list[triggered_idx] = True
                cx, cy = curse_positions[triggered_idx]
                curse_chests[triggered_idx] = Chest(
                    x=cx, y=cy,
                    loot=roll_chest_loot(),
                    label=f"Cursed Cache {triggered_idx + 1}",
                )
                del curse_markers[triggered_idx]

            elif result == "DEFEAT":
                _reset_curse_spawns()

            elif result == "FLED":
                marker.start_flee_cooldown()

        player_center = (player.x, player.y - PLAYER_HITBOX_CENTER_TO_FEET)

        for zone_data in TRANSFER_ZONES.values():
            zr = zone_rect(zone_data)
            if zr.collidepoint(player_center):
                running = False
                gameplay_signal = zone_data["target"]
                break

        if running:
            for door_data in LOCKED_DOORS.values():
                zr = zone_rect(door_data)
                if zr.collidepoint(player_center):
                    warn_timer = 2.5
                    warn_message = door_data.get("message",
                                                 "Nothing but silence beyond.")

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
        fireflies.draw(world_surface, view_rect=view_rect)

        viewport = frame.get_viewport()
        viewport.blit(world_surface, (0, 0), view_rect)

        frame.zoom_focus = (int(player.x), int(player.y - cam_y))
        frame.quests = get_quests(player)

        frame_action = frame.draw(screen)

        if frame_action == "PAUSE":
            pause_result = run_pause_menu(
                screen, frame, slot_id=slot_id,
                player=player, wizard=None,
                orc=None, enemies=None,
                on_save=_reset_curse_spawns)
            if pause_result == "QUIT_TO_MENU":
                running = False
                gameplay_signal = "QUIT_TO_MENU"
        elif frame_action == "STATS":
            run_stats_menu(screen, frame, player)

        any_chest_in_range = False
        for idx, chest in curse_chests.items():
            if (not player.curse_spawn_chest_opened_list[idx]
                    and chest.can_interact(player)):
                any_chest_in_range = True
                break

        if any_chest_in_range:
            cmd_box = pygame.Rect(40, 250, 240, 46)
            pygame.draw.rect(screen, (20, 25, 35), cmd_box, border_radius=6)
            pygame.draw.rect(screen, COLOR_GOLD, cmd_box, width=2, border_radius=6)
            prompt_surf = font_cmd.render("[E] Open chest", True, COLOR_GOLD)
            screen.blit(prompt_surf, prompt_surf.get_rect(center=cmd_box.center))

        if warn_timer > 0:
            warn_surf = font_cmd.render(warn_message, True, COLOR_WARN)
            warn_rect = warn_surf.get_rect(center=(960, 540))
            banner = pygame.Rect(warn_rect.left - 20, warn_rect.top - 8,
                                 warn_rect.width + 40, warn_rect.height + 16)
            pygame.draw.rect(screen, (20, 15, 25), banner, border_radius=6)
            pygame.draw.rect(screen, COLOR_WARN, banner, width=2, border_radius=6)
            screen.blit(warn_surf, warn_rect)

        draw_inventory_and_equipment(screen, player, frame)
        pygame.display.flip()

    if hasattr(player, "_on_heal_consumable_used"):
        try:
            del player._on_heal_consumable_used
        except AttributeError:
            pass

    return gameplay_signal