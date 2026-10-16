import os
import sys
import pygame

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from Modules.button import Button, draw_corner_brackets
from Fmain_menu.ingame_setting import run_ingame_settings
from Modules.save_manager import save_full_game_state


def _ask_quit_confirmation(screen, font_title, font_button, font_section):

    clock = pygame.time.Clock()
    screen_w, screen_h = screen.get_size()
    snapshot = screen.copy()

    COLOR_WARN_YELLOW = (255, 210, 60)
    COLOR_WARN_DARK   = (30, 20, 10)
    COLOR_RED_BORDER  = (220, 80, 80)
    COLOR_RED_DIM     = (140, 50, 50)
    COLOR_BRIGHT_GOLD = (255, 215, 0)
    COLOR_GOLD        = (212, 175, 55)
    COLOR_WHITE       = (240, 235, 210)
    COLOR_GRAY        = (150, 150, 170)
    COLOR_PANEL       = (35, 28, 45)

    COLOR_RED_BG      = (70, 25, 35)
    COLOR_RED_HOVER   = (200, 60, 80)
    COLOR_NEUTRAL_BG  = (35, 30, 60)
    COLOR_NEUTRAL_HOV = (60, 50, 95)

    panel_w, panel_h = 780, 420
    panel_rect = pygame.Rect(
        screen_w // 2 - panel_w // 2,
        screen_h // 2 - panel_h // 2,
        panel_w, panel_h,
    )

    btn_w, btn_h = 250, 64
    gap = 30
    total_w = btn_w * 2 + gap
    left_x  = panel_rect.centerx - total_w // 2
    right_x = left_x + btn_w + gap
    btn_y   = panel_rect.bottom - btn_h - 60

    quit_btn   = pygame.Rect(left_x,  btn_y, btn_w, btn_h)
    cancel_btn = pygame.Rect(right_x, btn_y, btn_w, btn_h)

    while True:
        clock.tick(60)
        mouse_pos = pygame.mouse.get_pos()

        screen.blit(snapshot, (0, 0))
        dim = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 205))
        screen.blit(dim, (0, 0))

        pygame.draw.rect(screen, COLOR_PANEL, panel_rect, border_radius=12)
        pygame.draw.rect(screen, COLOR_RED_BORDER, panel_rect,
                         width=3, border_radius=12)
        try:
            draw_corner_brackets(screen, panel_rect, COLOR_RED_BORDER,
                                 length=26, thickness=3, offset=8)
        except Exception:
            pass

        tri_cx   = panel_rect.centerx
        tri_top  = panel_rect.top + 35
        tri_size = 62

        triangle_pts = [
            (tri_cx, tri_top),
            (tri_cx - tri_size // 2, tri_top + tri_size),
            (tri_cx + tri_size // 2, tri_top + tri_size),
        ]
        pygame.draw.polygon(screen, COLOR_WARN_YELLOW, triangle_pts)
        pygame.draw.polygon(screen, COLOR_WARN_DARK, triangle_pts, 3)

        try:
            font_ex = pygame.font.SysFont("Arial", 40, bold=True)
        except Exception:
            font_ex = font_button
        ex_surf = font_ex.render("!", True, COLOR_WARN_DARK)
        screen.blit(ex_surf, ex_surf.get_rect(
            center=(tri_cx, tri_top + tri_size // 2 + 8)))

        title = font_title.render("QUIT WITHOUT SAVING?", True, COLOR_WARN_YELLOW)
        screen.blit(title, title.get_rect(
            center=(panel_rect.centerx, tri_top + tri_size + 42)))

        line_y = tri_top + tri_size + 76
        pygame.draw.line(screen, COLOR_RED_DIM,
                         (panel_rect.left + 70, line_y),
                         (panel_rect.right - 70, line_y),
                         2)

        msg1 = font_button.render(
            "You will lose all progress since your last save.",
            True, COLOR_WHITE)
        msg2 = font_button.render(
            "Quit to the main menu anyway?",
            True, COLOR_WARN_YELLOW)
        screen.blit(msg1, msg1.get_rect(
            center=(panel_rect.centerx, line_y + 38)))
        screen.blit(msg2, msg2.get_rect(
            center=(panel_rect.centerx, line_y + 74)))

        for rect, label, base_col, hover_col, border_col in (
            (quit_btn,   "YES", COLOR_RED_BG,     COLOR_RED_HOVER,
             COLOR_RED_BORDER),
            (cancel_btn, "NO",  COLOR_NEUTRAL_BG, COLOR_NEUTRAL_HOV,
             COLOR_GOLD),
        ):
            hovered = rect.collidepoint(mouse_pos)
            fill = hover_col if hovered else base_col
            pygame.draw.rect(screen, fill, rect, border_radius=8)
            pygame.draw.rect(screen, border_col, rect,
                             width=3, border_radius=8)
            col = COLOR_BRIGHT_GOLD if hovered else COLOR_WHITE
            lbl = font_button.render(label, True, col)
            screen.blit(lbl, lbl.get_rect(center=rect.center))

        hint = font_section.render(
            "[ Y: YES (quit without saving)   |   N or ESC: NO ]",
            True, COLOR_GRAY)
        screen.blit(hint, hint.get_rect(
            center=(panel_rect.centerx, panel_rect.bottom - 20)))

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if quit_btn.collidepoint(event.pos):
                    return True
                if cancel_btn.collidepoint(event.pos):
                    return False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_y:
                    return True
                if event.key in (pygame.K_n, pygame.K_ESCAPE):
                    return False


def run_pause_menu(screen, frame=None, slot_id=1, player=None, wizard=None,
                   orc=None, enemies=None, on_save=None):

    clock = pygame.time.Clock()
    running = True
    action_result = None
    save_notification_timer = 0

    COLOR_PANEL     = (28, 26, 48)
    COLOR_BORDER    = (212, 175, 55)
    COLOR_GOLD      = (255, 215, 0)
    COLOR_GREEN     = (120, 220, 130)
    COLOR_TEXT_GRAY = (150, 150, 170)
    COLOR_BTN_BG    = (35, 30, 60)
    COLOR_BTN_HOV   = (60, 50, 95)

    screen_w, screen_h = screen.get_size()
    center_x = screen_w // 2
    center_y = screen_h // 2

    bg_snapshot = screen.copy()

    dark_overlay = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
    dark_overlay.fill((10, 10, 20, 190))

    FONT_PATH = os.path.join(PROJECT_ROOT, "asset", "font", "TheGothicRite.otf")
    try:
        font_title = pygame.font.Font(FONT_PATH, 38)
        font_button = pygame.font.Font(FONT_PATH, 22)
        font_msg = pygame.font.Font(FONT_PATH, 18)
        font_section = pygame.font.Font(FONT_PATH, 16)
    except FileNotFoundError:
        font_title = pygame.font.SysFont("Georgia", 38, bold=True)
        font_button = pygame.font.SysFont("Georgia", 22, bold=True)
        font_msg = pygame.font.SysFont("Georgia", 18)
        font_section = pygame.font.SysFont("Georgia", 16, bold=True)

    panel_w, panel_h = 440, 480
    container_rect = pygame.Rect(center_x - (panel_w // 2),
                                 center_y - (panel_h // 2),
                                 panel_w, panel_h)

    btn_w, btn_h = 340, 46
    btn_x = center_x - (btn_w // 2)

    def make_btn(x, y, text):
        return Button(
            x, y, btn_w, btn_h, text=text, font=font_button,
            bg_color=COLOR_BTN_BG, hover_color=COLOR_BTN_HOV,
            text_color=COLOR_GOLD, border_color=COLOR_BORDER,
            border_radius=8,
        )

    resume_btn   = make_btn(btn_x, center_y - 120, "RESUME")
    save_btn     = make_btn(btn_x, center_y - 55,  f"SAVE GAME (SLOT {slot_id})")
    settings_btn = make_btn(btn_x, center_y + 10,  "SETTINGS")
    quit_btn     = make_btn(btn_x, center_y + 75,  "QUIT TO MAIN MENU")

    pause_buttons = [resume_btn, save_btn, settings_btn, quit_btn]

    title_surf = font_title.render("GAME PAUSED", True, COLOR_GOLD)
    title_rect = title_surf.get_rect(center=(center_x, container_rect.top + 45))
    hint_surf = font_button.render("[Press ESC to Resume]", True, COLOR_TEXT_GRAY)
    hint_rect = hint_surf.get_rect(center=(center_x, container_rect.bottom - 25))

    panel_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
    panel_surf.fill((*COLOR_PANEL, 245))
    panel_blit_rect = panel_surf.get_rect(center=container_rect.center)

    while running:
        clock.tick(60)
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if resume_btn.rect.collidepoint(mouse_pos):
                    running = False
                elif save_btn.rect.collidepoint(mouse_pos):
                    save_full_game_state(
                        slot_id, player=player, wizard=wizard,
                        orc=orc, enemies=enemies, position_valid=True,
                    )
                    save_notification_timer = 120

                    if callable(on_save):
                        try:
                            on_save()
                        except Exception as e:
                            print(f"[pause_menu] on_save callback failed: {e}")

                elif settings_btn.rect.collidepoint(mouse_pos):
                    run_ingame_settings(screen, bg_snapshot)

                elif quit_btn.rect.collidepoint(mouse_pos):
                    if _ask_quit_confirmation(
                        screen, font_title, font_button, font_section
                    ):
                        action_result = "QUIT_TO_MENU"
                        running = False

        screen.blit(bg_snapshot, (0, 0))
        screen.blit(dark_overlay, (0, 0))

        screen.blit(panel_surf, panel_blit_rect.topleft)
        pygame.draw.rect(screen, COLOR_BORDER, container_rect,
                         width=3, border_radius=12)
        draw_corner_brackets(screen, container_rect, COLOR_BORDER,
                             length=24, thickness=3, offset=8)

        pygame.draw.line(screen, COLOR_BORDER,
                         (container_rect.left + 60, container_rect.top + 80),
                         (container_rect.right - 60, container_rect.top + 80),
                         2)

        screen.blit(title_surf, title_rect)
        screen.blit(hint_surf, hint_rect)

        for btn in pause_buttons:
            try:
                btn.update(mouse_pos)
            except TypeError:
                btn.update()
            try:
                btn.draw(screen, mouse_pos)
            except TypeError:
                btn.draw(screen)

        if save_notification_timer > 0:
            save_notification_timer -= 1
            save_surf = font_msg.render(
                f"[!] GAME SAVED TO SLOT {slot_id}", True, COLOR_GREEN)
            save_rect = save_surf.get_rect(
                center=(center_x, container_rect.bottom - 55))
            screen.blit(save_surf, save_rect)

        pygame.display.flip()

    return action_result