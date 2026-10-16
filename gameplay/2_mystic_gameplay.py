import os
import sys
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
from Modules.quest import get_quests
from Modules.inv import (
    draw_inventory_and_equipment,
    handle_inventory_click,
)
from Modules.cinematics import (
    get_cam_y, smooth_camera_y, play_zoom_intro,
)
from Modules.transition import run_transition
from floor.mystic import MysticFloor

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


mystic_map = load_module_from_path(
    "map_2_mystic", os.path.join(PROJECT_ROOT, "map", "2_mystic.py"))
border = load_module_from_path(
    "map_border", os.path.join(PROJECT_ROOT, "map", "border.py"))

CELL_SIZE = mystic_map.CELL_SIZE
build_objects_from_grid = mystic_map.build_objects_from_grid
get_mob_spawns = mystic_map.get_mob_spawns

BORDER_WALLS = border.BORDER_WALLS
draw_borders = border.draw_borders

TRANSFER_ZONES      = mystic_map.TRANSFER_ZONES
LOCKED_DOORS        = mystic_map.LOCKED_DOORS
SPAWN_ZONES         = mystic_map.SPAWN_ZONES
draw_transfer_zones = mystic_map.draw_transfer_zones
draw_spawn_zones    = mystic_map.draw_spawn_zones
zone_rect           = mystic_map.zone_rect
zone_spawn_point    = mystic_map.zone_spawn_point

PLAYER_HITBOX_CENTER_TO_FEET = mystic_map.PLAYER_HITBOX_CENTER_TO_FEET

WORLD_HEIGHT = mystic_map.MAP_ROWS * mystic_map.CELL_SIZE
VIEWPORT_H   = 720


SKIPABLE = False

MYSTIC_INTRO_LINES = [
    ("NARRATOR", "The road bends west. Ancient trunks close over the sky."),
    ("NARRATOR", "A forest the kingdom never bothered to map."),
    ("SOLARIS", "...The air is thick here. Old. Silent."),
    ("LUNAIRE", "Solaris..."),
    ("SOLARIS", "...Lunaire?"),
    ("LUNAIRE", "Please... help me..."),
    ("SOLARIS", "I'm coming. Just hold on."),
]


def _wrap_text(text, font, max_width):
    words = text.split(' ')
    lines = []
    cur = ""
    for word in words:
        if "\n" in word:
            parts = word.split("\n")
            for j, part in enumerate(parts):
                if j > 0:
                    lines.append(cur)
                    cur = ""
                if part:
                    cur += part + " "
        else:
            test = cur + word + " "
            if font.size(test)[0] < max_width:
                cur = test
            else:
                lines.append(cur)
                cur = word + " "
    lines.append(cur)
    return lines


def _render_wrapped(surface, text, font, color, x, y, max_w, line_gap=8):
    for line in _wrap_text(text, font, max_w):
        stripped = line.strip()
        if stripped:
            s = font.render(stripped, True, color)
            surface.blit(s, (x, y))
        y += font.get_linesize() + line_gap


def _play_mystic_intro(screen):
    clock = pygame.time.Clock()
    screen_w, screen_h = screen.get_size()

    font_path = os.path.join(PROJECT_ROOT, "asset", "font", "TheGothicRite.otf")
    if os.path.exists(font_path):
        font_header = pygame.font.Font(font_path, 46)
        font_body   = pygame.font.Font(font_path, 32)
        font_hint   = pygame.font.Font(font_path, 20)
    else:
        font_header = pygame.font.SysFont("Georgia", 46, bold=True)
        font_body   = pygame.font.SysFont("Georgia", 32)
        font_hint   = pygame.font.SysFont("Georgia", 20)

    COLOR_BLACK = (10, 10, 15)
    COLOR_VOID  = (0, 0, 0)
    COLOR_GOLD  = (212, 175, 55)
    COLOR_WHITE = (240, 235, 210)
    COLOR_GRAY  = (150, 150, 170)
    COLOR_AQUA  = (140, 220, 255)

    CHAR_DELAY = 0.045
    LETTERBOX_H = 90

    for speaker, text in MYSTIC_INTRO_LINES:
        total = len(text)
        timer = 0.0
        cursor_t = 0.0
        revealed = False
        advanced = False

        while not advanced:
            dt = clock.tick(60) / 1000.0

            if not revealed:
                timer += dt
                cursor_t += dt
                vis = int(timer / CHAR_DELAY)
                if vis >= total:
                    vis = total
                    revealed = True

            shown = text[:vis] if not revealed else text
            if not revealed:
                cursor_char = "_" if (int(cursor_t * 3) % 2 == 0) else ""
                shown = shown + cursor_char

            screen.fill(COLOR_BLACK)

            hcolor = COLOR_AQUA if speaker.upper() in ("NARRATOR", "LUNAIRE") else COLOR_GOLD
            hsurf = font_header.render(speaker.capitalize(), True, hcolor)
            screen.blit(hsurf, (340, 260))
            pygame.draw.line(screen, COLOR_GOLD,
                             (340, 260 + hsurf.get_height() + 8),
                             (340 + 640, 260 + hsurf.get_height() + 8), 2)
            _render_wrapped(screen, shown, font_body, COLOR_WHITE, 340, 340, 1240)

            if revealed:
                hint = font_hint.render("[ SPACE / ENTER to continue ]", True, COLOR_GRAY)
                screen.blit(hint, hint.get_rect(center=(screen_w // 2, screen_h - 130)))

            bar = pygame.Surface((screen_w, LETTERBOX_H))
            bar.fill(COLOR_VOID)
            screen.blit(bar, (0, 0))
            screen.blit(bar, (0, screen_h - LETTERBOX_H))

            pygame.display.flip()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                if not revealed:
                    if SKIPABLE:
                        if ((event.type == pygame.KEYDOWN and
                             event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_e))
                            or (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1)):
                            revealed = True
                            timer = total * CHAR_DELAY
                    continue

                if ((event.type == pygame.KEYDOWN and
                     event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_e))
                    or (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1)):
                    advanced = True


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

    player.last_scene = "mystic"

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
    warn_message = "The deeper woods are sealed for now."

    if not getattr(player, "has_seen_mystic_intro", False):
        run_transition(screen,
                       message="Entering the Mystic Forest...",
                       duration_sec=1.3)

        _play_mystic_intro(screen)

        world_surface.fill(COLOR_GRASS)
        floor.draw(world_surface)
        if WORLD_HEIGHT > 720:
            extra_h = WORLD_HEIGHT - 720
            tile = world_surface.subsurface(pygame.Rect(0, 0, 1280, extra_h)).copy()
            world_surface.blit(tile, (0, 720))
        for obj in sorted(all_deco_objects,
                          key=lambda o: o.hitbox.bottom if hasattr(o, "hitbox") else o.rect.bottom):
            obj.draw(world_surface, **outline_pulse.draw_kwargs(obj))
        player.draw(world_surface)
        draw_borders(world_surface)

        play_zoom_intro(screen, frame, player, world_surface, WORLD_HEIGHT,
                        duration_sec=2.2, start_zoom=2.4, hold_peak_sec=0.2,
                        particles=particles)
        player.has_seen_mystic_intro = True

    running = True
    gameplay_signal = None
    smooth_cam_y = None

    world_surface.fill(COLOR_GRASS)
    floor.draw(world_surface)
    if WORLD_HEIGHT > 720:
        extra_h = WORLD_HEIGHT - 720
        tile = world_surface.subsurface(pygame.Rect(0, 0, 1280, extra_h)).copy()
        world_surface.blit(tile, (0, 720))
    for obj in sorted(all_deco_objects,
                      key=lambda o: o.hitbox.bottom if hasattr(o, "hitbox") else o.rect.bottom):
        obj.draw(world_surface, **outline_pulse.draw_kwargs(obj))
    player.draw(world_surface)
    draw_borders(world_surface)

    viewport = frame.get_viewport()
    viewport.blit(world_surface, (0, 0), pygame.Rect(0, 0, 1280, VIEWPORT_H))

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
                                                 "The deeper woods are sealed for now.")

        world_surface.fill(COLOR_GRASS)
        floor.draw(world_surface)

        if WORLD_HEIGHT > 720:
            extra_h = WORLD_HEIGHT - 720
            tile = world_surface.subsurface(pygame.Rect(0, 0, 1280, extra_h)).copy()
            world_surface.blit(tile, (0, 720))

        player_hitbox = player.get_hitbox()
        draw_queue = []
        for obj in all_deco_objects:
            draw_y = obj.hitbox.bottom if hasattr(obj, "hitbox") else obj.rect.bottom
            if (hasattr(obj, "layer_hitbox") and obj.layer_hitbox
                    and obj.layer_hitbox.colliderect(player_hitbox)):
                draw_y = player.y + 9999
            draw_queue.append((draw_y, obj))

        draw_queue.append((player.y, player))
        draw_queue.sort(key=lambda item: item[0])

        for _, entity in draw_queue:
            entity.draw(world_surface, **outline_pulse.draw_kwargs(entity))

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
                orc=None, enemies=None)
            if pause_result == "QUIT_TO_MENU":
                running = False
                gameplay_signal = "QUIT_TO_MENU"
        elif frame_action == "STATS":
            run_stats_menu(screen, frame, player)

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

    return gameplay_signal