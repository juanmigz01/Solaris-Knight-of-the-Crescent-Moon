import os
import sys
import importlib.util
import pygame

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

from player.player import Player
from enemies.wizard import Wizard
from Modules.game_frame import GameFrame
from Modules.pause_menu import run_pause_menu
from Modules.stats_menu import run_stats_menu
from Modules.dialogue_box import run_dialogue
from Modules.sound_manager import game_manager
from Modules.particles import ParticleSystem
from Modules.quest import get_quests
from Modules.inv import (
    draw_inventory_and_equipment,
    handle_inventory_click,
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


map_1 = load_module_from_path("map_1", os.path.join(PROJECT_ROOT, "map", "1.py"))
border = load_module_from_path("map_border", os.path.join(PROJECT_ROOT, "map", "border.py"))

CELL_SIZE = map_1.CELL_SIZE
build_objects_from_grid = map_1.build_objects_from_grid
get_mob_spawns = map_1.get_mob_spawns
BORDER_WALLS = border.BORDER_WALLS
draw_borders = border.draw_borders

TRANSFER_ZONES      = map_1.TRANSFER_ZONES
SPAWN_ZONES         = map_1.SPAWN_ZONES
draw_transfer_zones = map_1.draw_transfer_zones
draw_spawn_zones    = map_1.draw_spawn_zones
zone_rect           = map_1.zone_rect
zone_spawn_point    = map_1.zone_spawn_point

PLAYER_HITBOX_CENTER_TO_FEET = map_1.PLAYER_HITBOX_CENTER_TO_FEET

WORLD_HEIGHT = map_1.MAP_ROWS * map_1.CELL_SIZE
VIEWPORT_H   = 720


def grid_to_pixel(col, row):
    return (col * CELL_SIZE, row * CELL_SIZE)


def _reload_character_sprites(player, wizard):
    player.load_animations()
    wizard.load_spritesheet_and_json(
        os.path.join("asset", "enemy_img", "Wizard", "Wizard.png"),
        os.path.join("asset", "enemy_img", "Wizard", "Wizard.json"),
    )
    if "idledown" in wizard.animations and "idle" not in wizard.animations:
        wizard.animations["idle"] = wizard.animations["idledown"]
    wizard.set_animation("idle")


def _spawn_mobs_from_grid():
    mobs = {}
    for mob_type, mx, my in get_mob_spawns():
        if mob_type == "wizard_oz":
            if "wizard_oz" not in mobs:
                mobs["wizard_oz"] = Wizard(x=mx, y=my)
    return mobs


def _apply_hitbox_setting(player, wizard, deco_objects):
    on = getattr(game_manager, "hitbox_visible", False)
    player.show_hitbox = on
    wizard.show_hitbox = on
    for obj in deco_objects:
        obj.show_hitbox = on


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

    mobs = _spawn_mobs_from_grid()
    wizard = mobs.get("wizard_oz")
    if wizard is None:
        wizard = Wizard(x=5 * CELL_SIZE, y=5 * CELL_SIZE)
        mobs["wizard_oz"] = wizard

    wizard.dialogue_state = getattr(player, "wizard_dialogue_state", "PART_1")

    if getattr(player, "village_orc_reward_done", False):
        if wizard.dialogue_state != "COMPLETED":
            wizard.dialogue_state = "COMPLETED"
            player.wizard_dialogue_state = "COMPLETED"

    player.last_scene = "castle"

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

    _apply_hitbox_setting(player, wizard, all_deco_objects)

    player_name = getattr(player, "name", "Solaris")
    frame.title_text = f"{player_name}: Knight of the Crescent Moon"

    dialogue_story = [
        {"speaker": "Wizard Oz", "text": f"Ah. There you are, {player_name}."},
        {"speaker": player_name, "text": "You're the wizard they spoke of at the castle?"},
        {"speaker": "Wizard Oz", "text": "Oz. Just Oz. I've wandered these woods since before your kingdom had a name."},
        {"speaker": "Wizard Oz", "text": "I've heard what happened. Princess Lunaire, taken in the dark."},
        {"speaker": player_name, "text": "..."},
        {"speaker": "Wizard Oz", "text": "You know her, don't you? More than the kingdom does."},
        {"speaker": player_name, "text": "We grew up together. In the palace gardens."},
        {"speaker": "Wizard Oz", "text": "Then you have more reason to march than any soldier."},
        {"speaker": "Wizard Oz", "text": "Gorgona is no foe of steel alone. She bends the four elements to her will - Fire, Wind, Earth, Water."},
        {"speaker": "Wizard Oz", "text": "But she is not immune to them. They form a wheel, each one feeding the next."},
        {"speaker": player_name, "text": "Then teach me."},
        {"speaker": "Wizard Oz", "text": "Not yet. First - go east. A village lies past the trees."},
        {"speaker": "Wizard Oz", "text": "Its people are grieving too. When you reach them, come find me again."},
        {"speaker": "Wizard Oz", "text": "I will show you how to fight."},
        {"speaker": "Wizard Oz", "text": "Go now. The road is long, and the moon is already dimming."},
    ]

    dialogue_repeat = [
        {"speaker": "Wizard Oz",
         "text": f"Travel east, {player_name}. The village will not wait forever."},
    ]

    dialogue_after_village = [
        {"speaker": "Wizard Oz",
         "text": f"You've grown stronger, {player_name}. I can see it in how you carry yourself."},
        {"speaker": "Wizard Oz",
         "text": "The road west is open now. Beyond it lies the Mystic Forest - and your true trial."},
        {"speaker": "Wizard Oz",
         "text": "Go when you are ready."},
    ]

    obstacles = []
    for obj in all_deco_objects:
        if hasattr(obj, "hitbox"):
            obstacles.append(obj.hitbox)
    obstacles.append(wizard.hitbox)
    for wall_rect in BORDER_WALLS:
        obstacles.append(wall_rect)

    COLOR_GRASS = (80, 120, 60)
    COLOR_GOLD = (255, 215, 0)
    COLOR_WARN = (255, 170, 90)

    last_outline_state = getattr(game_manager, "outline_enabled", True)
    warn_timer = 0.0
    warn_message = "Not yet."

    world_surface.fill(COLOR_GRASS)
    castle_floor.draw(world_surface)
    if WORLD_HEIGHT > 720:
        extra_h = WORLD_HEIGHT - 720
        tile = world_surface.subsurface(pygame.Rect(0, 0, 1280, extra_h)).copy()
        world_surface.blit(tile, (0, 720))

    for obj in sorted(all_deco_objects,
                      key=lambda o: o.hitbox.bottom if hasattr(o, "hitbox") else o.rect.bottom):
        obj.draw(world_surface)
    wizard.draw(world_surface)
    player.draw(world_surface)
    draw_borders(world_surface)

    viewport = frame.get_viewport()
    viewport.blit(world_surface, (0, 0), pygame.Rect(0, 0, 1280, VIEWPORT_H))

    should_play_intro = (
        cinematic_intro
        or not getattr(player, "has_seen_castle_intro", False)
    )
    if should_play_intro:
        play_zoom_intro(screen, frame, player, world_surface, WORLD_HEIGHT,
                        duration_sec=1.9, start_zoom=2.4,
                        particles=particles)
        player.has_seen_castle_intro = True

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
                        orc=None, enemies=None,
                    )
                    if pause_result == "QUIT_TO_MENU":
                        running = False
                        gameplay_signal = "QUIT_TO_MENU"

                elif event.key == pygame.K_z:
                    game_manager.cycle_zoom()

                elif event.key == pygame.K_m:
                    if show_world_map is not None:
                        show_world_map(screen, player, player.last_scene)

                elif event.key == pygame.K_e:
                    if wizard.can_interact(player):
                        bg_snapshot = screen.copy()
                        village_done = bool(getattr(player, "village_orc_reward_done", False))

                        if wizard.dialogue_state == "PART_1" and not village_done:
                            run_dialogue(screen, dialogue_story, bg_snapshot)
                            wizard.dialogue_state = "COMPLETED"
                            player.wizard_dialogue_state = wizard.dialogue_state

                        elif village_done:
                            run_dialogue(screen, dialogue_after_village, bg_snapshot)
                        else:
                            run_dialogue(screen, dialogue_repeat, bg_snapshot)

        current_outline_state = getattr(game_manager, "outline_enabled", True)
        if current_outline_state != last_outline_state:
            last_outline_state = current_outline_state
            _reload_character_sprites(player, wizard)

        _apply_hitbox_setting(player, wizard, all_deco_objects)

        player.update(viewport_width=1280, viewport_height=WORLD_HEIGHT, obstacles=obstacles)
        wizard.update(delta_time=dt, player=player)

        wizard_done = (getattr(wizard, "dialogue_state", "PART_1") == "COMPLETED")
        village_done = bool(getattr(player, "village_orc_reward_done", False))

        player_center = (
            player.x,
            player.y - PLAYER_HITBOX_CENTER_TO_FEET,
        )
        player_hitbox = player.get_hitbox()

        for zone_data in TRANSFER_ZONES.values():
            zr = zone_rect(zone_data)
            if not zr.collidepoint(player_center):
                continue

            gate = zone_data.get("gate", "")
            gate_ok = False

            if gate == "wizard_completed":
                gate_ok = wizard_done or village_done
            elif gate == "village_done":
                gate_ok = village_done
            else:
                gate_ok = True

            if gate_ok:
                running = False
                gameplay_signal = zone_data["target"]
                break
            else:
                warn_timer = 2.5
                warn_message = zone_data.get("gate_message", "Not yet.")

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

        draw_queue.append((wizard.rect.bottom, wizard))
        draw_queue.append((player.y, player))
        draw_queue.sort(key=lambda item: item[0])

        for _, entity in draw_queue:
            entity.draw(world_surface)

        draw_borders(world_surface)
        zones_on = getattr(game_manager, "zones_visible", False)
        draw_transfer_zones(world_surface, force_show=zones_on)
        draw_spawn_zones(world_surface, force_show=zones_on)

        zoom = float(getattr(game_manager, "zoom_level", 1.0) or 1.0)
        target_cam_y = get_cam_y(player.y, zoom, WORLD_HEIGHT)

        if zoom <= 1.0:
            smooth_cam_y = 0.0
        else:
            smooth_cam_y = smooth_camera_y(smooth_cam_y, target_cam_y)

        cam_y = smooth_cam_y
        view_rect = pygame.Rect(0, int(cam_y), 1280, VIEWPORT_H)

        particles.draw(world_surface, view_rect=view_rect)

        viewport.blit(world_surface, (0, 0), view_rect)

        frame.zoom_focus = (int(player.x), int(player.y - cam_y))
        frame.quests = get_quests(player)
        frame_action = frame.draw(screen)

        if frame_action == "PAUSE":
            pause_result = run_pause_menu(
                screen, frame, slot_id=slot_id,
                player=player, wizard=wizard,
                orc=None, enemies=None,
            )
            if pause_result == "QUIT_TO_MENU":
                running = False
                gameplay_signal = "QUIT_TO_MENU"

        elif frame_action == "STATS":
            run_stats_menu(screen, frame, player)

        if wizard.can_interact(player):
            cmd_box = pygame.Rect(40, 250, 240, 46)
            pygame.draw.rect(screen, (20, 25, 35), cmd_box, border_radius=6)
            pygame.draw.rect(screen, COLOR_GOLD, cmd_box, width=2, border_radius=6)
            prompt_surf = font_cmd.render("[E] Talk to Wizard Oz", True, COLOR_GOLD)
            screen.blit(prompt_surf, prompt_surf.get_rect(center=cmd_box.center))

        if warn_timer > 0:
            warn_surf = font_cmd.render(warn_message, True, COLOR_WARN)
            warn_rect = warn_surf.get_rect(center=(960, 540))
            banner = pygame.Rect(
                warn_rect.left - 20, warn_rect.top - 8,
                warn_rect.width + 40, warn_rect.height + 16,
            )
            pygame.draw.rect(screen, (20, 15, 25), banner, border_radius=6)
            pygame.draw.rect(screen, COLOR_WARN, banner, width=2, border_radius=6)
            screen.blit(warn_surf, warn_rect)

        draw_inventory_and_equipment(screen, player, frame)
        pygame.display.flip()

    return gameplay_signal