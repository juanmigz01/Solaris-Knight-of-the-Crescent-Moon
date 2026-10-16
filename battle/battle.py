
import os
import sys
import math
import random
import pygame
import importlib

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

try:
    from classes.status_effects import StatusManager
except ImportError:
    StatusManager = None


def load_project_class(class_name, modules):
    for mod_path in modules:
        try:
            mod = importlib.import_module(mod_path)
            if hasattr(mod, class_name):
                return getattr(mod, class_name)
        except ImportError:
            continue
    raise ImportError(f"Could not locate class '{class_name}'")


try:
    from Modules.button import Button, draw_corner_brackets
except ImportError:
    Button = load_project_class("Button", ["classes.button", "Modules.button", "button"])
    try:
        from Modules.button import draw_corner_brackets
    except ImportError:
        def draw_corner_brackets(surface, rect, color, length=24, thickness=3, offset=6):
            pass

try:
    from Modules.game_frame import GameFrame
except ImportError:
    GameFrame = load_project_class("GameFrame", ["classes.game_frame", "Modules.game_frame", "game_frame"])

try:
    from Modules.inv import draw_inventory_and_equipment, handle_inventory_click
except ImportError:
    draw_inventory_and_equipment = None
    handle_inventory_click = None

try:
    from Modules.stats_menu import run_stats_menu
except ImportError:
    run_stats_menu = None

try:
    from Modules.sound_manager import game_manager
except ImportError:
    game_manager = None


from battle_func import (
    SPLASH_DURATION, SPLASH_FADE_IN, SPLASH_FADE_OUT, SPLASH_CENTER,
    SPLASH_RISE_PIXELS, draw_splash_text,
    is_clicked,
    has_elemental_weapon, has_burst_weapon,
    get_main_weapon, get_off_weapon,
    element_multiplier, apply_weapon_status,
    try_trigger_burn_instantly,
    consume_stun_if_any,
    draw_stun_indicator,
    draw_potion_buffs_indicator,
    set_entity_animation, play_hurt_animation,
    play_start_transition,
    draw_scaled_combatant, draw_target_marker, draw_huds, get_enemy_layout,
    WEAPON_STATUS_CHANCE,
    OFF_HAND_STATUS_CHANCE,
    get_element_text_color, COLOR_WHITE,
    PLAYER_ACTION_COLOR, ENEMY_ACTION_COLOR,
    get_hurt_vignette,
    _atk_mult, _elem_atk_mult, _elem_dmg_bonus,
    _status_dmg_bonus,
    _defense_multiplier,
    _target_resistance_mult,
    _effective_player_atk, _effective_player_def,
    _strip_temp_potion_buffs,
    _tick_potion_buff_durations,
    _dedupe_status_msgs, _compute_quests,
    _handle_victory_drops,
    _draw_hurt_flash, _draw_low_hp_border,
    HURT_FLASH_DURATION,
    play_battle_end_banner,
    ScreenShake,
    _format_action_line,
    FloatingTextManager,
    get_element_float_color,
    get_status_float_color,
    FLOATING_STATUS_COLORS,
    FLOATING_POTION_COLORS,
    JuiceManager,
    _size_from_damage,
    get_burst_flash_color,
    _flash_surface,
    _STATUS_NAME_TO_LETTER,
    play_skill_sfx,
    get_element_sfx,
    get_skill_sfx,
    play_status_sfx,
    play_heal_sfx,
    play_buff_sfx,
    play_missed_sfx,
    play_roar_sfx,
)


VIEWPORT_OFFSET_X = 320
VIEWPORT_OFFSET_Y = 180
ELEM_CHARGES_MAX  = 10
BURST_CHARGES_MAX = 5

ENEMY_STATUS_CHANCE = 0.70

ENEMY_ATTACK_LEAD_MS  = 400
PLAYER_ATTACK_LEAD_MS = 400
PLAYER_HURT_REVERT_MS = 500

TURN_PAUSE_MS = 1000

_PLAYER_HURT_ANIMS = ("hurt", "damage", "hit", "takehit", "damaged")

BATTLE_MUSIC_NAME    = "battle.mp3"
BATTLE_MUSIC_VOLUME  = 0.55
HURT_SFX_NAME        = "hurt.mp3"
HURT_SFX_PLAYER_VOL  = 0.50
HURT_SFX_ENEMY_VOL   = 0.35

HITSTOP_BURST_MS       = 120
BURST_FLASH_DURATION   = 0.16
HIT_SHAKE_DURATION     = 0.35
HIT_FLASH_DURATION     = 0.12
KILL_FADE_DURATION     = 0.70
ENEMY_INTRO_DURATION   = 0.35
DT_CLAMP               = 0.06

SKILL_SFX_PLAYER_VOL  = 0.55
SKILL_SFX_BURST_VOL   = 0.65
SKILL_SFX_ENEMY_VOL   = 0.50
STATUS_SFX_VOL        = 0.40
BUFF_SFX_VOL          = 0.45
HEAL_SFX_VOL          = 0.55
MISSED_SFX_VOL        = 0.45

HEALING_FLOAT_COLOR   = (120, 255, 140)


DEFAULT_BURST = {
    "name": "Elemental Burst", "type": "aoe",
    "damage_mult": 1.5, "status": None,
}


def _weapon_damage_blocked(target, weapon):
    allowed = getattr(target, "allowed_weapons", None)
    if allowed is None:
        return False
    if weapon is None:
        return True
    wid = getattr(weapon, "id_name", "")
    return wid not in allowed


def _weapon_has_true_damage(weapon):
    if weapon is None:
        return False
    special = getattr(weapon, "special_effects", {}) or {}
    return bool(special.get("true_damage", False))


def _weapon_has_moon_damage(weapon):

    if weapon is None:
        return False
    special = getattr(weapon, "special_effects", {}) or {}
    return bool(special.get("moon_damage", False))


def _is_gorgona(target):

    if target is None:
        return False
    return getattr(target, "name", "").strip().lower() == "gorgona"


_DEFAULT_TINT_CACHE = {}


def _get_default_battle_tint(w, h):

    key = (w, h)
    if key in _DEFAULT_TINT_CACHE:
        return _DEFAULT_TINT_CACHE[key]
    try:
        from Modules.particles import make_midnight_overlay
        tint = make_midnight_overlay(w, h)
    except Exception as e:
        print(f"[Battle] default tint failed: {e}")
        tint = None
    _DEFAULT_TINT_CACHE[key] = tint
    return tint


def _sync_stun_outlines(enemies, enemy_statuses):
    for i, enemy in enumerate(enemies):
        st = enemy_statuses[i] if i < len(enemy_statuses) else None
        stunned = st is not None and st.stacks.get("stun", 0) > 0
        if hasattr(enemy, "set_stunned"):
            enemy.set_stunned(stunned)


def _build_enemy_queue(enemies, attackers_override):
    alive = [e for e in enemies if e.hp > 0]
    if not alive:
        return []

    num_alive = len(alive)
    if attackers_override is None:
        num_attackers = 1 if num_alive <= 2 else 2
        num_attackers = min(num_attackers, num_alive)
        return random.sample(alive, num_attackers)
    if isinstance(attackers_override, int):
        num_attackers = min(attackers_override, num_alive)
        return random.sample(alive, num_attackers)
    if isinstance(attackers_override, (list, tuple)):
        return [enemies[i] for i in attackers_override
                if 0 <= i < len(enemies) and enemies[i].hp > 0]
    return random.sample(alive, 1)


def _play_hurt_sfx(volume):
    if game_manager is None:
        return
    try:
        game_manager.play_sfx(HURT_SFX_NAME, volume=volume)
    except Exception:
        pass


def _float_pos_for(target, enemies, player):
    if target is player:
        return (300, 420)
    try:
        idx = enemies.index(target)
    except (ValueError, AttributeError):
        return (640, 360)
    layout = get_enemy_layout(len(enemies))
    if 0 <= idx < len(layout):
        tx, ty, _ = layout[idx]
        return (tx, ty - 50)
    return (640, 360)


def _queue_float(pending, target, text, color, at_time, size=None):
    pending.append({
        "target": target,
        "text": str(text),
        "color": color,
        "at": at_time,
        "size": size,
    })


def _apply_hit_juice(target, shake=HIT_SHAKE_DURATION, flash=HIT_FLASH_DURATION):
    target._battle_shake_timer = max(
        getattr(target, "_battle_shake_timer", 0.0), shake)
    target._battle_hit_flash_timer = max(
        getattr(target, "_battle_hit_flash_timer", 0.0), flash)


def _tick_juice(entity, dt):
    if getattr(entity, "_battle_shake_timer", 0) > 0:
        entity._battle_shake_timer = max(0.0, entity._battle_shake_timer - dt)
    if getattr(entity, "_battle_hit_flash_timer", 0) > 0:
        entity._battle_hit_flash_timer = max(0.0, entity._battle_hit_flash_timer - dt)
    if getattr(entity, "_battle_fade_active", False):
        entity._battle_fade_timer = max(0.0, entity._battle_fade_timer - dt)
    if getattr(entity, "_battle_intro_active", False):
        entity._battle_intro_timer = min(
            entity._battle_intro_duration,
            entity._battle_intro_timer + dt)
        if entity._battle_intro_timer >= entity._battle_intro_duration:
            entity._battle_intro_active = False


_STATUS_KEY_MAP = {
    "Burn": "burn", "Bleed": "bleed", "Poison": "poison",
    "Blue Flame": "blue_flame", "Weak": "weak", "Stun": "stun",
    "Healing": "healing",
}


def _spawn_status_pops(juice, added_list, target, enemies, player):
    if not added_list:
        return
    try:
        idx = enemies.index(target)
        end_xy = (1200, 30 + idx * 66 + 42)
    except (ValueError, AttributeError):
        end_xy = (110, 90)
    start_xy = _float_pos_for(target, enemies, player)
    for entry in added_list:
        if not isinstance(entry, tuple) or len(entry) < 2:
            continue
        name = entry[0]
        sk = _STATUS_KEY_MAP.get(name)
        if not sk:
            continue
        letter = _STATUS_NAME_TO_LETTER.get(name, name[0])
        color = FLOATING_STATUS_COLORS.get(sk, (255, 255, 255))
        juice.spawn_status_pop(letter, color, start_xy, end_xy)


def _extend_status_with_pops(target, added, status_list, juice, enemies, player):
    if not added:
        return
    status_list.extend(added)
    _spawn_status_pops(juice, added, target, enemies, player)


def _enemy_move_sfx(enemy_move, attacker):

    if not enemy_move:
        return "thud.mp3"
    if enemy_move.get("self_buff"):
        return "powerup.mp3"
    override = enemy_move.get("sfx")
    if override:
        return override
    move_name = enemy_move.get("name", "")
    sfx = get_skill_sfx(move_name)
    if sfx:
        return sfx
    return get_element_sfx(getattr(attacker, "element", None))


def _stop_walk_run_loops():
    if game_manager is None:
        return
    try:
        game_manager.stop_sfx("walk")
        game_manager.stop_sfx("run")
    except Exception:
        pass


def _ask_flee_confirmation(screen, title_font, body_font, btn_font):
    clock = pygame.time.Clock()
    screen_w, screen_h = screen.get_size()
    snapshot = screen.copy()

    COLOR_VOID   = (0, 0, 0)
    COLOR_GOLD   = (212, 175, 55)
    COLOR_BRIGHT = (255, 215, 0)
    COLOR_WHITE  = (240, 235, 210)
    COLOR_GRAY   = (150, 150, 170)
    COLOR_RED    = (220, 80, 80)
    COLOR_RED_H  = (255, 110, 110)
    COLOR_RED_BG = (70, 25, 35)
    COLOR_PANEL  = (35, 30, 60)
    COLOR_HOVER  = (60, 50, 95)

    panel_w, panel_h = 780, 340
    panel_rect = pygame.Rect(
        screen_w // 2 - panel_w // 2,
        screen_h // 2 - panel_h // 2,
        panel_w, panel_h,
    )

    btn_w, btn_h = 220, 66
    gap = 50
    total_w = btn_w * 2 + gap
    left_x = panel_rect.centerx - total_w // 2
    right_x = left_x + btn_w + gap
    btn_y = panel_rect.bottom - btn_h - 40

    run_btn  = pygame.Rect(left_x,  btn_y, btn_w, btn_h)
    stay_btn = pygame.Rect(right_x, btn_y, btn_w, btn_h)

    while True:
        clock.tick(60)
        mouse_pos = pygame.mouse.get_pos()

        screen.blit(snapshot, (0, 0))
        dim = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 195))
        screen.blit(dim, (0, 0))

        pygame.draw.rect(screen, COLOR_PANEL, panel_rect, border_radius=12)
        pygame.draw.rect(screen, COLOR_GOLD, panel_rect,
                         width=3, border_radius=12)
        try:
            draw_corner_brackets(screen, panel_rect, COLOR_GOLD,
                                 length=26, thickness=3, offset=8)
        except Exception:
            pass

        title = title_font.render("ARE YOU SURE?", True, COLOR_BRIGHT)
        screen.blit(title, title.get_rect(
            center=(panel_rect.centerx, panel_rect.top + 55)))

        line_y = panel_rect.top + 100
        pygame.draw.line(screen, COLOR_GOLD,
                         (panel_rect.left + 60, line_y),
                         (panel_rect.right - 60, line_y), 2)

        msg1 = body_font.render(
            "Running away will cause the current",
            True, COLOR_WHITE)
        msg2 = body_font.render(
            "enemies to regen to FULL HP.",
            True, COLOR_RED)
        screen.blit(msg1, msg1.get_rect(
            center=(panel_rect.centerx, panel_rect.top + 145)))
        screen.blit(msg2, msg2.get_rect(
            center=(panel_rect.centerx, panel_rect.top + 180)))

        for rect, label, base_col, hover_col, text_col in (
            (run_btn,  "RUN",  COLOR_RED_BG, COLOR_RED_H,  COLOR_RED),
            (stay_btn, "STAY", COLOR_PANEL,  COLOR_HOVER,  COLOR_GOLD),
        ):
            hovered = rect.collidepoint(mouse_pos)
            fill = hover_col if hovered else base_col
            pygame.draw.rect(screen, fill, rect, border_radius=8)
            pygame.draw.rect(screen, COLOR_GOLD, rect,
                             width=3, border_radius=8)
            col = COLOR_BRIGHT if hovered else text_col
            lbl = btn_font.render(label, True, col)
            screen.blit(lbl, lbl.get_rect(center=rect.center))

        hint = body_font.render(
            "[ R: RUN   |   S or ESC: STAY ]",
            True, COLOR_GRAY)
        screen.blit(hint, hint.get_rect(
            center=(panel_rect.centerx, panel_rect.bottom - 14)))

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if run_btn.collidepoint(event.pos):
                    return True
                if stay_btn.collidepoint(event.pos):
                    return False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    return True
                if event.key in (pygame.K_s, pygame.K_ESCAPE):
                    return False


def run_battle(screen, player, enemies, slot_id=1,
               attackers_override=None, charges=None,
               skip_intro=False, strip_temp_buffs=False,
               allow_flee=True, show_end_banner=True,
               viewport_particles=None, viewport_tint=None):

    if not isinstance(enemies, (list, tuple)):
        enemies = [enemies]
    enemies = [e for e in enemies if e is not None]
    if not enemies:
        return "VICTORY"

    if charges is None:
        charges = {"elem": ELEM_CHARGES_MAX, "burst": BURST_CHARGES_MAX}
    charges.setdefault("elem", ELEM_CHARGES_MAX)
    charges.setdefault("burst", BURST_CHARGES_MAX)

    clock = pygame.time.Clock()

    _stop_walk_run_loops()

    if game_manager is not None:
        try:
            game_manager.play_music(BATTLE_MUSIC_NAME, fade_ms=800,
                                    volume=BATTLE_MUSIC_VOLUME)
        except Exception as e:
            print(f"[Battle] battle music failed: {e}")

    shake = ScreenShake()

    juice = JuiceManager()
    pending_float_texts = []

    burst_flash_timer = 0.0
    burst_flash_color = (255, 255, 255)

    for e in enemies:
        e._battle_shake_timer = 0.0
        e._battle_fade_timer = 0.0
        e._battle_fade_active = False
        e._battle_intro_timer = 0.0
        e._battle_intro_duration = ENEMY_INTRO_DURATION
        e._battle_intro_active = True
        e._battle_hit_flash_timer = 0.0
    player._battle_shake_timer = 0.0
    player._battle_hit_flash_timer = 0.0

    if not hasattr(player_status_holder := player, "_battle_apply_self_status"):
        pass

    _saved_zoom = None
    if game_manager is not None:
        try:
            _saved_zoom = getattr(game_manager, "zoom_level", 1.0)
            game_manager.zoom_level = 1.0
        except Exception:
            _saved_zoom = None

    font_path = os.path.join(PROJECT_ROOT, "asset", "font", "TheGothicRite.otf")
    if os.path.exists(font_path):
        font_main  = pygame.font.Font(font_path, 22)
        font_large = pygame.font.Font(font_path, 32)
        font_big   = pygame.font.Font(font_path, 52)
        font_burst = pygame.font.Font(font_path, 78)
        font_btn   = pygame.font.Font(font_path, 18)
        font_modal_title = pygame.font.Font(font_path, 40)
        font_modal_btn   = pygame.font.Font(font_path, 24)
    else:
        font_main  = pygame.font.SysFont("Georgia", 22)
        font_large = pygame.font.SysFont("Georgia", 32)
        font_big   = pygame.font.SysFont("Georgia", 52)
        font_burst = pygame.font.SysFont("Georgia", 78, bold=True)
        font_btn   = pygame.font.SysFont("Georgia", 18, bold=True)
        font_modal_title = pygame.font.SysFont("Georgia", 40, bold=True)
        font_modal_btn   = pygame.font.SysFont("Georgia", 24, bold=True)

    frame = GameFrame(font_large=font_large, font_small=font_main)

    bg_img_path = os.path.join(PROJECT_ROOT, "asset", "img", "battle.png")
    battle_bg = None
    if os.path.exists(bg_img_path):
        battle_bg = pygame.image.load(bg_img_path).convert()
        battle_bg = pygame.transform.scale(battle_bg, (1280, 720))

    if not skip_intro:
        play_start_transition(screen, frame)

    btn_attack = Button(40, 240, 240, 45, text="ATTACK", font=font_btn)
    btn_elem_attack = Button(40, 295, 240, 45,
                             text=f"ELEM ({charges['elem']})", font=font_btn)
    btn_burst = Button(40, 350, 240, 45,
                       text=f"BURST ({charges['burst']})", font=font_btn)
    btn_run = Button(40, 405, 240, 45, text="RUN AWAY", font=font_btn)

    last_elem  = charges["elem"]
    last_burst = charges["burst"]

    ACTION_DELAY = 1000
    BATTLE_END_DELAY = 2000
    DEFEAT_END_DELAY = 3000

    battle_state, battle_result = "PLAYER_TURN", "FLED"
    enemy_statuses = [StatusManager() if StatusManager else None for _ in enemies]
    player_status = StatusManager() if StatusManager else None
    target_index = 0

    if player_status is not None:
        def _apply_self_status(status_name, stacks, _st=player_status):
            _st.add_status(status_name, stacks)
        try:
            player._battle_apply_self_status = _apply_self_status
        except Exception:
            pass

    if len(enemies) == 1:
        message_text = f"A wild {getattr(enemies[0], 'name', 'Enemy')} appeared! Prepare for battle!"
    else:
        message_text = f"{len(enemies)} enemies appeared! Prepare for battle!"

    message_color = COLOR_WHITE

    action_timer = 0
    splash_text = ""
    splash_timer = 0.0
    splash_is_burst = False
    splash_color = None
    enemy_queue = []
    enemy_queue_idx = 0
    enemy_rects = [None] * len(enemies)

    player_hurt_flash_timer = 0.0
    hurt_played_this_turn = False

    pending_player_hurt_at = 0
    pending_player_hurt_active = False
    pending_enemy_hurts = []

    player_hurt_revert_at = 0

    elapsed_time = 0.0

    current_quests = _compute_quests(player)

    if hasattr(player, "can_move"):
        player.can_move = False
    for combatant in [player] + list(enemies):
        if hasattr(combatant, "set_animation"):
            combatant.set_animation("idle")

    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        dt = min(dt, DT_CLAMP)
        elapsed_time += dt
        current_time = pygame.time.get_ticks()
        mouse_pos = pygame.mouse.get_pos()

        shake.update(dt)

        if player_hurt_flash_timer > 0:
            player_hurt_flash_timer = max(0.0, player_hurt_flash_timer - dt)

        if player_hurt_revert_at > 0 and current_time >= player_hurt_revert_at:
            if (hasattr(player, "set_animation")
                    and player.hp > 0
                    and getattr(player, "current_animation", "") in _PLAYER_HURT_ANIMS):
                player.set_animation("idle")
            player_hurt_revert_at = 0

        if pending_player_hurt_active and current_time >= pending_player_hurt_at:
            player_hurt_flash_timer = HURT_FLASH_DURATION
            if hasattr(player, "set_animation") and player.hp > 0:
                play_hurt_animation(player)
                player_hurt_revert_at = current_time + PLAYER_HURT_REVERT_MS
            _play_hurt_sfx(HURT_SFX_PLAYER_VOL)
            pending_player_hurt_active = False

        if pending_enemy_hurts:
            still_pending = []
            for entry in pending_enemy_hurts:
                if current_time >= entry["at"]:
                    target = entry["enemy"]
                    if getattr(target, "hp", 0) > 0:
                        play_hurt_animation(target)
                        _play_hurt_sfx(HURT_SFX_ENEMY_VOL)
                else:
                    still_pending.append(entry)
            pending_enemy_hurts = still_pending

        if pending_float_texts:
            still_pending = []
            for entry in pending_float_texts:
                if current_time >= entry["at"]:
                    target = entry["target"]
                    base_x, base_y = _float_pos_for(target, enemies, player)
                    ox = random.randint(-70, 70)
                    oy = random.randint(-35, 25)
                    juice.spawn_float(
                        entry["text"],
                        base_x + ox,
                        base_y + oy,
                        entry["color"],
                        size=entry.get("size"),
                    )
                else:
                    still_pending.append(entry)
            pending_float_texts = still_pending

        for e in enemies:
            _tick_juice(e, dt)
        _tick_juice(player, dt)

        if burst_flash_timer > 0:
            burst_flash_timer = max(0.0, burst_flash_timer - dt)

        for e in enemies:
            if e.hp <= 0 and not getattr(e, "_battle_fade_active", False):
                e._battle_fade_active = True
                e._battle_fade_timer = KILL_FADE_DURATION
                e._battle_shake_timer = 0.0
                e._battle_intro_active = False

        juice.update(dt)

        can_elem  = has_elemental_weapon(player)
        can_burst = has_burst_weapon(player)

        viewport_mouse = (mouse_pos[0] - VIEWPORT_OFFSET_X,
                          mouse_pos[1] - VIEWPORT_OFFSET_Y)

        if charges["elem"] != last_elem:
            btn_elem_attack = Button(40, 295, 240, 45,
                                     text=f"ELEM ({charges['elem']})", font=font_btn)
            last_elem = charges["elem"]
        if charges["burst"] != last_burst:
            btn_burst = Button(40, 350, 240, 45,
                               text=f"BURST ({charges['burst']})", font=font_btn)
            last_burst = charges["burst"]

        show_elem  = can_elem  and charges["elem"]  > 0
        show_burst = can_burst and charges["burst"] > 0

        y = 240
        btn_attack.rect.y = y
        y += 55
        if show_elem:
            btn_elem_attack.rect.y = y
            y += 55
        if show_burst:
            btn_burst.rect.y = y
            y += 55
        if allow_flee:
            btn_run.rect.y = y

        if splash_timer > 0:
            splash_timer = max(0.0, splash_timer - dt)

        if battle_state != "BATTLE_OVER":
            alive_idxs = [i for i, e in enumerate(enemies) if e.hp > 0]
            if not alive_idxs:
                battle_state = "BATTLE_OVER"
                battle_result = "VICTORY"
                message_text = "All enemies defeated!"
                message_color = COLOR_WHITE
                action_timer = current_time + BATTLE_END_DELAY
            elif target_index not in alive_idxs:
                target_index = alive_idxs[0]

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_c and run_stats_menu:
                    run_stats_menu(screen, frame, player)

            if (battle_state == "PLAYER_TURN"
                    and event.type == pygame.MOUSEBUTTONDOWN
                    and event.button == 1):

                if is_clicked(btn_attack, mouse_pos):
                    play_skill_sfx("slash.mp3", volume=SKILL_SFX_PLAYER_VOL)

                    if hasattr(player, "set_animation"):
                        player.set_animation("attack1")

                    target = enemies[target_index] if target_index < len(enemies) else None
                    if target is None or target.hp <= 0:
                        for i, e in enumerate(enemies):
                            if e.hp > 0:
                                target = e; target_index = i
                                break

                    if target is not None and target.hp > 0:
                        main_w = get_main_weapon(player)
                        off_w = get_off_weapon(player)

                        p_atk = int(_effective_player_atk(player) * (1.0 + _atk_mult(player)))
                        e_def = getattr(target, "defense", 0)
                        def_mult = _defense_multiplier(e_def)

                        if _weapon_has_true_damage(main_w) or _weapon_has_moon_damage(main_w):
                            def_mult = 1.0

                        raw_dmg = p_atk + random.randint(0, 3)
                        if main_w:
                            try:
                                w_phys, w_elem = main_w.get_damage()
                                w_elem = int(w_elem * (1.0 + _elem_atk_mult(player)))
                                raw_dmg += w_phys + w_elem
                            except Exception:
                                pass

                        base_dmg = max(1, int(raw_dmg * def_mult))

                        multiplier = 1.0
                        if main_w:
                            weapon_element = getattr(main_w, "element", "Neutral")
                            if _weapon_has_moon_damage(main_w):
                                multiplier = 1.0
                            else:
                                enemy_element = getattr(target, "element", None)
                                multiplier = element_multiplier(weapon_element, enemy_element)
                                multiplier *= _target_resistance_mult(target, weapon_element)
                                mult_bonus = _elem_dmg_bonus(player, weapon_element)
                                if mult_bonus:
                                    multiplier *= (1.0 + mult_bonus)

                        dmg = max(1, int(base_dmg * multiplier + 0.5))

                        if main_w and _weapon_has_moon_damage(main_w) and _is_gorgona(target):
                            dmg *= 2

                        blocked = _weapon_damage_blocked(target, main_w)
                        if blocked:
                            dmg = 0
                            play_missed_sfx(volume=MISSED_SFX_VOL)

                        target.hp = max(0, target.hp - dmg)

                        if dmg > 0:
                            _apply_hit_juice(target)
                            _queue_float(
                                pending_float_texts, target, dmg,
                                get_element_float_color(
                                    getattr(main_w, "element", "Neutral")
                                    if main_w else "Neutral"),
                                current_time + PLAYER_ATTACK_LEAD_MS,
                                size=_size_from_damage(dmg),
                            )

                        status_list = []
                        t_status = enemy_statuses[target_index] if target_index < len(enemy_statuses) else None
                        if main_w and t_status is not None:
                            added = apply_weapon_status(main_w, t_status,
                                                        is_off_hand=False,
                                                        is_basic=True,
                                                        other_weapon=off_w)
                            if added:
                                play_status_sfx(volume=STATUS_SFX_VOL)
                            _extend_status_with_pops(target, added, status_list,
                                                     juice, enemies, player)
                        if off_w and t_status is not None:
                            added = apply_weapon_status(off_w, t_status,
                                                        is_off_hand=True,
                                                        is_basic=True,
                                                        other_weapon=main_w)
                            if added:
                                play_status_sfx(volume=STATUS_SFX_VOL)
                            _extend_status_with_pops(target, added, status_list,
                                                     juice, enemies, player)

                        burn_dmg = 0
                        if t_status is not None:
                            burn_dmg = try_trigger_burn_instantly(main_w, t_status, target)

                        if burn_dmg > 0:
                            _queue_float(
                                pending_float_texts, target, burn_dmg,
                                FLOATING_STATUS_COLORS["burn"],
                                current_time + PLAYER_ATTACK_LEAD_MS,
                                size=_size_from_damage(burn_dmg),
                            )

                        display_dmg = dmg + burn_dmg
                        message_color = PLAYER_ACTION_COLOR

                        if target.hp > 0:
                            pending_enemy_hurts.append({
                                "enemy": target,
                                "at": current_time + PLAYER_ATTACK_LEAD_MS,
                            })

                        if blocked:
                            message_text = "ATTACK: 0"
                        else:
                            message_text = _format_action_line(
                                "ATTACK", display_dmg, status_list)

                        battle_state = "PLAYER_ATTACKING"
                        action_timer = current_time + ACTION_DELAY

                elif (can_elem and charges["elem"] > 0
                        and is_clicked(btn_elem_attack, mouse_pos)):
                    charges["elem"] -= 1
                    if hasattr(player, "set_animation"):
                        player.set_animation("attack2")

                    main_w = get_main_weapon(player)
                    off_w = get_off_weapon(player)

                    weapon_element = getattr(main_w, "element", "Neutral") if main_w else "Neutral"

                    play_skill_sfx(get_element_sfx(weapon_element),
                                   volume=SKILL_SFX_PLAYER_VOL)

                    message_color = PLAYER_ACTION_COLOR

                    p_elem = int(getattr(player, "elemental_attack", 0)
                                 * (1.0 + _elem_atk_mult(player)))
                    old_base = max(10, p_elem) + random.randint(5, 12)
                    if main_w:
                        try:
                            _, w_elem = main_w.get_damage()
                            old_base += w_elem
                        except Exception:
                            pass
                    base_dmg = max(1, old_base // 2)

                    total_dmg = 0
                    status_list = []

                    for i, enemy in enumerate(enemies):
                        if enemy.hp <= 0:
                            continue

                        e_def = getattr(enemy, "defense", 0)
                        def_mult = _defense_multiplier(e_def)
                        if _weapon_has_true_damage(main_w) or _weapon_has_moon_damage(main_w):
                            def_mult = 1.0

                        multiplier = 1.0
                        if main_w:
                            if _weapon_has_moon_damage(main_w):
                                multiplier = 1.0
                            else:
                                enemy_element = getattr(enemy, "element", None)
                                multiplier = element_multiplier(weapon_element, enemy_element)
                                multiplier *= _target_resistance_mult(enemy, weapon_element)
                                mult_bonus = _elem_dmg_bonus(player, weapon_element)
                                if mult_bonus:
                                    multiplier *= (1.0 + mult_bonus)

                        dmg = max(1, int(base_dmg * def_mult * multiplier + 0.5))

                        if main_w and _weapon_has_moon_damage(main_w) and _is_gorgona(enemy):
                            dmg *= 2

                        if _weapon_damage_blocked(enemy, main_w):
                            dmg = 0
                        enemy.hp = max(0, enemy.hp - dmg)
                        total_dmg += dmg

                        if dmg > 0:
                            _apply_hit_juice(enemy)
                            _queue_float(
                                pending_float_texts, enemy, dmg,
                                get_element_float_color(weapon_element),
                                current_time + PLAYER_ATTACK_LEAD_MS,
                                size=_size_from_damage(dmg),
                            )

                        t_status = enemy_statuses[i]
                        if main_w:
                            added = apply_weapon_status(main_w, t_status,
                                                        is_off_hand=False,
                                                        other_weapon=off_w)
                            if added:
                                play_status_sfx(volume=STATUS_SFX_VOL)
                            _extend_status_with_pops(enemy, added, status_list,
                                                     juice, enemies, player)
                        if off_w:
                            added = apply_weapon_status(off_w, t_status,
                                                        is_off_hand=True,
                                                        other_weapon=main_w)
                            if added:
                                play_status_sfx(volume=STATUS_SFX_VOL)
                            _extend_status_with_pops(enemy, added, status_list,
                                                     juice, enemies, player)

                        if t_status is not None:
                            burn_dmg = try_trigger_burn_instantly(main_w, t_status, enemy)
                            if burn_dmg > 0:
                                total_dmg += burn_dmg
                                _queue_float(
                                    pending_float_texts, enemy, burn_dmg,
                                    FLOATING_STATUS_COLORS["burn"],
                                    current_time + PLAYER_ATTACK_LEAD_MS,
                                    size=_size_from_damage(burn_dmg),
                                )

                        if enemy.hp > 0:
                            pending_enemy_hurts.append({
                                "enemy": enemy,
                                "at": current_time + PLAYER_ATTACK_LEAD_MS,
                            })

                    message_text = _format_action_line(
                        "ELEMENTAL SLASH", total_dmg, status_list)

                    splash_text = "ELEMENTAL SLASH"
                    splash_is_burst = False
                    splash_color = get_element_text_color(weapon_element)
                    splash_timer = SPLASH_DURATION

                    battle_state = "PLAYER_ATTACKING"
                    action_timer = current_time + ACTION_DELAY

                elif (can_burst and charges["burst"] > 0
                        and is_clicked(btn_burst, mouse_pos)):
                    charges["burst"] -= 1
                    if hasattr(player, "set_animation"):
                        player.set_animation("attack2")

                    main_w = get_main_weapon(player)
                    off_w = get_off_weapon(player)

                    weapon_element = getattr(main_w, "element", "Neutral") if main_w else "Neutral"

                    play_skill_sfx("boom.mp3", volume=SKILL_SFX_BURST_VOL)

                    message_color = PLAYER_ACTION_COLOR

                    p_elem = int(getattr(player, "elemental_attack", 0)
                                 * (1.0 + _elem_atk_mult(player)))
                    base_dmg = max(10, p_elem) + random.randint(5, 12)
                    if main_w:
                        try:
                            _, w_elem = main_w.get_damage()
                            base_dmg += w_elem
                        except Exception:
                            pass

                    burst = getattr(main_w, "burst", None) if main_w else None
                    if not burst:
                        burst = DEFAULT_BURST

                    burst_name   = burst.get("name", "Elemental Burst")
                    burst_type   = burst.get("type", "aoe")
                    burst_mult   = float(burst.get("damage_mult", 1.5))
                    burst_status = burst.get("status")

                    if burst_type == "single":
                        if (0 <= target_index < len(enemies)
                                and enemies[target_index].hp > 0):
                            hit_indices = [target_index]
                        else:
                            alive = [i for i, e in enumerate(enemies) if e.hp > 0]
                            hit_indices = alive[:1]
                    else:
                        hit_indices = [i for i, e in enumerate(enemies) if e.hp > 0]

                    total_dmg = 0
                    status_list = []

                    for i in hit_indices:
                        enemy = enemies[i]
                        if enemy.hp <= 0:
                            continue

                        e_def = getattr(enemy, "defense", 0)
                        def_mult = _defense_multiplier(e_def)
                        if _weapon_has_true_damage(main_w) or _weapon_has_moon_damage(main_w):
                            def_mult = 1.0

                        multiplier = 1.0
                        if main_w:
                            if _weapon_has_moon_damage(main_w):
                                multiplier = 1.0
                            else:
                                enemy_element = getattr(enemy, "element", None)
                                multiplier = element_multiplier(weapon_element, enemy_element)
                                multiplier *= _target_resistance_mult(enemy, weapon_element)
                                mult_bonus = _elem_dmg_bonus(player, weapon_element)
                                if mult_bonus:
                                    multiplier *= (1.0 + mult_bonus)

                        dmg = max(1, int(base_dmg * burst_mult * def_mult * multiplier + 0.5))

                        if main_w and _weapon_has_moon_damage(main_w) and _is_gorgona(enemy):
                            dmg *= 2

                        if _weapon_damage_blocked(enemy, main_w):
                            dmg = 0
                        enemy.hp = max(0, enemy.hp - dmg)
                        total_dmg += dmg

                        if dmg > 0:
                            _apply_hit_juice(enemy)
                            _queue_float(
                                pending_float_texts, enemy, dmg,
                                get_element_float_color(weapon_element),
                                current_time + PLAYER_ATTACK_LEAD_MS,
                                size=_size_from_damage(dmg),
                            )

                        t_status = enemy_statuses[i]

                        if burst_status and t_status is not None:
                            if random.random() < WEAPON_STATUS_CHANCE:
                                b_key, b_stacks = burst_status
                                t_status.add_status(b_key, b_stacks)
                                status_list.append((b_key.capitalize(), b_stacks))
                                play_status_sfx(volume=STATUS_SFX_VOL)
                                _spawn_status_pops(
                                    juice, [(b_key.capitalize(), b_stacks)],
                                    enemy, enemies, player)

                        if main_w:
                            added = apply_weapon_status(main_w, t_status,
                                                        is_off_hand=False,
                                                        other_weapon=off_w)
                            if added:
                                play_status_sfx(volume=STATUS_SFX_VOL)
                            _extend_status_with_pops(enemy, added, status_list,
                                                     juice, enemies, player)
                        if off_w:
                            added = apply_weapon_status(off_w, t_status,
                                                        is_off_hand=True,
                                                        other_weapon=main_w)
                            if added:
                                play_status_sfx(volume=STATUS_SFX_VOL)
                            _extend_status_with_pops(enemy, added, status_list,
                                                     juice, enemies, player)

                        if t_status is not None:
                            burn_dmg = try_trigger_burn_instantly(main_w, t_status, enemy)
                            if burn_dmg > 0:
                                total_dmg += burn_dmg
                                _queue_float(
                                    pending_float_texts, enemy, burn_dmg,
                                    FLOATING_STATUS_COLORS["burn"],
                                    current_time + PLAYER_ATTACK_LEAD_MS,
                                    size=_size_from_damage(burn_dmg),
                                )

                        if enemy.hp > 0:
                            pending_enemy_hurts.append({
                                "enemy": enemy,
                                "at": current_time + PLAYER_ATTACK_LEAD_MS,
                            })

                    message_text = _format_action_line(
                        burst_name, total_dmg, status_list)

                    splash_text = burst_name
                    splash_is_burst = True
                    splash_color = get_element_text_color(weapon_element)
                    splash_timer = SPLASH_DURATION

                    if total_dmg > 0:
                        intensity = min(18.0, 7.0 + total_dmg * 0.22)
                        shake.trigger(intensity=intensity, duration=0.32)
                        burst_flash_timer = BURST_FLASH_DURATION
                        burst_flash_color = get_burst_flash_color(weapon_element)
                        try:
                            _flash_surface(screen, burst_flash_color, 0.85)
                            pygame.display.flip()
                            pygame.time.delay(HITSTOP_BURST_MS)
                        except Exception:
                            pass
                    else:
                        shake.trigger(intensity=8.0, duration=0.28)

                    battle_state = "PLAYER_ATTACKING"
                    action_timer = current_time + ACTION_DELAY

                elif allow_flee and is_clicked(btn_run, mouse_pos):
                    confirmed = _ask_flee_confirmation(
                        screen,
                        title_font=font_modal_title,
                        body_font=font_main,
                        btn_font=font_modal_btn,
                    )

                    if confirmed:
                        for e in enemies:
                            if getattr(e, "hp", 0) > 0:
                                max_hp = getattr(e, "max_hp", None)
                                if max_hp is not None:
                                    e.hp = max_hp

                        battle_result = "FLED"
                        running = False

                else:
                    clicked_target = None
                    for i, rect in enumerate(enemy_rects):
                        if rect is None or enemies[i].hp <= 0:
                            continue
                        if rect.collidepoint(viewport_mouse):
                            clicked_target = i
                            break

                    if clicked_target is not None:
                        target_index = clicked_target
                    elif handle_inventory_click:
                        hp_before  = player.hp
                        atk_before = getattr(player, "temp_atk_bonus", 0)
                        def_before = getattr(player, "temp_def_bonus", 0)

                        item_msg = handle_inventory_click(mouse_pos, player, frame)

                        hp_after  = player.hp
                        atk_after = getattr(player, "temp_atk_bonus", 0)
                        def_after = getattr(player, "temp_def_bonus", 0)

                        if hp_after > hp_before:
                            healed = hp_after - hp_before
                            play_heal_sfx(volume=HEAL_SFX_VOL)
                            _queue_float(
                                pending_float_texts, player,
                                f"+{healed}",
                                FLOATING_POTION_COLORS["heal"],
                                current_time + 100,
                                size=_size_from_damage(healed, base_min=24,
                                                       base_max=42, scale=0.6),
                            )
                            juice.spawn_heal_sparkles(count=14,
                                                      base_x=300, base_y=420)

                        if player_status is not None and \
                                player_status.stacks.get("healing", 0) > 0:
                            pass

                        if atk_after > atk_before:
                            _queue_float(
                                pending_float_texts, player, "ATK+",
                                FLOATING_POTION_COLORS["atk"],
                                current_time + 100,
                                size=30,
                            )
                        if def_after > def_before:
                            _queue_float(
                                pending_float_texts, player, "DEF+",
                                FLOATING_POTION_COLORS["def"],
                                current_time + 100,
                                size=30,
                            )
                        if atk_after > atk_before or def_after > def_before:
                            play_buff_sfx(volume=BUFF_SFX_VOL)

                        if item_msg:
                            message_text = item_msg
                            message_color = COLOR_WHITE

        if battle_state == "PLAYER_ATTACKING" and current_time >= action_timer:
            if hasattr(player, "set_animation") and player.hp > 0:
                player.set_animation("idle")

            alive = [e for e in enemies if e.hp > 0]
            if not alive:
                battle_state = "BATTLE_OVER"
                battle_result = "VICTORY"
                message_text = "All enemies defeated!"
                message_color = COLOR_WHITE
                action_timer = current_time + BATTLE_END_DELAY
            else:
                enemy_queue = _build_enemy_queue(enemies, attackers_override)
                pending_enemy_hurts.clear()
                hurt_played_this_turn = False
                pending_player_hurt_active = False
                enemy_queue_idx = 0
                battle_state = "ENEMY_ATTACKING"
                action_timer = current_time + TURN_PAUSE_MS

        elif battle_state == "PLAYER_TURN_WAIT" and current_time >= action_timer:
            player_stunned = (
                player_status is not None
                and player_status.stacks.get("stun", 0) > 0
            )

            if player_stunned:
                player_status.stacks["stun"] = max(
                    0, player_status.stacks["stun"] - 1)
                remaining = player_status.stacks.get("stun", 0)

                if remaining > 0:
                    message_text = (f"{player.name} is stunned and cannot move! "
                                    f"({remaining} turn left)")
                else:
                    message_text = f"{player.name} is stunned and cannot move!"
                message_color = (200, 230, 255)
                splash_text = "STUNNED"
                splash_is_burst = False
                splash_color = (200, 230, 255)
                splash_timer = SPLASH_DURATION

                if hasattr(player, "set_animation"):
                    player.set_animation("idle")

                alive = [e for e in enemies if e.hp > 0]
                if not alive:
                    battle_state = "BATTLE_OVER"
                    battle_result = "VICTORY"
                    message_text = "All enemies defeated!"
                    message_color = COLOR_WHITE
                    action_timer = current_time + BATTLE_END_DELAY
                else:
                    enemy_queue = _build_enemy_queue(enemies, attackers_override)
                    pending_enemy_hurts.clear()
                    hurt_played_this_turn = False
                    pending_player_hurt_active = False
                    enemy_queue_idx = 0
                    battle_state = "ENEMY_ATTACKING"
                    action_timer = current_time + TURN_PAUSE_MS
            else:
                _tick_potion_buff_durations(player)
                battle_state = "PLAYER_TURN"

        elif battle_state == "ENEMY_ATTACKING" and current_time >= action_timer:

            if player.hp <= 0:
                battle_state = "BATTLE_OVER"
                battle_result = "DEFEAT"
                message_text = f"{player.name} was defeated..."
                message_color = COLOR_WHITE
                action_timer = current_time + DEFEAT_END_DELAY
                set_entity_animation(player, "death", "dead", "die", "defeat")
                pending_player_hurt_active = False

            elif enemy_queue_idx < len(enemy_queue):
                attacker = enemy_queue[enemy_queue_idx]
                enemy_queue_idx += 1

                if attacker.hp <= 0:
                    action_timer = current_time
                else:
                    e_idx = enemies.index(attacker)
                    e_status = enemy_statuses[e_idx]

                    if consume_stun_if_any(attacker, e_status):
                        remaining = e_status.stacks.get("stun", 0) if e_status else 0
                        if remaining > 0:
                            message_text = (f"{attacker.name} is stunned and cannot move! "
                                            f"({remaining} turn left)")
                        else:
                            message_text = f"{attacker.name} is stunned and cannot move!"
                        message_color = (200, 230, 255)
                        splash_text = "STUNNED"
                        splash_is_burst = False
                        splash_color = (200, 230, 255)
                        splash_timer = SPLASH_DURATION
                        action_timer = current_time + ACTION_DELAY
                        continue

                    weak_reduction = 0
                    if e_status is not None and hasattr(e_status, "get_damage_reduction"):
                        weak_reduction = e_status.get_damage_reduction()

                    enemy_move = None
                    if hasattr(attacker, "pick_enemy_move"):
                        try:
                            enemy_move = attacker.pick_enemy_move()
                        except Exception:
                            enemy_move = None

                    attacker_element = getattr(attacker, "element", None)
                    message_color = ENEMY_ACTION_COLOR

                    _sfx = _enemy_move_sfx(enemy_move, attacker)
                    play_skill_sfx(_sfx, volume=SKILL_SFX_ENEMY_VOL)

                    if enemy_move:
                        move_name = enemy_move.get("name", "Attack")
                        anim_key  = enemy_move.get("animation", "attack1")
                        self_buff = enemy_move.get("self_buff")

                        if self_buff:
                            stat_name, amount = self_buff
                            set_entity_animation(attacker, anim_key, "block", "idle")
                            current_value = getattr(attacker, stat_name, 0)
                            setattr(attacker, stat_name, current_value + amount)
                            message_text = (f"{move_name}: {stat_name.upper()} +{amount}")
                            message_color = ENEMY_ACTION_COLOR
                            splash_text = move_name
                            splash_is_burst = False
                            splash_color = None
                            splash_timer = SPLASH_DURATION
                        else:
                            min_dmg = enemy_move.get("min_dmg", 2)
                            max_dmg = enemy_move.get("max_dmg", 5)
                            status_effect = enemy_move.get("status")
                            hits = enemy_move.get("hits", 1)

                            set_entity_animation(attacker, anim_key, "attack1", "attack")

                            raw_dmg = 0
                            for _ in range(hits):
                                raw_dmg += random.randint(min_dmg, max_dmg)

                            enemy_element = getattr(attacker, "element", None)
                            player_element = getattr(player, "element", "Neutral")

                            p_def = _effective_player_def(player)
                            def_mult = _defense_multiplier(p_def)
                            raw_dmg = max(1, int(raw_dmg * def_mult))

                            multiplier = element_multiplier(enemy_element, player_element)

                            enemy_dmg = max(1, int(raw_dmg * multiplier + 0.5) - weak_reduction)
                            enemy_dmg = max(1, enemy_dmg)
                            player.hp = max(0, player.hp - enemy_dmg)

                            if enemy_dmg > 0:
                                _apply_hit_juice(player, shake=0.30)
                                _queue_float(
                                    pending_float_texts, player, enemy_dmg,
                                    get_element_float_color(enemy_element),
                                    current_time + ENEMY_ATTACK_LEAD_MS,
                                    size=_size_from_damage(enemy_dmg),
                                )

                            if not hurt_played_this_turn:
                                hurt_played_this_turn = True
                                if player.hp > 0:
                                    pending_player_hurt_at = current_time + ENEMY_ATTACK_LEAD_MS
                                    pending_player_hurt_active = True

                            status_list = []
                            if status_effect and player_status is not None:
                                kind, stacks = status_effect
                                if random.random() < ENEMY_STATUS_CHANCE:
                                    player_status.add_status(kind, stacks)
                                    status_list.append((kind.capitalize(), stacks))
                                    play_status_sfx(volume=STATUS_SFX_VOL)

                            cond_statuses = enemy_move.get("status_if_absent")
                            if cond_statuses and player_status is not None:
                                for c_kind, c_stacks in cond_statuses:
                                    if player_status.stacks.get(c_kind, 0) <= 0:
                                        if random.random() < ENEMY_STATUS_CHANCE:
                                            player_status.add_status(c_kind, c_stacks)
                                            status_list.append((c_kind.capitalize(), c_stacks))
                                            play_status_sfx(volume=STATUS_SFX_VOL)

                            if (enemy_move.get("convert_burn_to_blue", False)
                                    and player_status is not None):
                                burn_before = player_status.stacks.get("burn", 0)
                                if burn_before > 0:
                                    player_status.convert_burn_to_blue_flame()
                                    status_list.append(("Blue Flame", burn_before))

                            _spawn_status_pops(juice, status_list, player,
                                               enemies, player)

                            message_text = _format_action_line(
                                move_name, enemy_dmg, status_list)

                            splash_text = move_name
                            splash_is_burst = False
                            splash_color = get_element_text_color(enemy_element)
                            splash_timer = SPLASH_DURATION
                    else:
                        set_entity_animation(attacker, "attack1", "attack01", "attack")
                        e_atk = getattr(attacker, "atk", 8)

                        enemy_element = getattr(attacker, "element", None)
                        player_element = getattr(player, "element", "Neutral")

                        p_def = _effective_player_def(player)
                        def_mult = _defense_multiplier(p_def)
                        raw_dmg = max(2, e_atk) + random.randint(0, 2)
                        base_dmg = max(1, int(raw_dmg * def_mult))

                        multiplier = element_multiplier(enemy_element, player_element)

                        enemy_dmg = max(1, int(base_dmg * multiplier + 0.5) - weak_reduction)
                        enemy_dmg = max(1, enemy_dmg)
                        player.hp = max(0, player.hp - enemy_dmg)

                        if enemy_dmg > 0:
                            _apply_hit_juice(player, shake=0.30)
                            _queue_float(
                                pending_float_texts, player, enemy_dmg,
                                get_element_float_color(enemy_element),
                                current_time + ENEMY_ATTACK_LEAD_MS,
                                size=_size_from_damage(enemy_dmg),
                            )

                        if not hurt_played_this_turn:
                            hurt_played_this_turn = True
                            if player.hp > 0:
                                pending_player_hurt_at = current_time + ENEMY_ATTACK_LEAD_MS
                                pending_player_hurt_active = True

                        message_text = _format_action_line("STRIKE", enemy_dmg)
                        splash_color = get_element_text_color(enemy_element)

                    action_timer = current_time + ACTION_DELAY

            else:
                pending_player_hurt_active = False

                for e in enemies:
                    if e.hp > 0:
                        set_entity_animation(e, "idle")

                if hasattr(player, "set_animation") and player.hp > 0:
                    player.set_animation("idle")

                tick_msgs = []

                status_bonuses = {
                    "bleed":      _status_dmg_bonus(player, "bleed"),
                    "burn":       _status_dmg_bonus(player, "burn"),
                    "poison":     _status_dmg_bonus(player, "poison"),
                    "blue_flame": _status_dmg_bonus(player, "blue_flame"),
                }

                for i, enemy in enumerate(enemies):
                    if enemy.hp <= 0:
                        continue
                    st = enemy_statuses[i]
                    if st is None:
                        continue

                    status_breakdown = {}
                    heal_breakdown = {}
                    e_tick = st.process_turn_damage(
                        enemy, bonuses=status_bonuses,
                        breakdown=status_breakdown,
                        heal_breakdown=heal_breakdown)

                    if e_tick > 0:
                        tick_msgs.append(f"{enemy.name} takes {e_tick} status dmg")
                        for status_key, amount in status_breakdown.items():
                            if amount > 0:
                                _queue_float(
                                    pending_float_texts, enemy, amount,
                                    get_status_float_color(status_key),
                                    current_time + 80,
                                    size=_size_from_damage(
                                        amount, base_min=18,
                                        base_max=26, scale=1.0),
                                )

                    for status_key, amount in heal_breakdown.items():
                        if amount > 0:
                            tick_msgs.append(f"{enemy.name} heals {amount} HP")
                            _queue_float(
                                pending_float_texts, enemy, f"+{amount}",
                                get_status_float_color(status_key),
                                current_time + 80,
                                size=_size_from_damage(
                                    amount, base_min=20,
                                    base_max=30, scale=0.8),
                            )

                    if enemy.hp <= 0:
                        tick_msgs.append(f"{enemy.name} fell")

                if player_status is not None and player.hp > 0:
                    p_breakdown = {}
                    p_heal_breakdown = {}
                    p_tick = player_status.process_turn_damage(
                        player,
                        breakdown=p_breakdown,
                        heal_breakdown=p_heal_breakdown)

                    if p_tick > 0:
                        tick_msgs.append(f"{player.name} takes {p_tick} status dmg")
                        for status_key, amount in p_breakdown.items():
                            if amount > 0:
                                _queue_float(
                                    pending_float_texts, player, amount,
                                    get_status_float_color(status_key),
                                    current_time + 80,
                                    size=_size_from_damage(
                                        amount, base_min=18,
                                        base_max=26, scale=1.0),
                                )
                        player_hurt_flash_timer = HURT_FLASH_DURATION
                        if player.hp > 0:
                            play_hurt_animation(player)
                            player_hurt_revert_at = current_time + PLAYER_HURT_REVERT_MS

                    for status_key, amount in p_heal_breakdown.items():
                        if amount > 0:
                            tick_msgs.append(f"{player.name} heals {amount} HP")
                            _queue_float(
                                pending_float_texts, player, f"+{amount}",
                                get_status_float_color(status_key),
                                current_time + 80,
                                size=_size_from_damage(
                                    amount, base_min=20,
                                    base_max=30, scale=0.8),
                            )
                            juice.spawn_heal_sparkles(count=6,
                                                      base_x=300, base_y=420)

                    if player.hp <= 0:
                        battle_state = "BATTLE_OVER"
                        battle_result = "DEFEAT"
                        message_text = f"{player.name} succumbed to status damage..."
                        message_color = COLOR_WHITE
                        action_timer = current_time + DEFEAT_END_DELAY
                        set_entity_animation(player, "death", "dead", "die", "defeat")
                        continue

                alive_after = [e for e in enemies if e.hp > 0]
                if not alive_after:
                    battle_state = "BATTLE_OVER"
                    battle_result = "VICTORY"
                    message_text = "All enemies fell!"
                    message_color = COLOR_WHITE
                    action_timer = current_time + BATTLE_END_DELAY
                    continue

                if tick_msgs:
                    message_text = "   |   ".join(tick_msgs)
                    message_color = COLOR_WHITE

                battle_state = "PLAYER_TURN_WAIT"
                action_timer = current_time + TURN_PAUSE_MS

        elif battle_state == "BATTLE_OVER" and current_time >= action_timer:
            running = False

        if hasattr(player, "update"):
            try:
                player.update(dt)
            except TypeError:
                player.update()
        for enemy in enemies:
            if hasattr(enemy, "update"):
                enemy.update(dt)

        viewport = frame.get_viewport()

        if battle_bg:
            viewport.blit(battle_bg, (0, 0))
        else:
            viewport.fill((25, 30, 35))

        _sync_stun_outlines(enemies, enemy_statuses)

        p_shake_off = (0, 0)
        p_shake_t = getattr(player, "_battle_shake_timer", 0.0)
        if p_shake_t > 0:
            mag = int(4 * (p_shake_t / HIT_SHAKE_DURATION))
            mag = max(1, mag)
            p_shake_off = (random.randint(-mag, mag), random.randint(-mag, mag))

        p_flash = 0.0
        p_flash_t = getattr(player, "_battle_hit_flash_timer", 0.0)
        if p_flash_t > 0:
            p_flash = p_flash_t / HIT_FLASH_DURATION
            p_flash = max(0.0, min(1.0, p_flash))

        player_rect = draw_scaled_combatant(
            viewport, player, target_x=300, target_y=510,
            facing_right=True, shadow_mult=1.4,
            pixel_offset=p_shake_off,
            hit_flash=p_flash)

        layout = get_enemy_layout(len(enemies))
        for i, enemy in enumerate(enemies):
            if i >= len(layout):
                break

            if getattr(enemy, "_battle_fade_active", False) and \
                    getattr(enemy, "_battle_fade_timer", 0) <= 0:
                enemy_rects[i] = None
                continue

            tx, ty, sc_mult = layout[i]
            base_scale = getattr(enemy, "battle_scale", 5.0)
            final_scale = base_scale * sc_mult

            e_shake_off = (0, 0)
            e_shake_t = getattr(enemy, "_battle_shake_timer", 0.0)
            if e_shake_t > 0:
                mag = int(4 * (e_shake_t / HIT_SHAKE_DURATION))
                mag = max(1, mag)
                e_shake_off = (random.randint(-mag, mag),
                               random.randint(-mag, mag))

            e_alpha = 255
            e_extra = 1.0
            if getattr(enemy, "_battle_fade_active", False):
                t = 1.0 - (getattr(enemy, "_battle_fade_timer", 0.0)
                           / KILL_FADE_DURATION)
                t = max(0.0, min(1.0, t))
                e_alpha = int(255 * (1.0 - t))
                e_extra = 1.0 - 0.15 * t

            if getattr(enemy, "_battle_intro_active", False):
                dur = max(1e-6, getattr(enemy, "_battle_intro_duration",
                                        ENEMY_INTRO_DURATION))
                p = min(1.0, getattr(enemy, "_battle_intro_timer", 0.0) / dur)
                if p < 0.5:
                    intro_s = 0.5 + p * 1.3
                else:
                    intro_s = 1.15 - (p - 0.5) * 0.3
                e_extra *= intro_s

            e_flash = 0.0
            e_flash_t = getattr(enemy, "_battle_hit_flash_timer", 0.0)
            if e_flash_t > 0:
                e_flash = e_flash_t / HIT_FLASH_DURATION
                e_flash = max(0.0, min(1.0, e_flash))

            rect = draw_scaled_combatant(
                viewport, enemy,
                target_x=tx, target_y=ty,
                facing_right=False,
                battle_scale=final_scale,
                shadow_mult=sc_mult,
                pixel_offset=e_shake_off,
                alpha=e_alpha,
                extra_scale=e_extra,
                hit_flash=e_flash)
            enemy_rects[i] = rect

        _tint_to_use = viewport_tint
        if _tint_to_use is None:
            vp_w, vp_h = viewport.get_size()
            _tint_to_use = _get_default_battle_tint(vp_w, vp_h)

        if _tint_to_use is not None:
            try:
                viewport.blit(_tint_to_use, (0, 0))
            except Exception:
                pass

        if viewport_particles is not None:
            try:
                viewport_particles.update(dt)
                viewport_particles.draw(viewport)
            except Exception:
                pass

        if player_rect is not None:
            has_atk_buff = getattr(player, "temp_atk_bonus", 0) > 0
            has_def_buff = getattr(player, "temp_def_bonus", 0) > 0
            if has_atk_buff or has_def_buff:
                atk_turns = int(getattr(player, "temp_atk_bonus_turns", 0))
                def_turns = int(getattr(player, "temp_def_bonus_turns", 0))
                draw_potion_buffs_indicator(viewport, player_rect,
                                            elapsed_time,
                                            has_atk_buff, has_def_buff,
                                            atk_turns=atk_turns,
                                            def_turns=def_turns)

        if (battle_state == "PLAYER_TURN"
                and 0 <= target_index < len(enemies)
                and enemies[target_index].hp > 0):
            bob = int(3 * pygame.math.Vector2(1, 0).rotate(
                (current_time // 8) % 360).y)
            draw_target_marker(viewport, enemy_rects[target_index], bob=bob)

        for i, enemy in enumerate(enemies):
            if getattr(enemy, "hp", 0) <= 0:
                continue
            st = enemy_statuses[i]
            if st is None:
                continue
            if st.stacks.get("stun", 0) > 0:
                draw_stun_indicator(viewport, enemy_rects[i], elapsed_time)

        draw_huds(viewport, player, enemies, font_large, font_main,
                  player_status=player_status,
                  enemy_statuses=enemy_statuses,
                  target_index=target_index,
                  mouse_pos=viewport_mouse)

        if splash_timer > 0:
            progress = 1.0 - (splash_timer / SPLASH_DURATION)
            rise = int(-SPLASH_RISE_PIXELS * progress)
            elapsed = SPLASH_DURATION - splash_timer
            if elapsed < SPLASH_FADE_IN:
                alpha = int(255 * (elapsed / SPLASH_FADE_IN))
            elif splash_timer < SPLASH_FADE_OUT:
                alpha = int(255 * (splash_timer / SPLASH_FADE_OUT))
            else:
                alpha = 255
            active_font = font_burst if splash_is_burst else font_big
            draw_splash_text(viewport, splash_text, active_font, alpha,
                             rise_offset=rise, color=splash_color)

        log_rect = pygame.Rect(60, 580, 1160, 110)
        log_bg = pygame.Surface((log_rect.width, log_rect.height), pygame.SRCALPHA)
        log_bg.fill((15, 20, 25, 220))
        viewport.blit(log_bg, log_rect.topleft)
        pygame.draw.rect(viewport, (212, 175, 55), log_rect, 3)

        msg_surf = font_main.render(message_text, True, message_color)
        viewport.blit(msg_surf, (log_rect.x + 20, log_rect.y + 40))

        _draw_hurt_flash(viewport, player_hurt_flash_timer)
        _draw_low_hp_border(viewport, player, elapsed_time)

        juice.draw(viewport)

        if burst_flash_timer > 0:
            a = burst_flash_timer / BURST_FLASH_DURATION
            _flash_surface(viewport, burst_flash_color, a * 0.7)

        current_quests = _compute_quests(player)
        frame.quests = current_quests

        frame.shake_offset = shake.offset
        frame_action = frame.draw(screen)

        if frame_action == "STATS" and run_stats_menu:
            run_stats_menu(screen, frame, player)

        if draw_inventory_and_equipment:
            draw_inventory_and_equipment(screen, player, frame)

        if battle_state in ("PLAYER_TURN", "PLAYER_TURN_WAIT"):
            btn_attack.update(mouse_pos); btn_attack.draw(screen)
            if show_elem:
                btn_elem_attack.update(mouse_pos); btn_elem_attack.draw(screen)
            if show_burst:
                btn_burst.update(mouse_pos); btn_burst.draw(screen)
            if allow_flee:
                btn_run.update(mouse_pos); btn_run.draw(screen)

        pygame.display.flip()

    try:
        if hasattr(player, "_battle_apply_self_status"):
            delattr(player, "_battle_apply_self_status")
    except Exception:
        pass

    if show_end_banner:
        if battle_result == "VICTORY":
            play_battle_end_banner(screen, True)
        elif battle_result == "DEFEAT":
            play_battle_end_banner(screen, False)

    if battle_result == "DEFEAT" and hasattr(player, "respawn"):
        player.respawn()

    if hasattr(player, "can_move"):
        player.can_move = True
    if hasattr(player, "set_animation"):
        player.set_animation("idle")
    for enemy in enemies:
        if hasattr(enemy, "set_animation"):
            enemy.set_animation("idle")
        if hasattr(enemy, "reset_battle_trigger"):
            enemy.reset_battle_trigger()

    if battle_result == "FLED":
        for enemy in enemies:
            if hasattr(enemy, "start_flee_cooldown"):
                enemy.start_flee_cooldown()

    if battle_result == "VICTORY":
        try:
            _handle_victory_drops(screen, player, enemies, font_large, font_main)
        except Exception as e:
            print(f"[Battle] Victory drops failed: {e}")

    if strip_temp_buffs:
        try:
            _strip_temp_potion_buffs(player)
        except Exception as e:
            print(f"[Battle] strip_temp_potion_buffs failed: {e}")

    if _saved_zoom is not None and game_manager is not None:
        try:
            game_manager.zoom_level = _saved_zoom
        except Exception:
            pass

    if game_manager is not None:
        try:
            game_manager.resume_ambient(fade_ms=600)
        except Exception as e:
            print(f"[Battle] resume_ambient failed: {e}")

    return battle_result