import os
import sys
import pygame

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from Modules.button import Button, draw_corner_brackets


def run_stats_menu(screen, arg2, player=None):

    if player is None:
        player = arg2

    clock = pygame.time.Clock()

    COLOR_GOLD      = (255, 215, 0)
    COLOR_BORDER    = (212, 175, 55)
    COLOR_PANEL     = (28, 26, 48, 245)
    COLOR_TEXT      = (240, 235, 210)
    COLOR_LABEL     = (180, 175, 155)
    COLOR_DIVIDER   = (60, 55, 85)
    COLOR_BTN_BG    = (35, 30, 60)
    COLOR_BTN_HOV   = (60, 50, 95)

    font_path = os.path.join(PROJECT_ROOT, "asset", "font", "TheGothicRite.otf")
    if os.path.exists(font_path):
        font_title = pygame.font.Font(font_path, 38)
        font_stat = pygame.font.Font(font_path, 22)
        font_btn = pygame.font.Font(font_path, 20)
    else:
        font_title = pygame.font.SysFont("Georgia", 38, bold=True)
        font_stat = pygame.font.SysFont("Georgia", 22, bold=True)
        font_btn = pygame.font.SysFont("Georgia", 20, bold=True)

    bg_snapshot = screen.copy()
    overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    overlay.fill((10, 10, 20, 190))

    screen_w, screen_h = screen.get_size()
    center_x = screen_w // 2
    center_y = screen_h // 2

    panel_w, panel_h = 580, 600
    panel_rect = pygame.Rect(center_x - (panel_w // 2), center_y - (panel_h // 2), panel_w, panel_h)

    btn_w, btn_h = 240, 50
    btn_close = Button(
        center_x - (btn_w // 2),
        panel_rect.bottom - 70,
        btn_w,
        btn_h,
        text="CLOSE [ESC]",
        font=font_btn,
        bg_color=COLOR_BTN_BG,
        hover_color=COLOR_BTN_HOV,
        text_color=COLOR_GOLD,
        border_color=COLOR_BORDER,
        border_radius=8
    )

    p_name = getattr(player, "name", "Solaris")
    p_hp = getattr(player, "hp", 100)
    p_max_hp = getattr(player, "max_hp", 100)
    p_atk = getattr(player, "atk", 5)
    p_def = getattr(player, "defense", 5)
    p_elem_atk = getattr(player, "elemental_attack", 0)

    stats_list = [
        ("Hero Name", f"{p_name}"),
        ("Health Points", f"{p_hp} / {p_max_hp}"),
        ("Attack", f"{p_atk}"),
        ("Defense", f"{p_def}"),
        ("Elemental Attack", f"{p_elem_atk}"),
    ]

    running = True

    while running:
        clock.tick(60)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

        screen.blit(bg_snapshot, (0, 0))
        screen.blit(overlay, (0, 0))

        panel_bg = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel_bg.fill(COLOR_PANEL)
        screen.blit(panel_bg, panel_rect.topleft)

        pygame.draw.rect(screen, COLOR_BORDER, panel_rect, width=3, border_radius=10)
        draw_corner_brackets(screen, panel_rect, COLOR_BORDER, length=28, thickness=3, offset=8)

        title_surf = font_title.render("CHARACTER STATS", True, COLOR_GOLD)
        title_rect = title_surf.get_rect(center=(center_x, panel_rect.top + 45))
        screen.blit(title_surf, title_rect)

        line_y = panel_rect.top + 80
        pygame.draw.line(screen, COLOR_BORDER, (panel_rect.left + 35, line_y), (panel_rect.right - 35, line_y), 2)

        start_y = panel_rect.top + 100
        row_spacing = 42

        for index, (label_str, val_str) in enumerate(stats_list):
            curr_y = start_y + (index * row_spacing)

            lbl_surf = font_stat.render(label_str, True, COLOR_LABEL)
            screen.blit(lbl_surf, (panel_rect.left + 50, curr_y))

            val_surf = font_stat.render(val_str, True, COLOR_TEXT)
            val_rect = val_surf.get_rect(topright=(panel_rect.right - 50, curr_y))
            screen.blit(val_surf, val_rect)

            if index < len(stats_list) - 1:
                subtle_line_y = curr_y + 32
                pygame.draw.line(
                    screen,
                    COLOR_DIVIDER,
                    (panel_rect.left + 45, subtle_line_y),
                    (panel_rect.right - 45, subtle_line_y),
                    1
                )

        if btn_close.draw(screen):
            running = False

        draw_corner_brackets(screen, btn_close.rect, COLOR_BORDER, length=14, thickness=2, offset=4)

        pygame.display.flip()