
import os
import sys
import math
import random
import pygame

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from battle.battle import (
    run_battle, ELEM_CHARGES_MAX, BURST_CHARGES_MAX,
)
from battle.multi_battle import show_wave_banner
from battle_func import (
    _strip_temp_potion_buffs,
    fade_to_black,
    play_battle_end_banner,
    play_roar_sfx,
)
from enemies.kitsune import Kitsune
from enemies.tiny_orc import TinyOrc
from enemies.slime import Slime
from enemies.tiny_devil import TinyDevil

from Modules.particles import (
    ParticleBundle, FireflySystem, BlueFallSystem, make_midnight_overlay,
)

try:
    from Modules.sound_manager import game_manager
except ImportError:
    game_manager = None


VIEWPORT_W = 1280
VIEWPORT_H = 720


class KitsuneBoss(Kitsune):
    BOSS_HP    = 300
    BOSS_ATK   = 11
    BOSS_DEF   = 8
    BOSS_EVADE = 0.12

    MOVE_TABLE = [
        (Kitsune.AZURE_SPLASH, 0.80),
        (Kitsune.AZURE_FREEZE, 0.20),
    ]

    def __init__(self, x=100, y=100, scale=1.0):
        super().__init__(x=x, y=y, scale=scale)

        self.max_hp = self.BOSS_HP
        self.hp = self.BOSS_HP
        self.atk = self.BOSS_ATK
        self.defense = self.BOSS_DEF
        self.evade = self.BOSS_EVADE

        self.name = "Kitsune"
        self.is_boss = True
        self.battle_scale = 1.7

    def pick_enemy_move(self):
        roll = random.random()
        cumulative = 0.0
        for move, weight in self.MOVE_TABLE:
            cumulative += weight
            if roll <= cumulative:
                return dict(move)
        return dict(self.AZURE_SPLASH)


BOSS_DROPS = ["blueflame_katana", "the_suns_ray"]


def _font(size, bold=False):
    font_path = os.path.join(PROJECT_ROOT, "asset", "font", "TheGothicRite.otf")
    if os.path.exists(font_path):
        return pygame.font.Font(font_path, size)
    return pygame.font.SysFont("Georgia", size, bold=bold)


def _build_kitsune_mood():

    intensity = "medium"
    if game_manager is not None:
        try:
            intensity = getattr(game_manager, "particle_intensity", "medium")
        except Exception:
            intensity = "medium"

    bundle = ParticleBundle(
        FireflySystem(world_w=VIEWPORT_W, world_h=VIEWPORT_H,
                      intensity=intensity),
        BlueFallSystem(world_w=VIEWPORT_W, world_h=VIEWPORT_H,
                       intensity=intensity),
    )
    tint = make_midnight_overlay(VIEWPORT_W, VIEWPORT_H)
    return bundle, tint


def _wrap_text(text, font, max_width):
    words = text.split(' ')
    lines_out = []
    cur = ""
    for word in words:
        if "\n" in word:
            parts = word.split("\n")
            for j, part in enumerate(parts):
                if j > 0:
                    lines_out.append(cur)
                    cur = ""
                if part:
                    cur += part + " "
        else:
            test = cur + word + " "
            if font.size(test)[0] < max_width:
                cur = test
            else:
                lines_out.append(cur)
                cur = word + " "
    lines_out.append(cur)
    return lines_out


def _render_wrapped(surface, text, font, color, x, y, max_w, line_gap=8):
    for line in _wrap_text(text, font, max_w):
        stripped = line.strip()
        if stripped:
            s = font.render(stripped, True, color)
            surface.blit(s, (x, y))
        y += font.get_linesize() + line_gap


def _play_letterbox_dialogue(screen, dialogue_list):
    fade_to_black(screen, duration_ms=400)

    clock = pygame.time.Clock()
    screen_w, screen_h = screen.get_size()

    font_header = _font(46)
    font_body   = _font(32)
    font_hint   = _font(20)

    COLOR_BLACK = (10, 10, 15)
    COLOR_VOID  = (0, 0, 0)
    COLOR_GOLD  = (212, 175, 55)
    COLOR_WHITE = (240, 235, 210)
    COLOR_GRAY  = (150, 150, 170)
    COLOR_AQUA  = (140, 220, 255)
    COLOR_FOX   = (255, 170, 90)
    COLOR_OZ    = (200, 180, 255)

    CHAR_DELAY  = 0.045
    LETTERBOX_H = 90

    for speaker, text in dialogue_list:
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

            upper = speaker.upper()
            if upper in ("NARRATOR", "SYSTEM", "LUNAIRE"):
                hcolor = COLOR_AQUA
            elif "kitsune" in speaker.lower() or "fox" in speaker.lower():
                hcolor = COLOR_FOX
            elif "oz" in speaker.lower() or "wizard" in speaker.lower():
                hcolor = COLOR_OZ
            else:
                hcolor = COLOR_GOLD

            hsurf = font_header.render(speaker, True, hcolor)
            screen.blit(hsurf, (340, 260))
            pygame.draw.line(screen, COLOR_GOLD,
                             (340, 260 + hsurf.get_height() + 8),
                             (340 + 640, 260 + hsurf.get_height() + 8), 2)
            _render_wrapped(screen, shown, font_body, COLOR_WHITE,
                            340, 340, 1240)

            if revealed:
                hint = font_hint.render("[ SPACE / ENTER to continue ]",
                                        True, COLOR_GRAY)
                screen.blit(hint, hint.get_rect(
                    center=(screen_w // 2, screen_h - 130)))

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


def _play_kitsune_defeat_dialogue(screen, player_name):
    lines = [
        ("Kitsune", "...ha... hahaha..."),
        ("Kitsune", "How... how did you defeat a god like me?"),
        ("Kitsune",
         "I have burned through ages. Through empires. "
         "Through every knight who ever dared the woods."),
        ("Kitsune",
         "And yet... a boy with a crescent in his hand."),
        ("NARRATOR",
         "The fox spirit's flames gutter low. Her tails "
         "dim one by one."),
        (player_name,
         "You weren't a god. You were a gatekeeper."),
        (player_name, "And the gate is open now."),
        ("Kitsune", "...nn... you... *you really believe that*..."),
        ("Kitsune", "Then take them. The blue flame and the sun."),
        ("Kitsune",
         "They will not save her. But they will keep you walking."),
        ("NARRATOR",
         "Her body dissolves into embers. The shrine goes quiet."),
    ]
    _play_letterbox_dialogue(screen, lines)


def _play_kitsune_defeat_cutscene(screen, player_name):
    lines = [
        (player_name, "Lulu... Lunaire..."),
        ("Kitsune",   "HAHAHAHAHAH! Brave knight."),
    ]
    _play_letterbox_dialogue(screen, lines)


def _play_oz_wake_cutscene(screen, player_name):
    lines = [
        ("Wizard Oz", f"{player_name}. {player_name}. Wake up."),
        ("SYSTEM",    "You revive at the last save."),
    ]
    _play_letterbox_dialogue(screen, lines)


def _play_kitsune_showcase(screen, boss, duration_sec=3.0):
    clock = pygame.time.Clock()
    sw, sh = screen.get_size()

    play_roar_sfx(volume=0.65)

    frames = getattr(boss, "animations", {}).get("idle", [])
    base = frames[0] if frames else getattr(boss, "image", None)
    if base is None:
        return

    font_name = _font(96)
    name_gold = font_name.render("KITSUNE", True, (255, 180, 60))
    name_out  = font_name.render("KITSUNE", True, (0, 0, 0))

    start = pygame.time.get_ticks()
    running = True
    skipped = False

    while running:
        clock.tick(60)
        elapsed = (pygame.time.get_ticks() - start) / 1000.0
        if elapsed >= duration_sec:
            break

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            if ((event.type == pygame.KEYDOWN
                 or event.type == pygame.MOUSEBUTTONDOWN)
                    and elapsed > 0.6):
                skipped = True
                running = False
                break

        if skipped:
            break

        t = elapsed / duration_sec

        if t < 0.14:
            alpha = int(255 * (t / 0.14))
        elif t < 0.86:
            alpha = 255
        else:
            alpha = int(255 * max(0.0, 1.0 - (t - 0.86) / 0.14))

        if t < 0.20:
            local = t / 0.20
            scale = 0.55 + 0.55 * local
        elif t < 0.32:
            local = (t - 0.20) / 0.12
            scale = 1.10 - 0.10 * local
        else:
            scale = 1.0 + 0.015 * math.sin(elapsed * 2.6)

        screen.fill((4, 4, 10))

        if alpha > 5:
            glow_w = int(700 * scale)
            glow_h = int(600 * scale)
            glow = pygame.Surface((glow_w, glow_h), pygame.SRCALPHA)
            for i in range(10):
                a = int((40 - i * 3) * (alpha / 255))
                if a <= 0:
                    continue
                inset = i * 18
                pygame.draw.ellipse(
                    glow, (255, 110, 40, a),
                    (inset, inset, glow_w - inset * 2, glow_h - inset * 2),
                )
            screen.blit(glow,
                        glow.get_rect(center=(sw // 2, sh // 2 - 40)))

        base_w, base_h = base.get_size()
        aspect = base_w / float(base_h) if base_h else 1.0
        target_h = int(560 * scale)
        target_w = max(1, int(target_h * aspect))
        big = pygame.transform.smoothscale(base, (target_w, target_h))
        big.set_alpha(alpha)
        rect = big.get_rect(center=(sw // 2, sh // 2 - 40))
        screen.blit(big, rect)

        if t > 0.25 and alpha > 5:
            name_alpha = int(255 * min(1.0, (t - 0.25) / 0.20))
            if t > 0.86:
                name_alpha = int(name_alpha *
                                 max(0.0, 1.0 - (t - 0.86) / 0.14))
            name_alpha = max(0, min(255, name_alpha))

            ng = name_gold.copy(); ng.set_alpha(name_alpha)
            no = name_out.copy();  no.set_alpha(name_alpha)

            ny = sh // 2 + int(360 * scale) + 30
            nr = ng.get_rect(center=(sw // 2, ny))
            for dx, dy in ((-3, 0), (3, 0), (0, -3), (0, 3)):
                screen.blit(no, (nr.x + dx, nr.y + dy))
            screen.blit(ng, nr)

        pygame.display.flip()


def _give_boss_rewards(screen, player):
    try:
        from Modules.inv import give_item_by_id
        from battle.battle_func import _play_drop_animations
    except ImportError as e:
        print(f"[BossBattle] reward import failed: {e}")
        return

    for item_id in BOSS_DROPS:
        try:
            give_item_by_id(player, item_id)
        except Exception as e:
            print(f"[BossBattle] give_item_by_id({item_id}) failed: {e}")

    font_large = _font(32)
    font_body  = _font(22)

    try:
        _play_drop_animations(screen, BOSS_DROPS, font_large, font_body)
    except Exception as e:
        print(f"[BossBattle] drop animation failed: {e}")


def _play_lunaire_whisper(screen, player_name):
    lines = [
        ("NARRATOR",
         "And then - a voice. Not from the shrine. Not from "
         "the forest. From somewhere much, much further away."),
        ("LUNAIRE", f"{player_name}..."),
        ("LUNAIRE", "I'm... I'm here..."),
        ("LUNAIRE", "e...  e..."),
        ("NARRATOR",
         "The whisper fades. The forest holds its breath."),
    ]
    _play_letterbox_dialogue(screen, lines)


def run_boss_battle(screen, player, slot_id=1):
    player_name = getattr(player, "name", "Solaris")

    charges = {"elem": ELEM_CHARGES_MAX, "burst": BURST_CHARGES_MAX}

    kitsune_particles, kitsune_tint = _build_kitsune_mood()

    wave1_enemies = [
        TinyOrc(x=0, y=0),
        Slime(x=0, y=0),
        TinyDevil(x=0, y=0),
    ]

    result = run_battle(
        screen, player, wave1_enemies,
        slot_id=slot_id,
        attackers_override=2,
        charges=charges,
        skip_intro=False,
        show_end_banner=False,
    )

    if result != "VICTORY":
        if result == "DEFEAT":
            play_battle_end_banner(screen, False)
        _strip_temp_potion_buffs(player)
        return result

    show_wave_banner(screen, 2, 2, duration_sec=1.8)

    boss = KitsuneBoss(x=0, y=0)
    _play_kitsune_showcase(screen, boss, duration_sec=3.0)

    result = run_battle(
        screen, player, [boss],
        slot_id=slot_id,
        attackers_override=1,
        charges=charges,
        skip_intro=True,
        show_end_banner=False,
        viewport_particles=kitsune_particles,
        viewport_tint=kitsune_tint,
    )

    if result == "VICTORY":
        play_battle_end_banner(screen, True)
        _play_kitsune_defeat_dialogue(screen, player_name)
        _give_boss_rewards(screen, player)
        _play_lunaire_whisper(screen, player_name)

    elif result == "DEFEAT":
        play_battle_end_banner(screen, False)
        _play_kitsune_defeat_cutscene(screen, player_name)
        _play_oz_wake_cutscene(screen, player_name)

    _strip_temp_potion_buffs(player)
    return result