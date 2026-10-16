
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
    play_battle_end_banner,
    play_transition_sfx,
)


def _ease_out_cubic(t):
    return 1 - (1 - t) ** 3


def _ease_in_cubic(t):
    return t * t * t


def show_wave_banner(screen, current_wave=1, total_waves=1, duration_sec=1.6):
    try:
        play_transition_sfx()
    except Exception:
        pass

    clock = pygame.time.Clock()
    screen_w, screen_h = screen.get_size()

    font_path = os.path.join(PROJECT_ROOT, "asset", "font", "TheGothicRite.otf")
    if os.path.exists(font_path):
        font_big   = pygame.font.Font(font_path, 96)
        font_small = pygame.font.Font(font_path, 32)
    else:
        font_big   = pygame.font.SysFont("Georgia", 96, bold=True)
        font_small = pygame.font.SysFont("Georgia", 32, bold=True)

    big_text = "THE BATTLE BEGINS!"
    sub_text = "Enemies incoming!"

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
                running = False
                break
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_ESCAPE):
                    running = False
                    break

        if not running:
            break

        t = elapsed / duration_sec

        if t < 0.10:
            overlay_a = t / 0.10
        elif t < 0.75:
            overlay_a = 1.0
        else:
            overlay_a = max(0.0, 1.0 - (t - 0.75) / 0.25)

        if t < 0.35:
            local = t / 0.35
            base = 0.55 + 0.45 * _ease_out_cubic(local)
            overshoot = math.sin(local * math.pi) * 0.10
            scale = base + overshoot
        elif t < 0.75:
            scale = 1.0
        else:
            local = (t - 0.75) / 0.25
            scale = 1.0 - 0.15 * _ease_in_cubic(local)

        beam_alpha = int(200 * overlay_a)
        text_alpha = int(255 * overlay_a)

        overlay = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, int(220 * overlay_a)))
        screen.blit(overlay, (0, 0))

        beam_h = max(2, int(6 * scale))
        beam = pygame.Surface((screen_w, beam_h), pygame.SRCALPHA)
        beam.fill((255, 215, 0, beam_alpha))
        beam_y = screen_h // 2 - 10 - beam_h // 2
        screen.blit(beam, (0, beam_y))

        bw = max(1, int(big_base.get_width() * scale))
        bh = max(1, int(big_base.get_height() * scale))
        big_scaled = pygame.transform.scale(big_base, (bw, bh))
        out_scaled = pygame.transform.scale(big_out, (bw, bh))

        cx = screen_w // 2
        cy = screen_h // 2 - 20

        big_scaled.set_alpha(text_alpha)
        out_scaled.set_alpha(text_alpha)

        for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2),
                       (-2, -2), (2, -2), (-2, 2), (2, 2)):
            r = out_scaled.get_rect(center=(cx + dx, cy + dy))
            screen.blit(out_scaled, r)

        r = big_scaled.get_rect(center=(cx, cy))
        screen.blit(big_scaled, r)

        sub_surf.set_alpha(text_alpha)
        sub_rect = sub_surf.get_rect(center=(cx, cy + 80))
        screen.blit(sub_surf, sub_rect)

        pygame.display.flip()


def run_multi_battle(screen, player, waves, slot_id=1):
    waves = [w for w in waves if w]
    if not waves:
        return "VICTORY"

    total = len(waves)
    charges = {"elem": ELEM_CHARGES_MAX, "burst": BURST_CHARGES_MAX}

    for i, wave in enumerate(waves):
        if i > 0:
            show_wave_banner(screen, i + 1, total)

        if isinstance(wave, dict):
            w_enemies = wave.get("enemies", [])
            w_attackers = wave.get("attackers")
        else:
            w_enemies = wave
            w_attackers = None

        live_wave = [e for e in w_enemies if getattr(e, "hp", 0) > 0]
        if not live_wave:
            continue

        result = run_battle(screen, player, live_wave,
                            slot_id=slot_id,
                            attackers_override=w_attackers,
                            charges=charges,
                            skip_intro=(i > 0),
                            show_end_banner=False)

        if result == "DEFEAT":
            play_battle_end_banner(screen, False)
            _strip_temp_potion_buffs(player)
            return "DEFEAT"
        if result == "FLED":
            _strip_temp_potion_buffs(player)
            return "FLED"

    play_battle_end_banner(screen, True)
    _strip_temp_potion_buffs(player)
    return "VICTORY"