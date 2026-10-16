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
from enemies.tiny_orc import TinyOrc
from enemies.slime import Slime
from Modules.game_frame import GameFrame
from Modules.pause_menu import run_pause_menu
from Modules.stats_menu import run_stats_menu
from Modules.dialogue_box import run_dialogue
from Modules.sound_manager import game_manager
from Modules.particles import ParticleSystem
from Modules.chest import Chest
from Modules.quest import get_quests
from Modules.inv import (
    draw_inventory_and_equipment,
    handle_inventory_click,
    give_item_by_id,
    give_outskirts_reward,
    roll_chest_loot,
)
from Modules.cinematics import (
    get_cam_y, smooth_camera_y, play_zoom_intro,
)
from floor.castle import CastleFloor

from battle.multi_battle import run_multi_battle
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


outskirts_map = load_module_from_path(
    "map_1_outskirts", os.path.join(PROJECT_ROOT, "map", "1_outskirts.py"))
border = load_module_from_path(
    "map_border", os.path.join(PROJECT_ROOT, "map", "border.py"))

CELL_SIZE = outskirts_map.CELL_SIZE
build_objects_from_grid = outskirts_map.build_objects_from_grid
get_mob_spawns = outskirts_map.get_mob_spawns

BORDER_WALLS = border.BORDER_WALLS
draw_borders = border.draw_borders

TRANSFER_ZONES      = outskirts_map.TRANSFER_ZONES
LOCKED_DOORS        = outskirts_map.LOCKED_DOORS
SPAWN_ZONES         = outskirts_map.SPAWN_ZONES
draw_transfer_zones = outskirts_map.draw_transfer_zones
draw_spawn_zones    = outskirts_map.draw_spawn_zones
zone_rect           = outskirts_map.zone_rect
zone_spawn_point    = outskirts_map.zone_spawn_point

PLAYER_HITBOX_CENTER_TO_FEET = outskirts_map.PLAYER_HITBOX_CENTER_TO_FEET

WORLD_HEIGHT = outskirts_map.MAP_ROWS * outskirts_map.CELL_SIZE
VIEWPORT_H   = 720

TOTAL_HORDES = 3


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


def _play_cinematic(screen, dialogue_list):
    clock = pygame.time.Clock()
    screen_w, screen_h = screen.get_size()

    font_path = os.path.join(PROJECT_ROOT, "asset", "font", "TheGothicRite.otf")
    if os.path.exists(font_path):
        font_header  = pygame.font.Font(font_path, 46)
        font_body    = pygame.font.Font(font_path, 32)
        font_hint    = pygame.font.Font(font_path, 20)
        font_choice  = pygame.font.Font(font_path, 28)
    else:
        font_header  = pygame.font.SysFont("Georgia", 46, bold=True)
        font_body    = pygame.font.SysFont("Georgia", 32)
        font_hint    = pygame.font.SysFont("Georgia", 20)
        font_choice  = pygame.font.SysFont("Georgia", 28, bold=True)

    COLOR_BLACK = (10, 10, 15)
    COLOR_VOID  = (0, 0, 0)
    COLOR_GOLD  = (212, 175, 55)
    COLOR_BRIGHT_GOLD = (255, 215, 0)
    COLOR_WHITE = (240, 235, 210)
    COLOR_GRAY  = (150, 150, 170)
    COLOR_AQUA  = (140, 220, 255)

    CHAR_DELAY = 0.035
    LETTERBOX_H = 90

    def _draw(speaker, shown_text, revealed, choices_rects, mouse_pos):
        screen.fill(COLOR_BLACK)
        hcolor = COLOR_AQUA if speaker.upper() in ("NARRATOR", "SYSTEM") else COLOR_GOLD
        hsurf = font_header.render(speaker, True, hcolor)
        screen.blit(hsurf, (340, 260))
        pygame.draw.line(screen, COLOR_GOLD,
                         (340, 260 + hsurf.get_height() + 8),
                         (340 + 640, 260 + hsurf.get_height() + 8), 2)
        _render_wrapped(screen, shown_text, font_body, COLOR_WHITE, 340, 340, 1240)

        if revealed:
            if choices_rects:
                for r, ch_dict in choices_rects:
                    hovered = r.collidepoint(mouse_pos)
                    fill = (60, 50, 95) if hovered else (35, 30, 60)
                    pygame.draw.rect(screen, fill, r, border_radius=6)
                    pygame.draw.rect(screen, COLOR_GOLD, r, width=2, border_radius=6)
                    idx = choices_rects.index((r, ch_dict)) + 1
                    lbl = f"{idx}. {ch_dict['label']}"
                    col = COLOR_BRIGHT_GOLD if hovered else COLOR_WHITE
                    ls = font_choice.render(lbl, True, col)
                    screen.blit(ls, (r.x + 18, r.y + (r.height - ls.get_height()) // 2))
            else:
                hint = font_hint.render("[ SPACE / ENTER to continue ]", True, COLOR_GRAY)
                screen.blit(hint, hint.get_rect(center=(screen_w // 2, screen_h - 130)))

        bar = pygame.Surface((screen_w, LETTERBOX_H))
        bar.fill(COLOR_VOID)
        screen.blit(bar, (0, 0))
        screen.blit(bar, (0, screen_h - LETTERBOX_H))

    for line in dialogue_list:
        speaker = line.get("speaker", "???")
        text = line.get("text", "")
        choices = line.get("choices")

        total = len(text)
        timer = 0.0
        cursor_t = 0.0
        revealed = False

        choices_rects = []
        if choices:
            cw, ch = 640, 52
            cx = screen_w // 2 - cw // 2
            base_y = screen_h - 260
            for ci, chd in enumerate(choices):
                r = pygame.Rect(cx, base_y + ci * (ch + 12), cw, ch)
                choices_rects.append((r, chd))

        advanced = False
        chose_key = None

        while not advanced and chose_key is None:
            dt = clock.tick(60) / 1000.0
            mouse_pos = pygame.mouse.get_pos()

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

            _draw(speaker, shown, revealed,
                  choices_rects if revealed else None, mouse_pos)
            pygame.display.flip()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                if not revealed:
                    if ((event.type == pygame.KEYDOWN and
                         event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_e))
                        or (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1)):
                        revealed = True
                        timer = total * CHAR_DELAY
                    continue

                if choices_rects:
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        for r, chd in choices_rects:
                            if r.collidepoint(event.pos):
                                chose_key = chd.get("key", "")
                                break
                    elif event.type == pygame.KEYDOWN:
                        if pygame.K_1 <= event.key <= pygame.K_9:
                            n = event.key - pygame.K_1
                            if 0 <= n < len(choices_rects):
                                chose_key = choices_rects[n][1].get("key", "")
                else:
                    if ((event.type == pygame.KEYDOWN and
                         event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_e))
                        or (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1)):
                        advanced = True

        if chose_key is not None:
            return ("CHOICE", chose_key)

    return None


def _play_outskirts_cutscene(player_name, screen):
    opening = [
        {"speaker": "NARRATOR",
         "text": "The last of the horde falls. Only one still stands - "
                 "a tiny orc, wounded and cornered against a maple tree."},
        {"speaker": player_name, "text": "You."},
        {"speaker": player_name, "text": "Where is Lunaire?"},
        {"speaker": "Tiny Orc", "text": "Hehehe..."},
        {"speaker": "Tiny Orc", "text": "Hee hee hee hee..."},
        {"speaker": "NARRATOR",
         "text": "The orc wipes blood from its lip and smiles."},
        {"speaker": player_name, "text": "...",
         "choices": [
             {"label": "Question him", "key": "question"},
             {"label": "End him",      "key": "end"},
         ]},
    ]
    result = _play_cinematic(screen, opening)
    branch = "question"
    if isinstance(result, tuple) and result[0] == "CHOICE":
        branch = result[1]

    if branch == "question":
        _play_cinematic(screen, [
            {"speaker": player_name, "text": "Answer me. Now."},
            {"speaker": "Tiny Orc",
             "text": "Hee hee... you think I'll tell a human anything?"},
            {"speaker": player_name,
             "text": "The princess. Where did Gorgona take her?"},
            {"speaker": "Tiny Orc",
             "text": "...why should I care about your little moon?"},
            {"speaker": "NARRATOR",
             "text": f"{player_name} draws his blade. The steel catches the dim light."},
            {"speaker": player_name,
             "text": "Because I will make what comes next very, very slow."},
            {"speaker": "Tiny Orc", "text": "..."},
            {"speaker": "Tiny Orc", "text": "...fine. FINE."},
            {"speaker": "Tiny Orc",
             "text": "East. Past the tree line. A forest the humans never mapped."},
            {"speaker": "Tiny Orc",
             "text": "The Mystic Forest. Beneath the Empress's empire."},
            {"speaker": "Tiny Orc",
             "text": "That is where she keeps what she takes."},
            {"speaker": player_name, "text": "..."},
            {"speaker": player_name, "text": "Then that is where I go."},
            {"speaker": "NARRATOR",
             "text": "The orc slumps. The road east is open."},
        ])
    else:
        _play_cinematic(screen, [
            {"speaker": "NARRATOR",
             "text": f"{player_name} does not ask again."},
            {"speaker": "NARRATOR",
             "text": "The orc falls before he can change his mind."},
            {"speaker": player_name, "text": "..."},
            {"speaker": player_name, "text": "Then I go east."},
        ])

    return branch


def _spawn_mobs_from_grid():
    mobs = {"wizard_oz": None}
    markers = []
    for mob_type, mx, my in get_mob_spawns():
        if mob_type == "wizard_oz" and mobs["wizard_oz"] is None:
            mobs["wizard_oz"] = Wizard(x=mx, y=my)
        elif mob_type == "slime":
            markers.append(Slime(x=mx, y=my))
        elif mob_type == "tiny_orc":
            o = TinyOrc(x=mx, y=my)
            o.name = "Orc Scout"
            markers.append(o)
    return mobs, markers


def _reload_character_sprites(player, wizard, markers):
    player.load_animations()
    if wizard is not None:
        wizard.load_spritesheet_and_json(
            os.path.join("asset", "enemy_img", "Wizard", "Wizard.png"),
            os.path.join("asset", "enemy_img", "Wizard", "Wizard.json"))
        if "idledown" in wizard.animations and "idle" not in wizard.animations:
            wizard.animations["idle"] = wizard.animations["idledown"]
        wizard.set_animation("idle")

    for m in markers:
        if m is None:
            continue
        if isinstance(m, Slime):
            m.load_spritesheet_and_json(
                os.path.join("asset", "enemy_img", "slime", "Slime.png"),
                os.path.join("asset", "enemy_img", "slime", "Slime.json"))
        elif isinstance(m, TinyOrc):
            m.load_spritesheet_and_json(
                os.path.join("asset", "enemy_img", "tiny orc", "Tiny_Orc.png"),
                os.path.join("asset", "enemy_img", "tiny orc", "Tiny_Orc.json"))
        m.set_animation("idle")


def _apply_hitbox_setting(player, mobs, deco_objects):
    on = getattr(game_manager, "hitbox_visible", False)
    player.show_hitbox = on
    for m in mobs:
        if m is not None:
            m.show_hitbox = on
    for obj in deco_objects:
        obj.show_hitbox = on


def _spawn_unique_orcs(count):
    import random as _rng
    from enemies.enemy_element import ElementComponent
    elements = list(ElementComponent.ELEMENTS)
    _rng.shuffle(elements)
    return [TinyOrc(x=0, y=0, element=elements[i % len(elements)]) for i in range(count)]


def _build_horde_slime_small():
    return [
        {"enemies": [Slime(x=0, y=0), Slime(x=0, y=0)], "attackers": 1},
        {"enemies": [Slime(x=0, y=0), Slime(x=0, y=0)], "attackers": 1},
    ]


def _build_horde_orc():
    return [
        {"enemies": _spawn_unique_orcs(1) + [Slime(x=0, y=0)], "attackers": 1},
        {"enemies": _spawn_unique_orcs(2), "attackers": 1},
        {"enemies": _spawn_unique_orcs(1), "attackers": None},
    ]


def _build_horde_slime_big():
    return [
        {"enemies": [Slime(x=0, y=0), Slime(x=0, y=0), Slime(x=0, y=0)], "attackers": 2},
        {"enemies": [Slime(x=0, y=0), Slime(x=0, y=0), Slime(x=0, y=0)], "attackers": 2},
    ]


def _build_horde_by_index(idx):
    builders = [_build_horde_slime_small, _build_horde_orc, _build_horde_slime_big]
    if 0 <= idx < len(builders):
        return builders[idx]()
    return _build_horde_slime_small()


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

    player.last_scene = "outskirts"

    if not hasattr(player, "outskirts_wizard_state"):
        player.outskirts_wizard_state = "NEW"
    if not hasattr(player, "outskirts_horde_defeated"):
        player.outskirts_horde_defeated = False
    if not hasattr(player, "outskirts_horde_defeated_list"):
        player.outskirts_horde_defeated_list = [False] * TOTAL_HORDES
    if not hasattr(player, "outskirts_dual_rapier_given"):
        player.outskirts_dual_rapier_given = False
    if not hasattr(player, "has_seen_outskirts_intro"):
        player.has_seen_outskirts_intro = False

    if not hasattr(player, "outskirts_horde_chest_opened_list"):
        if getattr(player, "outskirts_horde_chest_opened", False):
            player.outskirts_horde_chest_opened_list = [True] * TOTAL_HORDES
        else:
            player.outskirts_horde_chest_opened_list = [False] * TOTAL_HORDES
    while len(player.outskirts_horde_chest_opened_list) < TOTAL_HORDES:
        player.outskirts_horde_chest_opened_list.append(False)

    while len(player.outskirts_horde_defeated_list) < TOTAL_HORDES:
        player.outskirts_horde_defeated_list.append(False)

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

    mobs, markers = _spawn_mobs_from_grid()
    wizard = mobs.get("wizard_oz")

    def _visible_markers():
        if player.outskirts_horde_defeated:
            return []
        if player.outskirts_wizard_state != "TALKED":
            return []
        out = []
        for i, m in enumerate(markers):
            if i < len(player.outskirts_horde_defeated_list) \
                    and player.outskirts_horde_defeated_list[i]:
                continue
            out.append((i, m))
        return out

    visible_pairs = _visible_markers()
    _reload_character_sprites(player, wizard, [m for (_, m) in visible_pairs])

    active_mobs = [wizard] + [m for (_, m) in visible_pairs]
    _apply_hitbox_setting(player, active_mobs, all_deco_objects)

    player_name = getattr(player, "name", "Solaris")
    frame.title_text = f"{player_name}: Knight of the Crescent Moon"

    static_obstacles = []
    for obj in all_deco_objects:
        if hasattr(obj, "hitbox"):
            static_obstacles.append(obj.hitbox)
    for wall_rect in BORDER_WALLS:
        static_obstacles.append(wall_rect)

    horde_chests = [None] * TOTAL_HORDES
    for idx, marker in enumerate(markers):
        if idx >= TOTAL_HORDES:
            break
        if idx >= len(player.outskirts_horde_defeated_list):
            continue
        if not player.outskirts_horde_defeated_list[idx]:
            continue
        if idx < len(player.outskirts_horde_chest_opened_list) \
                and player.outskirts_horde_chest_opened_list[idx]:
            continue
        horde_chests[idx] = Chest(x=marker.x, y=marker.y,
                                  loot=roll_chest_loot(),
                                  label=f"Horde {idx + 1} Cache")

    COLOR_GRASS = (80, 120, 60)
    COLOR_GOLD = (255, 215, 0)
    COLOR_WARN = (255, 170, 90)

    last_outline_state = getattr(game_manager, "outline_enabled", True)
    warn_timer = 0.0
    warn_message = "The Mystic Forest is not yet open."

    dialogue_intro = [
        {"speaker": "Wizard Oz",
         "text": f"There you are, {player_name}. This is the Outskirts."},
        {"speaker": "Wizard Oz",
         "text": "West of here lies the Mystic Forest - your true trial."},
        {"speaker": "Wizard Oz",
         "text": "But the way is blocked. Three hordes have taken the western path."},
        {"speaker": player_name, "text": "Then I'll cut through them."},
        {"speaker": "Wizard Oz",
         "text": "Good. Clear them out, and the road will be yours."},
    ]

    dialogue_dual_rapier = [
        {"speaker": "Wizard Oz",
         "text": "The hordes are broken. Well fought."},
        {"speaker": "Wizard Oz",
         "text": "Take this - a rapier for your off-hand."},
        {"speaker": "SYSTEM",
         "text": "[Gained Dual Rapier!]"},
        {"speaker": "Wizard Oz",
         "text": "Its passives feed your main blade. Wield it well."},
        {"speaker": "Wizard Oz",
         "text": "Ahead lies the Mystic Forest. Gorgona's royal"},
        {"speaker": "Wizard Oz",
         "text": "guard patrols it - fox-spirits, tengu, and worse."},
        {"speaker": "Wizard Oz",
         "text": "Rest while you can. They will not fall easily."},
    ]

    dialogue_after_horde = [
        {"speaker": "Wizard Oz",
         "text": "Rest while you can. The Mystic Forest will not go easy on you."},
    ]

    dialogue_repeat = [
        {"speaker": "Wizard Oz",
         "text": "The hordes still block the western path. Clear them out."},
    ]

    world_surface.fill(COLOR_GRASS)
    castle_floor.draw(world_surface)
    if WORLD_HEIGHT > 720:
        extra_h = WORLD_HEIGHT - 720
        tile = world_surface.subsurface(pygame.Rect(0, 0, 1280, extra_h)).copy()
        world_surface.blit(tile, (0, 720))

    for obj in sorted(all_deco_objects,
                      key=lambda o: o.hitbox.bottom if hasattr(o, "hitbox") else o.rect.bottom):
        obj.draw(world_surface)
    for (_, m) in visible_pairs:
        m.draw(world_surface)
    if wizard is not None:
        wizard.draw(world_surface)
    player.draw(world_surface)
    draw_borders(world_surface)

    viewport = frame.get_viewport()
    viewport.blit(world_surface, (0, 0), pygame.Rect(0, 0, 1280, VIEWPORT_H))

    if (entry_from == "castle"
            and not getattr(player, "has_seen_outskirts_intro", False)):
        play_zoom_intro(screen, frame, player, world_surface, WORLD_HEIGHT,
                        duration_sec=1.8, start_zoom=1.8, hold_peak_sec=0.15,
                        particles=particles)
        player.has_seen_outskirts_intro = True

    running = True
    gameplay_signal = None
    smooth_cam_y = None

    while running:
        dt = clock.tick(60) / 1000.0
        dt = min(dt, 0.05)

        for idx, h_chest in enumerate(horde_chests):
            if h_chest is None:
                continue
            h_chest.update(dt)
            if getattr(h_chest, "looted", False) and h_chest.is_opened():
                horde_chests[idx] = None

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

                elif event.key == pygame.K_e:
                    opened_chest = False
                    for idx, h_chest in enumerate(horde_chests):
                        if h_chest is None:
                            continue
                        if h_chest.can_interact(player):
                            opened_flag = (idx < len(player.outskirts_horde_chest_opened_list)
                                           and player.outskirts_horde_chest_opened_list[idx])
                            if not opened_flag:
                                h_chest.open()
                                h_chest.looted = True
                                for item_id in h_chest.loot:
                                    give_item_by_id(player, item_id)
                                if idx < len(player.outskirts_horde_chest_opened_list):
                                    player.outskirts_horde_chest_opened_list[idx] = True
                            opened_chest = True
                            break

                    if not opened_chest and wizard is not None and wizard.can_interact(player):
                        bg_snapshot = screen.copy()
                        if player.outskirts_horde_defeated:
                            if not getattr(player, "outskirts_dual_rapier_given", False):
                                give_outskirts_reward(player)
                                player.outskirts_dual_rapier_given = True
                                run_dialogue(screen, dialogue_dual_rapier, bg_snapshot)
                            else:
                                run_dialogue(screen, dialogue_after_horde, bg_snapshot)
                        elif player.outskirts_wizard_state == "NEW":
                            run_dialogue(screen, dialogue_intro, bg_snapshot)
                            player.outskirts_wizard_state = "TALKED"
                            _reload_character_sprites(
                                player, wizard,
                                [m for (_, m) in _visible_markers()])
                        else:
                            run_dialogue(screen, dialogue_repeat, bg_snapshot)

        current_outline_state = getattr(game_manager, "outline_enabled", True)
        if current_outline_state != last_outline_state:
            last_outline_state = current_outline_state
            _reload_character_sprites(
                player, wizard, [m for (_, m) in _visible_markers()])

        visible_pairs = _visible_markers()
        active_mobs = [wizard] + [m for (_, m) in visible_pairs]
        _apply_hitbox_setting(player, active_mobs, all_deco_objects)

        frame_obstacles = list(static_obstacles)
        if wizard is not None:
            frame_obstacles.append(wizard.hitbox)
        for h_chest in horde_chests:
            if h_chest is not None:
                frame_obstacles.append(h_chest.rect)

        player.update(viewport_width=1280, viewport_height=WORLD_HEIGHT,
                      obstacles=frame_obstacles)

        if wizard is not None:
            wizard.update(delta_time=dt, player=player)
        for (_, m) in visible_pairs:
            m.update(delta_time=dt, player=player)

        if (visible_pairs
                and not player.outskirts_horde_defeated
                and player.outskirts_wizard_state == "TALKED"):
            for (idx, marker) in visible_pairs:
                if marker.is_player_detected(player) and marker.triggered_battle:
                    marker.triggered_battle = False

                    play_warning_sfx()

                    horde_waves = _build_horde_by_index(idx)
                    result = run_multi_battle(screen, player, horde_waves, slot_id=slot_id)

                    if result == "VICTORY":
                        if idx < len(player.outskirts_horde_defeated_list):
                            player.outskirts_horde_defeated_list[idx] = True

                        if idx < TOTAL_HORDES and idx < len(markers):
                            horde_chests[idx] = Chest(
                                x=markers[idx].x, y=markers[idx].y,
                                loot=roll_chest_loot(),
                                label=f"Horde {idx + 1} Cache")

                        if all(player.outskirts_horde_defeated_list):
                            _play_outskirts_cutscene(player_name, screen)
                            player.outskirts_horde_defeated = True
                    break

        player_center = (player.x, player.y - PLAYER_HITBOX_CENTER_TO_FEET)

        horde_done = bool(player.outskirts_horde_defeated)

        for zone_data in TRANSFER_ZONES.values():
            zr = zone_rect(zone_data)
            if not zr.collidepoint(player_center):
                continue

            gate = zone_data.get("gate", "")
            gate_ok = True
            if gate == "horde_done":
                gate_ok = horde_done

            if gate_ok:
                running = False
                gameplay_signal = zone_data["target"]
                break
            else:
                warn_timer = 2.5
                warn_message = zone_data.get("gate_message",
                                             "The Mystic Forest is not yet open.")

        if running:
            for door_data in LOCKED_DOORS.values():
                zr = zone_rect(door_data)
                if zr.collidepoint(player_center):
                    warn_timer = 2.5
                    warn_message = door_data.get("message", "Locked.")

        world_surface.fill(COLOR_GRASS)
        castle_floor.draw(world_surface)

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

        for (_, m) in visible_pairs:
            draw_queue.append((m.rect.bottom, m))
        if wizard is not None:
            draw_queue.append((wizard.rect.bottom, wizard))
        for h_chest in horde_chests:
            if h_chest is not None:
                draw_queue.append((h_chest.rect.bottom, h_chest))
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
                player=player, wizard=None,
                orc=None, enemies=None)
            if pause_result == "QUIT_TO_MENU":
                running = False
                gameplay_signal = "QUIT_TO_MENU"
        elif frame_action == "STATS":
            run_stats_menu(screen, frame, player)

        prompt_drawn = False
        for h_chest in horde_chests:
            if h_chest is not None and h_chest.can_interact(player):
                cmd_box = pygame.Rect(40, 250, 240, 46)
                pygame.draw.rect(screen, (20, 25, 35), cmd_box, border_radius=6)
                pygame.draw.rect(screen, COLOR_GOLD, cmd_box, width=2, border_radius=6)
                prompt_surf = font_cmd.render("[E] Open chest", True, COLOR_GOLD)
                screen.blit(prompt_surf, prompt_surf.get_rect(center=cmd_box.center))
                prompt_drawn = True
                break

        if not prompt_drawn and wizard is not None and wizard.can_interact(player):
            cmd_box = pygame.Rect(40, 250, 240, 46)
            pygame.draw.rect(screen, (20, 25, 35), cmd_box, border_radius=6)
            pygame.draw.rect(screen, COLOR_GOLD, cmd_box, width=2, border_radius=6)
            prompt_surf = font_cmd.render("[E] Talk to Wizard Oz", True, COLOR_GOLD)
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

    return gameplay_signal