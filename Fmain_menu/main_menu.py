import sys
import os
import math
import random

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

CACHE_DIR = os.path.join(PROJECT_ROOT, "saves", "__pycache__")
os.makedirs(CACHE_DIR, exist_ok=True)
sys.pycache_prefix = CACHE_DIR

import pygame
from Modules.button import Button
from Modules.sound_manager import game_manager
from Fmain_menu.play_continue import run_save_select
from Fmain_menu.setting import run_settings
from Fmain_menu.about import run_about


def run_main_menu(screen=None):

    if not pygame.get_init():
        pygame.init()

    game_manager.play_music("default.mp3")

    SCREEN_WIDTH = 1920
    SCREEN_HEIGHT = 1080
    FPS = 60

    COLOR_WHITE   = (240, 235, 210)
    COLOR_GOLD    = (255, 215, 0)
    COLOR_BORDER  = (212, 175, 55)
    COLOR_BTN_BG  = (35, 30, 60)
    COLOR_BTN_HOV = (70, 60, 105)
    COLOR_SHADOW  = (10, 10, 20)

    if screen is None:
        screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Solaris: Knight of the Crescent Moon")

    clock = pygame.time.Clock()

    bg_path = os.path.join(PROJECT_ROOT, "asset", "main_menu", "main_menu.png")
    if os.path.exists(bg_path):
        raw_bg = pygame.image.load(bg_path).convert_alpha()
        bg_image = pygame.transform.scale(raw_bg, (SCREEN_WIDTH, SCREEN_HEIGHT))
    else:
        bg_image = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        bg_image.fill((15, 15, 30))

    font_path = os.path.join(PROJECT_ROOT, "asset", "font", "TheGothicRite.otf")
    try:
        title_font = pygame.font.Font(font_path, 80)
        button_font = pygame.font.Font(font_path, 48)
    except (FileNotFoundError, OSError):
        title_font = pygame.font.SysFont("Georgia", 80, bold=True)
        button_font = pygame.font.SysFont("Georgia", 48, bold=True)

    play_btn = Button(
        160, 395, 360, 90, text="PLAY", font=button_font,
        bg_color=COLOR_BTN_BG, hover_color=COLOR_BTN_HOV,
        text_color=COLOR_GOLD, border_color=COLOR_BORDER,
        border_radius=10,
    )
    setting_btn = Button(
        160, 515, 360, 90, text="Settings", font=button_font,
        bg_color=COLOR_BTN_BG, hover_color=COLOR_BTN_HOV,
        text_color=COLOR_GOLD, border_color=COLOR_BORDER,
        border_radius=10,
    )
    about_btn = Button(
        160, 635, 360, 90, text="About", font=button_font,
        bg_color=COLOR_BTN_BG, hover_color=COLOR_BTN_HOV,
        text_color=COLOR_GOLD, border_color=COLOR_BORDER,
        border_radius=10,
    )

    t1_surf = title_font.render("Solaris: Knight of the", True, COLOR_WHITE)
    t1_shadow = title_font.render("Solaris: Knight of the", True, COLOR_SHADOW)

    t2_surf = title_font.render("Crescent Moon", True, COLOR_GOLD)
    t2_shadow = title_font.render("Crescent Moon", True, COLOR_SHADOW)

    t1_rect = t1_surf.get_rect(center=(420, 125))
    t2_rect = t2_surf.get_rect(center=(420, 205))

    stars = [
        {
            "x": random.randint(0, SCREEN_WIDTH),
            "y": random.randint(0, SCREEN_HEIGHT),
            "speed": random.uniform(0.15, 0.4),
            "size": random.randint(1, 3)
        }
        for _ in range(70)
    ]

    frame_count = 0
    run = True
    while run:
        frame_count += 1

        screen.blit(bg_image, (0, 0))

        for star in stars:
            star["x"] -= star["speed"]
            if star["x"] < 0:
                star["x"] = SCREEN_WIDTH
                star["y"] = random.randint(0, SCREEN_HEIGHT)
            alpha = int(120 + math.sin(frame_count * 0.04 + star["x"]) * 90)
            star_surf = pygame.Surface((star["size"], star["size"]), pygame.SRCALPHA)
            star_surf.fill((255, 255, 255, max(0, min(255, alpha))))
            screen.blit(star_surf, (star["x"], star["y"]))

        screen.blit(t1_shadow, (t1_rect.x + 4, t1_rect.y + 4))
        screen.blit(t1_surf, t1_rect)

        screen.blit(t2_shadow, (t2_rect.x + 4, t2_rect.y + 4))
        screen.blit(t2_surf, t2_rect)

        if play_btn.draw(screen):
            run_save_select(screen)

        if setting_btn.draw(screen):
            run_settings(screen)

        if about_btn.draw(screen):
            run_about(screen)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False

        pygame.display.flip()
        clock.tick(FPS)


if __name__ == "__main__":
    run_main_menu()
    pygame.quit()
    sys.exit()