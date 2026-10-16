
import os
import sys
import math
import pygame

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from battle.battle import run_battle, ELEM_CHARGES_MAX, BURST_CHARGES_MAX
from battle_func import (
    _strip_temp_potion_buffs,
    fade_to_black,
    play_battle_end_banner,
    play_roar_sfx,
    play_transition_sfx,
)
from enemies.gorgona import Gorgona

from Modules.particles import (
    ParticleBundle, FireflySystem, RedFallSystem, make_midnight_overlay,
)

try:
    from Modules.sound_manager import game_manager
except ImportError:
    game_manager = None


THUNDER_SFX_PATH = os.path.join(PROJECT_ROOT, "asset", "sfx", "thunder.mp3")

ENDING_VICTORY_MUSIC = "ending_fanfare.mp3"
ENDING_DEFEAT_MUSIC  = "ending_lose.mp3"
END_SCREEN_MUSIC     = "end.mp3"

ENDING_MUSIC_VOLUME    = 0.70
END_SCREEN_MUSIC_VOL   = 0.75

VIEWPORT_W = 1280
VIEWPORT_H = 720


def _play_ending_music(name, volume=ENDING_MUSIC_VOLUME):
    if game_manager is None:
        return
    if not getattr(game_manager, "bgm_enabled", True):
        return
    try:
        game_manager.play_music(name, fade_ms=1200, volume=volume)
    except Exception as e:
        print(f"[FinalBattle] ending music failed ({name}): {e}")


def _build_fight_mood():

    intensity = "medium"
    if game_manager is not None:
        try:
            intensity = getattr(game_manager, "particle_intensity", "medium")
        except Exception:
            intensity = "medium"

    bundle = ParticleBundle(
        FireflySystem(world_w=VIEWPORT_W, world_h=VIEWPORT_H,
                      intensity=intensity),
        RedFallSystem(world_w=VIEWPORT_W, world_h=VIEWPORT_H,
                      intensity=intensity),
    )
    tint = make_midnight_overlay(VIEWPORT_W, VIEWPORT_H)
    return bundle, tint


def _font(size, bold=False):
    font_path = os.path.join(PROJECT_ROOT, "asset", "font", "TheGothicRite.otf")
    if os.path.exists(font_path):
        return pygame.font.Font(font_path, size)
    return pygame.font.SysFont("Georgia", size, bold=bold)


def _play_thunder_sfx():
    try:
        from Modules.sound_manager import game_manager as gm
    except ImportError:
        return
    if not getattr(gm, "sfx_enabled", True):
        return
    if not os.path.exists(THUNDER_SFX_PATH):
        print(f"[FinalBattle] thunder SFX not found: {THUNDER_SFX_PATH}")
        return
    try:
        snd = pygame.mixer.Sound(THUNDER_SFX_PATH)
        snd.set_volume(getattr(gm, "sfx_volume", 0.5))
        snd.play()
    except Exception as e:
        print(f"[FinalBattle] thunder SFX failed: {e}")


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
    COLOR_GORG  = (200, 100, 220)

    CHAR_DELAY  = 0.040
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
            elif "gorgona" in speaker.lower():
                hcolor = COLOR_GORG
            elif "oz" in speaker.lower() or "wizard" in speaker.lower():
                hcolor = COLOR_OZ
            elif "kitsune" in speaker.lower() or "fox" in speaker.lower():
                hcolor = COLOR_FOX
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


def _show_gorgona_tutorial(screen):
    clock = pygame.time.Clock()
    screen_w, screen_h = screen.get_size()

    font_title = _font(52)
    font_big   = _font(30)
    font_body  = _font(22)
    font_btn   = _font(26)

    COLOR_BLACK = (10, 10, 15)
    COLOR_VOID  = (0, 0, 0)
    COLOR_GOLD  = (212, 175, 55)
    COLOR_WHITE = (240, 235, 210)
    COLOR_GRAY  = (150, 150, 170)
    COLOR_PANEL = (35, 30, 60)
    COLOR_HOVER = (60, 50, 95)

    yes_btn = pygame.Rect(screen_w // 2 - 220, screen_h // 2 + 160, 200, 60)
    no_btn  = pygame.Rect(screen_w // 2 + 20,  screen_h // 2 + 160, 200, 60)

    state = "ASK"
    start_ms = pygame.time.get_ticks()

    while True:
        clock.tick(60)
        mouse_pos = pygame.mouse.get_pos()
        now = pygame.time.get_ticks()

        screen.fill(COLOR_BLACK)
        bar = pygame.Surface((screen_w, 90)); bar.fill(COLOR_VOID)
        screen.blit(bar, (0, 0)); screen.blit(bar, (0, screen_h - 90))

        if state == "ASK":
            t = font_title.render("THE FINAL BATTLE", True, COLOR_GOLD)
            screen.blit(t, t.get_rect(center=(screen_w // 2, 220)))

            q = font_big.render("Do you wish to hear of Gorgona's nature?",
                                True, COLOR_WHITE)
            screen.blit(q, q.get_rect(center=(screen_w // 2, 340)))

            sub = font_body.render("(Choosing NO proceeds straight to the fight)",
                                   True, COLOR_GRAY)
            screen.blit(sub, sub.get_rect(center=(screen_w // 2, 400)))

            for rect, label in ((yes_btn, "YES"), (no_btn, "NO")):
                hovered = rect.collidepoint(mouse_pos)
                fill = COLOR_HOVER if hovered else COLOR_PANEL
                pygame.draw.rect(screen, fill, rect, border_radius=8)
                pygame.draw.rect(screen, COLOR_GOLD, rect, width=3,
                                 border_radius=8)
                col = COLOR_GOLD if hovered else COLOR_WHITE
                lbl = font_btn.render(label, True, col)
                screen.blit(lbl, lbl.get_rect(center=rect.center))

        elif state == "INFO":
            t = font_title.render("GORGONA, THE VAIN EMPRESS", True, COLOR_GOLD)
            screen.blit(t, t.get_rect(center=(screen_w // 2, 200)))

            lines = [
                "She bends the four elements. She does not tire.",
                "",
                "Only FOUR blades can wound her:",
                "   - The Sun's Ray",
                "   - Eclipsis Dagger   (true damage)",
                "   - Crimson Petal Katana",
                "   - Demon Blade",
                "",
                "Every other weapon deals ZERO direct damage.",
                "BUT status effects (Burn / Bleed / Poison / Blue Flame)",
                "still hurt her each turn.",
                "",
                "She has THREE faces. Each one must fall.",
                "ELEMENTAL SLASH and BURST charges refill each phase.",
            ]
            y = 290
            for ln in lines:
                s = font_body.render(ln, True, COLOR_WHITE)
                screen.blit(s, s.get_rect(midtop=(screen_w // 2, y)))
                y += 32

            if now - start_ms > 400:
                hint = font_body.render("[ SPACE / ENTER / CLICK to fight ]",
                                        True, COLOR_GRAY)
                screen.blit(hint, hint.get_rect(
                    center=(screen_w // 2, screen_h - 130)))

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if state == "ASK":
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if yes_btn.collidepoint(event.pos):
                        state = "INFO"; start_ms = now
                    elif no_btn.collidepoint(event.pos):
                        return "NO"
                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_y,):
                        state = "INFO"; start_ms = now
                    elif event.key in (pygame.K_n, pygame.K_ESCAPE):
                        return "NO"
            else:
                if now - start_ms > 400:
                    if ((event.type == pygame.KEYDOWN and
                         event.key in (pygame.K_SPACE, pygame.K_RETURN,
                                       pygame.K_e, pygame.K_ESCAPE))
                        or (event.type == pygame.MOUSEBUTTONDOWN
                            and event.button == 1)):
                        return "YES"


def _play_final_banner(screen, duration_sec=2.4):
    try:
        play_transition_sfx()
    except Exception:
        pass

    clock = pygame.time.Clock()
    screen_w, screen_h = screen.get_size()

    font_path = os.path.join(PROJECT_ROOT, "asset", "font", "TheGothicRite.otf")
    if os.path.exists(font_path):
        font_big   = pygame.font.Font(font_path, 100)
        font_small = pygame.font.Font(font_path, 34)
    else:
        font_big   = pygame.font.SysFont("Georgia", 100, bold=True)
        font_small = pygame.font.SysFont("Georgia", 34, bold=True)

    big_text = "THE FINAL BATTLE BEGINS!"
    sub_text = "Gorgona, the Vain Empress"

    big_base = font_big.render(big_text, True, (255, 215, 0))
    big_out  = font_big.render(big_text, True, (0, 0, 0))
    sub_surf = font_small.render(sub_text, True, (240, 235, 210))

    start = pygame.time.get_ticks()
    running = True
    while running:
        clock.tick(60)
        elapsed = (pygame.time.get_ticks() - start) / 1000.0
        if elapsed >= duration_sec:
            break

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_ESCAPE):
                    return

        t = elapsed / duration_sec
        if t < 0.10:    overlay_a = t / 0.10
        elif t < 0.80:  overlay_a = 1.0
        else:           overlay_a = max(0.0, 1.0 - (t - 0.80) / 0.20)

        scale = 0.55 + 0.45 * min(1.0, t / 0.35) if t < 0.35 else 1.0
        if t > 0.80:
            scale = 1.0 - 0.15 * ((t - 0.80) / 0.20)

        overlay = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, int(220 * overlay_a)))
        screen.blit(overlay, (0, 0))

        alpha = int(255 * overlay_a)

        bw = max(1, int(big_base.get_width() * scale))
        bh = max(1, int(big_base.get_height() * scale))
        big_scaled = pygame.transform.scale(big_base, (bw, bh))
        out_scaled = pygame.transform.scale(big_out, (bw, bh))
        big_scaled.set_alpha(alpha); out_scaled.set_alpha(alpha)

        cx = screen_w // 2
        cy = screen_h // 2 - 20

        for dx, dy in ((-3, 0), (3, 0), (0, -3), (0, 3)):
            r = out_scaled.get_rect(center=(cx + dx, cy + dy))
            screen.blit(out_scaled, r)
        r = big_scaled.get_rect(center=(cx, cy))
        screen.blit(big_scaled, r)

        sub_surf.set_alpha(alpha)
        screen.blit(sub_surf, sub_surf.get_rect(center=(cx, cy + 100)))

        pygame.display.flip()


def _play_phase_transition(screen, from_phase, to_phase):
    play_roar_sfx(volume=0.65)

    if from_phase == 0:
        lines = [
            ("NARRATOR",
             "Gorgona's green scales crack. Something gold pushes through."),
            ("Gorgona", "You... broke my skin. How... DARE you!"),
            ("Gorgona", "Then let the Empress show you her true face!"),
            ("NARRATOR",
             "Gilded armor splits the mist. A second form rises."),
        ]
    else:
        lines = [
            ("NARRATOR",
             "The gilded plate shatters. Embers bleed through."),
            ("Gorgona", "ENOUGH!"),
            ("Gorgona", "If you want your moon, take her from THIS!"),
            ("NARRATOR",
             "Black scales. Burning eyes. The ECLIPSE awakens."),
        ]
    _play_letterbox_dialogue(screen, lines)


def _play_death_cutscene(screen, player_name, attempt):
    lines = [
        (player_name, "Lulu... Lunaire..."),
        ("Gorgona",
         "HAHAHAHA! Pitiful. Stay down, little knight."),
        ("NARRATOR",
         "The world dims. But somewhere far away - a light."),
        ("Wizard Oz",
         f"{player_name}. {player_name}. Wake up."),
        ("Wizard Oz",
         "It is not your time. Not yet. Rise again."),
        ("SYSTEM",
         f"You revive at the last save. (Death {attempt})"),
    ]
    _play_letterbox_dialogue(screen, lines)


def _show_death_screen(screen, attempts, player_name):
    clock = pygame.time.Clock()
    screen_w, screen_h = screen.get_size()
    font_title = _font(72)
    font_body  = _font(28)

    COLOR_BLACK = (10, 10, 15)
    COLOR_VOID  = (0, 0, 0)
    COLOR_RED   = (200, 55, 55)
    COLOR_WHITE = (240, 235, 210)
    COLOR_GRAY  = (150, 150, 170)

    start = pygame.time.get_ticks()
    duration_ms = 2200

    while pygame.time.get_ticks() - start < duration_ms:
        clock.tick(60)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()

        screen.fill(COLOR_BLACK)
        bar = pygame.Surface((screen_w, 90)); bar.fill(COLOR_VOID)
        screen.blit(bar, (0, 0)); screen.blit(bar, (0, screen_h - 90))

        t = font_title.render("YOU DIED", True, COLOR_RED)
        screen.blit(t, t.get_rect(center=(screen_w // 2, screen_h // 2 - 40)))

        a = font_body.render(f"Attempt {attempts} of 3", True, COLOR_WHITE)
        screen.blit(a, a.get_rect(center=(screen_w // 2, screen_h // 2 + 40)))

        hint = font_body.render("...", True, COLOR_GRAY)
        screen.blit(hint, hint.get_rect(
            center=(screen_w // 2, screen_h - 130)))

        pygame.display.flip()


def _ask_continue_or_giveup(screen, attempts):
    clock = pygame.time.Clock()
    screen_w, screen_h = screen.get_size()

    font_title = _font(56)
    font_body  = _font(28)
    font_btn   = _font(26)

    COLOR_BLACK = (10, 10, 15)
    COLOR_VOID  = (0, 0, 0)
    COLOR_GOLD  = (212, 175, 55)
    COLOR_WHITE = (240, 235, 210)
    COLOR_GRAY  = (150, 150, 170)
    COLOR_RED   = (200, 55, 55)
    COLOR_PANEL = (35, 30, 60)
    COLOR_HOVER = (60, 50, 95)

    cont_btn = pygame.Rect(screen_w // 2 - 250, screen_h // 2 + 100, 220, 70)
    give_btn = pygame.Rect(screen_w // 2 + 30,  screen_h // 2 + 100, 220, 70)

    while True:
        clock.tick(60)
        mouse_pos = pygame.mouse.get_pos()

        screen.fill(COLOR_BLACK)
        bar = pygame.Surface((screen_w, 90)); bar.fill(COLOR_VOID)
        screen.blit(bar, (0, 0)); screen.blit(bar, (0, screen_h - 90))

        t = font_title.render("YOU HAVE FALLEN", True, COLOR_RED)
        screen.blit(t, t.get_rect(center=(screen_w // 2, 240)))

        a = font_body.render(f"Attempt {attempts} - Gorgona still stands.",
                             True, COLOR_WHITE)
        screen.blit(a, a.get_rect(center=(screen_w // 2, 340)))

        q = font_body.render("Do you wish to continue?", True, COLOR_WHITE)
        screen.blit(q, q.get_rect(center=(screen_w // 2, 400)))

        sub = font_body.render("(Refusing to continue ends the story here.)",
                               True, COLOR_GRAY)
        screen.blit(sub, sub.get_rect(center=(screen_w // 2, 450)))

        for rect, label, hover_col in (
            (cont_btn, "CONTINUE", COLOR_HOVER),
            (give_btn, "GIVE UP",  (80, 30, 40)),
        ):
            hovered = rect.collidepoint(mouse_pos)
            fill = hover_col if hovered else COLOR_PANEL
            pygame.draw.rect(screen, fill, rect, border_radius=8)
            pygame.draw.rect(screen, COLOR_GOLD, rect, width=3,
                             border_radius=8)
            col = COLOR_GOLD if hovered else COLOR_WHITE
            lbl = font_btn.render(label, True, col)
            screen.blit(lbl, lbl.get_rect(center=rect.center))

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if cont_btn.collidepoint(event.pos):
                    return "CONTINUE"
                if give_btn.collidepoint(event.pos):
                    return "GIVE_UP"
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    return "CONTINUE"
                if event.key == pygame.K_ESCAPE:
                    return "GIVE_UP"


def _play_timeskip_flash(screen, duration_ms=1600):
    _play_thunder_sfx()

    clock = pygame.time.Clock()
    screen_w, screen_h = screen.get_size()
    start = pygame.time.get_ticks()

    while pygame.time.get_ticks() - start < duration_ms:
        clock.tick(60)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()

        progress = (pygame.time.get_ticks() - start) / float(duration_ms)
        whiteness = int(255 * min(1.0, progress * 1.5))

        screen.fill((10, 10, 15))
        flash = pygame.Surface((screen_w, screen_h))
        flash.fill((255, 255, 255))
        flash.set_alpha(whiteness)
        screen.blit(flash, (0, 0))
        pygame.display.flip()


def _play_victory_cutscene(screen, player_name):
    _play_ending_music(ENDING_VICTORY_MUSIC)

    lines = [
        ("NARRATOR",
         "Gorgona falls. Her castle groans and starts to crumble."),
        ("Gorgona",
         "...impossible... I was... ETERNAL..."),
        ("NARRATOR",
         "A door of light opens in the dark. A figure steps through."),
        ("LUNAIRE", f"{player_name}...?"),
        ("NARRATOR", f"{player_name} turns."),
        (player_name, "Lunaire."),
        ("LUNAIRE", "You... you actually came."),
        (player_name, "I promised, remember?"),
        ("LUNAIRE", "...you kept it."),
        ("NARRATOR",
         "They reach for each other. The world around them goes white."),
    ]
    _play_letterbox_dialogue(screen, lines)

    _play_timeskip_flash(screen)

    skip_lines = [
        ("NARRATOR", "One year later..."),
        ("NARRATOR",
         "The Kingdom of Aurelia celebrates beneath a full moon."),
        ("NARRATOR",
         f"Solaris, Knight of the Crescent Moon, and Lunaire,"),
        ("NARRATOR", "Princess of Aurelia, are bound at last."),
        ("LUNAIRE",
         "...I told you, didn't I? That you'd always find your way back."),
        (player_name, "And I told you - I always come back."),
        ("NARRATOR",
         "The crescent pendant rests between them."),
        ("NARRATOR", "And so ends the tale of the crescent moon."),
    ]
    _play_letterbox_dialogue(screen, skip_lines)


def _play_bad_ending(screen, player_name):
    _play_ending_music(ENDING_DEFEAT_MUSIC)

    lines = [
        ("NARRATOR", f"{player_name} falls. His blade shatters on the stone."),
        ("Gorgona", "Pathetic little knight. You should have stayed home."),
        ("Gorgona",
         "The princess will wait forever. And the moon will go dark."),
        ("NARRATOR", "The world dims."),
        ("NARRATOR", "There is no one left to save her."),
        ("NARRATOR", "BAD ENDING."),
    ]
    _play_letterbox_dialogue(screen, lines)


def _show_the_end_screen(screen):
    _play_ending_music(END_SCREEN_MUSIC, volume=END_SCREEN_MUSIC_VOL)

    clock = pygame.time.Clock()
    screen_w, screen_h = screen.get_size()

    font_title = _font(120)
    font_sub   = _font(30)
    font_btn   = _font(28)

    COLOR_BLACK = (10, 10, 15)
    COLOR_VOID  = (0, 0, 0)
    COLOR_GOLD  = (212, 175, 55)
    COLOR_BRIGHT_GOLD = (255, 215, 0)
    COLOR_WHITE = (240, 235, 210)
    COLOR_GRAY  = (150, 150, 170)
    COLOR_PANEL = (35, 30, 60)
    COLOR_HOVER = (60, 50, 95)

    next_btn = pygame.Rect(screen_w // 2 - 130, screen_h // 2 + 200, 260, 70)

    start = pygame.time.get_ticks()
    fade_ms = 800

    while True:
        clock.tick(60)
        mouse_pos = pygame.mouse.get_pos()
        now = pygame.time.get_ticks()

        screen.fill(COLOR_BLACK)
        bar = pygame.Surface((screen_w, 90)); bar.fill(COLOR_VOID)
        screen.blit(bar, (0, 0)); screen.blit(bar, (0, screen_h - 90))

        alpha = min(255, int(255 * ((now - start) / float(fade_ms))))

        title = font_title.render("THE END", True, COLOR_BRIGHT_GOLD)
        title.set_alpha(alpha)
        screen.blit(title, title.get_rect(center=(screen_w // 2, screen_h // 2 - 80)))

        line_surf = pygame.Surface((420, 2), pygame.SRCALPHA)
        line_surf.fill((*COLOR_GOLD, alpha))
        screen.blit(line_surf, line_surf.get_rect(center=(screen_w // 2, screen_h // 2 + 30)))

        sub = font_sub.render("Press NEXT to continue", True, COLOR_WHITE)
        sub.set_alpha(alpha)
        screen.blit(sub, sub.get_rect(center=(screen_w // 2, screen_h // 2 + 80)))

        if now - start >= fade_ms:
            hovered = next_btn.collidepoint(mouse_pos)
            fill = COLOR_HOVER if hovered else COLOR_PANEL
            pygame.draw.rect(screen, fill, next_btn, border_radius=10)
            pygame.draw.rect(screen, COLOR_GOLD, next_btn, width=3,
                             border_radius=10)
            col = COLOR_GOLD if hovered else COLOR_WHITE
            lbl = font_btn.render("NEXT", True, col)
            screen.blit(lbl, lbl.get_rect(center=next_btn.center))

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if now - start < fade_ms:
                continue
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if next_btn.collidepoint(event.pos):
                    return
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_e):
                    return


def _show_journey_screen(screen, player_name, ending_type):
    clock = pygame.time.Clock()
    screen_w, screen_h = screen.get_size()

    font_title = _font(64)
    font_sub   = _font(38)
    font_body  = _font(24)
    font_btn   = _font(26)

    COLOR_BLACK = (10, 10, 15)
    COLOR_VOID  = (0, 0, 0)
    COLOR_GOLD  = (212, 175, 55)
    COLOR_BRIGHT_GOLD = (255, 215, 0)
    COLOR_WHITE = (240, 235, 210)
    COLOR_GRAY  = (150, 150, 170)
    COLOR_RED   = (200, 55, 55)
    COLOR_PANEL = (35, 30, 60)
    COLOR_HOVER = (60, 50, 95)

    if ending_type == "GOOD":
        sub_text = "Happy Ending"
        sub_color = COLOR_BRIGHT_GOLD
        body_lines = [
            "The crescent moon shines again.",
            "Lunaire is safe. Aurelia is at peace.",
            "And the knight kept his promise.",
        ]
    else:
        sub_text = "Bad Ending"
        sub_color = COLOR_RED
        body_lines = [
            "The knight fell at the Empress's throne.",
            "Lunaire waits still.",
            "The moon remains dark.",
        ]

    btn_w = 320
    btn_h = 76
    gap = 40
    total_w = btn_w * 2 + gap
    left_x = screen_w // 2 - total_w // 2
    right_x = left_x + btn_w + gap
    btn_y = screen_h // 2 + 190

    start_new_btn = pygame.Rect(left_x,  btn_y, btn_w, btn_h)
    restart_btn   = pygame.Rect(right_x, btn_y, btn_w, btn_h)

    start = pygame.time.get_ticks()
    fade_ms = 700

    while True:
        clock.tick(60)
        mouse_pos = pygame.mouse.get_pos()
        now = pygame.time.get_ticks()

        screen.fill(COLOR_BLACK)
        bar = pygame.Surface((screen_w, 90)); bar.fill(COLOR_VOID)
        screen.blit(bar, (0, 0)); screen.blit(bar, (0, screen_h - 90))

        alpha = min(255, int(255 * ((now - start) / float(fade_ms))))

        title = font_title.render(
            f"End of {player_name}'s journey", True, COLOR_BRIGHT_GOLD)
        title.set_alpha(alpha)
        screen.blit(title, title.get_rect(center=(screen_w // 2, 260)))

        sub = font_sub.render(sub_text, True, sub_color)
        sub.set_alpha(alpha)
        screen.blit(sub, sub.get_rect(center=(screen_w // 2, 350)))

        y = 440
        for ln in body_lines:
            s = font_body.render(ln, True, COLOR_WHITE)
            s.set_alpha(alpha)
            screen.blit(s, s.get_rect(center=(screen_w // 2, y)))
            y += 40

        if now - start >= fade_ms:
            for rect, label, hover_col in (
                (start_new_btn, "START NEW", COLOR_HOVER),
                (restart_btn,   "RESTART",   (80, 30, 40)),
            ):
                hovered = rect.collidepoint(mouse_pos)
                fill = hover_col if hovered else COLOR_PANEL
                pygame.draw.rect(screen, fill, rect, border_radius=10)
                pygame.draw.rect(screen, COLOR_GOLD, rect, width=3,
                                 border_radius=10)
                col = COLOR_GOLD if hovered else COLOR_WHITE
                lbl = font_btn.render(label, True, col)
                screen.blit(lbl, lbl.get_rect(center=rect.center))

            hint = font_body.render(
                "[ START NEW: save & return to menu  |  RESTART: play again ]",
                True, COLOR_GRAY)
            screen.blit(hint, hint.get_rect(
                center=(screen_w // 2, screen_h - 130)))

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if now - start < fade_ms:
                continue
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if start_new_btn.collidepoint(event.pos):
                    return "NEW"
                if restart_btn.collidepoint(event.pos):
                    return "RESTART"
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_e):
                    return "NEW"
                if event.key == pygame.K_r:
                    return "RESTART"


def _run_three_phases(screen, player, boss, slot_id,
                      viewport_particles=None, viewport_tint=None):

    for phase_idx in range(3):
        if phase_idx > 0:
            _play_phase_transition(screen, phase_idx - 1, phase_idx)

        charges = {"elem": ELEM_CHARGES_MAX, "burst": BURST_CHARGES_MAX}

        result = run_battle(
            screen, player, [boss],
            slot_id=slot_id,
            attackers_override=1,
            charges=charges,
            skip_intro=(phase_idx > 0),
            allow_flee=False,
            show_end_banner=False,
            viewport_particles=viewport_particles,
            viewport_tint=viewport_tint,
        )

        if result == "DEFEAT":
            return "DEFEAT"
        if result == "FLED":
            return "FLED"

        if boss.is_final_phase:
            return "VICTORY"
        else:
            boss.try_advance_phase()

    return "VICTORY"


def run_final_battle(screen, player, slot_id=1):
    player_name = getattr(player, "name", "Solaris")

    _show_gorgona_tutorial(screen)
    _play_final_banner(screen)

    fight_particles, fight_tint = _build_fight_mood()

    deaths = 0

    while True:
        boss = Gorgona(x=0, y=0, scale=1.0)

        result = _run_three_phases(
            screen, player, boss, slot_id,
            viewport_particles=fight_particles,
            viewport_tint=fight_tint,
        )

        if result == "VICTORY":
            play_battle_end_banner(screen, True)
            _play_victory_cutscene(screen, player_name)
            _strip_temp_potion_buffs(player)

            _show_the_end_screen(screen)
            choice = _show_journey_screen(screen, player_name, "GOOD")
            if choice == "RESTART":
                return "VICTORY_RESTART"
            return "VICTORY_NEW"

        deaths += 1

        play_battle_end_banner(screen, False)

        _play_death_cutscene(screen, player_name, deaths)

        if deaths >= 3:
            choice = _ask_continue_or_giveup(screen, deaths)
            if choice == "GIVE_UP":
                _play_bad_ending(screen, player_name)
                _strip_temp_potion_buffs(player)

                _show_the_end_screen(screen)
                journey_choice = _show_journey_screen(screen, player_name, "BAD")
                if journey_choice == "RESTART":
                    return "BAD_ENDING_RESTART"
                return "BAD_ENDING_NEW"
        else:
            _show_death_screen(screen, deaths, player_name)

        if hasattr(player, "respawn"):
            player.respawn()