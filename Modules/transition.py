import os
import sys
import math
import random
import pygame

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

COLOR_BG        = (15, 15, 30)
COLOR_PANEL     = (28, 26, 48)
COLOR_BORDER    = (212, 175, 55)
COLOR_GOLD      = (255, 215, 0)
COLOR_GLOW_GOLD = (255, 230, 140)
COLOR_WHITE     = (240, 235, 210)


def run_transition(screen, message="Entering Realm...", duration_sec=1.2):

    clock = pygame.time.Clock()
    screen_w, screen_h = screen.get_size()

    font_path = os.path.join(PROJECT_ROOT, "asset", "font", "TheGothicRite.otf")
    if os.path.exists(font_path):
        font_title = pygame.font.Font(font_path, 28)
        font_sub = pygame.font.Font(font_path, 18)
    else:
        font_title = pygame.font.SysFont("Georgia", 28, bold=True)
        font_sub = pygame.font.SysFont("Georgia", 18, bold=True)

    target_frames = max(1, int(duration_sec * 60))
    frame_count = 0

    stars = [
        {
            "x": random.randint(0, screen_w),
            "y": random.randint(0, screen_h),
            "speed": random.uniform(0.15, 0.4),
            "size": random.randint(1, 2)
        }
        for _ in range(60)
    ]

    fade_surf = pygame.Surface((screen_w, screen_h))
    fade_surf.fill(COLOR_BG)

    running = True
    while running and frame_count < target_frames:
        clock.tick(60)
        frame_count += 1
        progress = min(1.0, frame_count / float(target_frames))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        screen.fill(COLOR_BG)

        for star in stars:
            star["x"] -= star["speed"]
            if star["x"] < 0:
                star["x"] = screen_w
                star["y"] = random.randint(0, screen_h)
            alpha = int(120 + math.sin(frame_count * 0.04 + star["x"]) * 90)
            star_surf = pygame.Surface((star["size"], star["size"]), pygame.SRCALPHA)
            star_surf.fill((255, 255, 255, max(0, min(255, alpha))))
            screen.blit(star_surf, (star["x"], star["y"]))

        alpha_pulse = int(200 + math.sin(frame_count * 0.1) * 55)
        text_surf = font_title.render(message, True, COLOR_WHITE)
        text_surf.set_alpha(alpha_pulse)
        text_rect = text_surf.get_rect(center=(screen_w // 2, screen_h // 2 - 20))
        screen.blit(text_surf, text_rect)

        bar_w, bar_h = 360, 6
        bar_x = (screen_w - bar_w) // 2
        bar_y = screen_h // 2 + 30

        pygame.draw.rect(screen, COLOR_BORDER,
                         (bar_x - 2, bar_y - 2, bar_w + 4, bar_h + 4),
                         width=2, border_radius=4)

        pygame.draw.rect(screen, COLOR_PANEL,
                         (bar_x, bar_y, bar_w, bar_h), border_radius=3)

        fill_w = int(progress * bar_w)
        if fill_w > 0:
            pygame.draw.rect(screen, COLOR_GOLD,
                             (bar_x, bar_y, fill_w, bar_h), border_radius=3)

        pct_surf = font_sub.render(f"{int(progress * 100)}%", True, COLOR_GLOW_GOLD)
        pct_rect = pct_surf.get_rect(center=(screen_w // 2, bar_y + 25))
        screen.blit(pct_surf, pct_rect)

        fade_out_frames = 15
        if frame_count >= target_frames - fade_out_frames:
            fade_alpha = int(255 * ((frame_count - (target_frames - fade_out_frames)) / fade_out_frames))
            fade_surf.set_alpha(fade_alpha)
            screen.blit(fade_surf, (0, 0))

        pygame.display.flip()