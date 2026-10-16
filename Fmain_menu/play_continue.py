import math
import os
import random
import sys
import pygame

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from Modules.button import Button, draw_corner_brackets
from Modules.transition import run_transition
from Modules.save_manager import load_save_data, save_save_data, delete_save_data
from Modules.sound_manager import game_manager
from player.player import Player
from Fmain_menu.prologue import run_prologue
from Fmain_menu.tutorial import run_tutorial

from gameplay.map_router import run_gameplay_with_map_switching


def wait_for_mouse_release():
    pygame.event.clear()
    while any(pygame.mouse.get_pressed()):
        pygame.event.pump()
        pygame.time.wait(10)
    pygame.event.clear()


def _show_game_complete_screen(screen, player_name):
    clock = pygame.time.Clock()
    screen_w, screen_h = screen.get_size()

    font_path = os.path.join(PROJECT_ROOT, "asset", "font", "TheGothicRite.otf")
    try:
        font_title = pygame.font.Font(font_path, 120)
        font_sub   = pygame.font.Font(font_path, 30)
        font_hint  = pygame.font.Font(font_path, 22)
    except (FileNotFoundError, OSError):
        font_title = pygame.font.SysFont("Georgia", 120, bold=True)
        font_sub   = pygame.font.SysFont("Georgia", 30, bold=True)
        font_hint  = pygame.font.SysFont("Georgia", 22)

    COLOR_BLACK = (10, 10, 15)
    COLOR_VOID  = (0, 0, 0)
    COLOR_BRIGHT_GOLD = (255, 215, 0)
    COLOR_GOLD  = (212, 175, 55)
    COLOR_WHITE = (240, 235, 210)
    COLOR_GRAY  = (150, 150, 170)
    COLOR_PANEL = (35, 30, 60)
    COLOR_HOVER = (60, 50, 95)

    menu_btn = pygame.Rect(screen_w // 2 - 180, screen_h // 2 + 200, 360, 76)

    try:
        game_manager.play_music("end.mp3", fade_ms=800, volume=0.55)
    except Exception:
        pass

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
        screen.blit(title, title.get_rect(center=(screen_w // 2, screen_h // 2 - 100)))

        line = pygame.Surface((420, 2), pygame.SRCALPHA)
        line.fill((*COLOR_GOLD, alpha))
        screen.blit(line, line.get_rect(center=(screen_w // 2, screen_h // 2 - 10)))

        sub = font_sub.render(f"{player_name}'s journey has ended.",
                              True, COLOR_WHITE)
        sub.set_alpha(alpha)
        screen.blit(sub, sub.get_rect(center=(screen_w // 2, screen_h // 2 + 40)))

        hint = font_hint.render("Thank you for playing.",
                                True, COLOR_GRAY)
        hint.set_alpha(alpha)
        screen.blit(hint, hint.get_rect(center=(screen_w // 2, screen_h // 2 + 110)))

        if now - start >= fade_ms:
            hovered = menu_btn.collidepoint(mouse_pos)
            fill = COLOR_HOVER if hovered else COLOR_PANEL
            pygame.draw.rect(screen, fill, menu_btn, border_radius=10)
            pygame.draw.rect(screen, COLOR_GOLD, menu_btn, width=3,
                             border_radius=10)
            col = COLOR_GOLD if hovered else COLOR_WHITE
            lbl = font_hint.render("RETURN TO MENU", True, col)
            screen.blit(lbl, lbl.get_rect(center=menu_btn.center))

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if now - start < fade_ms:
                continue
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if menu_btn.collidepoint(event.pos):
                    return
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_SPACE, pygame.K_RETURN,
                                 pygame.K_e, pygame.K_ESCAPE):
                    return


def run_save_select(screen):
    game_manager.play_music("default.mp3")
    wait_for_mouse_release()

    clock = pygame.time.Clock()

    screen_w, screen_h = screen.get_size()
    center_x = screen_w // 2
    center_y = screen_h // 2

    bg_path = os.path.join(PROJECT_ROOT, "asset", "main_menu", "main_menu.png")
    if os.path.exists(bg_path):
        bg_image = pygame.image.load(bg_path).convert()
        bg_image = pygame.transform.scale(bg_image, (screen_w, screen_h))
    else:
        bg_image = pygame.Surface((screen_w, screen_h))
        bg_image.fill((15, 15, 30))

    dark_overlay = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
    dark_overlay.fill((10, 10, 20, 200))

    font_path = os.path.join(PROJECT_ROOT, "asset", "font", "TheGothicRite.otf")
    if os.path.exists(font_path):
        font_title = pygame.font.Font(font_path, 38)
        font_slot = pygame.font.Font(font_path, 26)
        font_small = pygame.font.Font(font_path, 20)
        font_btn = pygame.font.Font(font_path, 18)
        font_caution = pygame.font.Font(font_path, 22)
    else:
        font_title = pygame.font.SysFont("Georgia", 38, bold=True)
        font_slot = pygame.font.SysFont("Georgia", 26, bold=True)
        font_small = pygame.font.SysFont("Georgia", 20, bold=True)
        font_btn = pygame.font.SysFont("Georgia", 18, bold=True)
        font_caution = pygame.font.SysFont("Georgia", 22, bold=True)

    COLOR_GOLD      = (255, 215, 0)
    COLOR_BORDER    = (212, 175, 55)
    COLOR_PANEL     = (28, 26, 48, 245)
    COLOR_WHITE     = (240, 235, 210)
    COLOR_GRAY      = (150, 150, 170)
    COLOR_RED       = (200, 55, 55)
    COLOR_RED_HOV   = (240, 75, 95)
    COLOR_BTN_BG    = (35, 30, 60)
    COLOR_BTN_HOV   = (60, 50, 95)

    title_panel_w, title_panel_h = 560, 90
    title_panel_rect = pygame.Rect(center_x - (title_panel_w // 2), 60, title_panel_w, title_panel_h)

    card_w, card_h = 800, 140
    card_x = center_x - (card_w // 2)

    slot_buttons = [
        Button(card_x, 240, card_w, card_h,
               font=font_slot, bg_color=COLOR_BTN_BG, hover_color=COLOR_BTN_HOV,
               text_color=COLOR_GOLD, border_color=COLOR_BORDER, border_radius=10),
        Button(card_x, 420, card_w, card_h,
               font=font_slot, bg_color=COLOR_BTN_BG, hover_color=COLOR_BTN_HOV,
               text_color=COLOR_GOLD, border_color=COLOR_BORDER, border_radius=10),
        Button(card_x, 600, card_w, card_h,
               font=font_slot, bg_color=COLOR_BTN_BG, hover_color=COLOR_BTN_HOV,
               text_color=COLOR_GOLD, border_color=COLOR_BORDER, border_radius=10),
    ]

    delete_buttons = [
        Button(card_x + card_w - 140, 240 + 45, 110, 50, text="DELETE",
               font=font_btn, bg_color=COLOR_RED, hover_color=COLOR_RED_HOV,
               text_color=COLOR_GOLD, border_color=COLOR_GOLD, border_radius=6),
        Button(card_x + card_w - 140, 420 + 45, 110, 50, text="DELETE",
               font=font_btn, bg_color=COLOR_RED, hover_color=COLOR_RED_HOV,
               text_color=COLOR_GOLD, border_color=COLOR_GOLD, border_radius=6),
        Button(card_x + card_w - 140, 600 + 45, 110, 50, text="DELETE",
               font=font_btn, bg_color=COLOR_RED, hover_color=COLOR_RED_HOV,
               text_color=COLOR_GOLD, border_color=COLOR_GOLD, border_radius=6),
    ]

    back_button = Button(80, 920, 200, 60, text="BACK",
                         font=font_slot, bg_color=COLOR_BTN_BG, hover_color=COLOR_BTN_HOV,
                         text_color=COLOR_GOLD, border_color=COLOR_BORDER, border_radius=8)

    modal_w, modal_h = 500, 240
    modal_rect = pygame.Rect(center_x - (modal_w // 2), center_y - (modal_h // 2), modal_w, modal_h)

    confirm_yes_btn = Button(center_x - 130, center_y + 35, 110, 48, text="YES",
                             font=font_btn, bg_color=COLOR_RED, hover_color=COLOR_RED_HOV,
                             text_color=COLOR_GOLD, border_color=COLOR_GOLD, border_radius=6)

    confirm_no_btn = Button(center_x + 20, center_y + 35, 110, 48, text="NO",
                            font=font_btn, bg_color=COLOR_BTN_BG, hover_color=COLOR_BTN_HOV,
                            text_color=COLOR_GOLD, border_color=COLOR_BORDER, border_radius=6)

    confirm_delete_slot = None

    tut_modal_w, tut_modal_h = 620, 280
    tut_modal_rect = pygame.Rect(
        center_x - (tut_modal_w // 2),
        center_y - (tut_modal_h // 2),
        tut_modal_w, tut_modal_h,
    )

    tutorial_yes_btn = Button(center_x - 130, center_y + 50, 110, 48, text="YES",
                              font=font_btn, bg_color=COLOR_BTN_BG, hover_color=COLOR_BTN_HOV,
                              text_color=COLOR_GOLD, border_color=COLOR_BORDER, border_radius=6)

    tutorial_no_btn = Button(center_x + 20, center_y + 50, 110, 48, text="NO",
                             font=font_btn, bg_color=COLOR_BTN_BG, hover_color=COLOR_BTN_HOV,
                             text_color=COLOR_GOLD, border_color=COLOR_BORDER, border_radius=6)

    tutorial_prompt_slot = None

    stars = [
        {"x": random.randint(0, screen_w),
         "y": random.randint(0, screen_h),
         "speed": random.uniform(0.15, 0.4),
         "size": random.randint(1, 3)}
        for _ in range(70)
    ]

    frame_count = 0
    running = True

    while running:
        clock.tick(60)
        frame_count += 1

        any_modal_open = (confirm_delete_slot is not None) or (tutorial_prompt_slot is not None)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                if confirm_delete_slot is not None:
                    confirm_delete_slot = None
                elif tutorial_prompt_slot is not None:
                    tutorial_prompt_slot = None
                else:
                    running = False

        screen.blit(bg_image, (0, 0))

        for star in stars:
            star["x"] -= star["speed"]
            if star["x"] < 0:
                star["x"] = screen_w
                star["y"] = random.randint(0, screen_h)
            alpha = int(120 + math.sin(frame_count * 0.04 + star["x"]) * 90)
            star_surf = pygame.Surface((star["size"], star["size"]), pygame.SRCALPHA)
            star_surf.fill((255, 255, 255, max(0, min(255, alpha))))
            screen.blit(star_surf, (star["x"], star["y"]))

        screen.blit(dark_overlay, (0, 0))

        title_panel_bg = pygame.Surface((title_panel_w, title_panel_h), pygame.SRCALPHA)
        title_panel_bg.fill(COLOR_PANEL)
        screen.blit(title_panel_bg, title_panel_rect.topleft)

        pygame.draw.rect(screen, COLOR_BORDER, title_panel_rect, width=3, border_radius=10)
        draw_corner_brackets(screen, title_panel_rect, COLOR_BORDER, length=24, thickness=3, offset=6)

        title_surface = font_title.render("SELECT SAVE SLOT", True, COLOR_GOLD)
        title_rect = title_surface.get_rect(center=(center_x, title_panel_rect.top + 38))
        screen.blit(title_surface, title_rect)

        line_y = title_panel_rect.bottom + 15
        pygame.draw.line(screen, COLOR_BORDER,
                         (title_panel_rect.left - 40, line_y),
                         (title_panel_rect.right + 40, line_y), 2)

        if not any_modal_open:
            if back_button.draw(screen):
                running = False
                break
        else:
            back_button.draw(screen)

        draw_corner_brackets(screen, back_button.rect, COLOR_BORDER, length=18, thickness=3, offset=5)

        for index, slot_btn in enumerate(slot_buttons):
            slot_id = index + 1
            save_data = load_save_data(slot_id)
            delete_btn = delete_buttons[index]

            if not any_modal_open:
                slot_clicked = slot_btn.draw(screen)
            else:
                slot_btn.draw(screen)
                slot_clicked = False

            draw_corner_brackets(screen, slot_btn.rect, COLOR_BORDER, length=24, thickness=3, offset=6)

            slot_header = font_slot.render(f"SLOT {slot_id}", True, COLOR_GOLD)
            screen.blit(slot_header, (slot_btn.rect.x + 35, slot_btn.rect.y + 25))

            delete_clicked = False
            if save_data:
                p_name = save_data.get("player_name", "Solaris")

                player_block = save_data.get("player", {}) or {}
                is_completed = bool(player_block.get("game_completed", False))

                label = f"Hero: {p_name}"
                if is_completed:
                    label += "   [ COMPLETED ]"

                info_surface = font_small.render(label, True, COLOR_WHITE)
                screen.blit(info_surface, (slot_btn.rect.x + 35, slot_btn.rect.y + 75))

                if not any_modal_open:
                    delete_clicked = delete_btn.draw(screen)
                else:
                    delete_btn.draw(screen)
            else:
                empty_surface = font_small.render(
                    "[ Empty Save Slot ] - Click to Start New Game",
                    True, COLOR_GRAY
                )
                screen.blit(empty_surface, (slot_btn.rect.x + 35, slot_btn.rect.y + 75))

            if delete_clicked:
                confirm_delete_slot = slot_id
                wait_for_mouse_release()
                break
            elif slot_clicked and not (save_data and delete_btn.rect.collidepoint(pygame.mouse.get_pos())):
                has_player_block = (
                    save_data is not None
                    and isinstance(save_data.get("player"), dict)
                    and len(save_data["player"]) > 0
                )

                if save_data is None or not has_player_block:
                    tutorial_prompt_slot = slot_id
                    wait_for_mouse_release()
                    break
                else:
                    player_block = save_data.get("player", {}) or {}
                    if bool(player_block.get("game_completed", False)):
                        saved_name = save_data.get("player_name", "Solaris")
                        _show_game_complete_screen(screen, saved_name)
                        wait_for_mouse_release()
                        game_manager.play_music("default.mp3", fade_ms=600)
                        break

                    saved_name = save_data.get("player_name", "Solaris")
                    existing_player = Player(x=13 * 64, y=6 * 64, name=saved_name)
                    if hasattr(existing_player, "set_name"):
                        existing_player.set_name(saved_name)

                    run_transition(screen, message="Entering Aurelia...", duration_sec=1.2)

                    result = run_gameplay_with_map_switching(
                        screen, slot_id=slot_id, player=existing_player
                    )
                    wait_for_mouse_release()

                    if result == "QUIT_TO_MENU":
                        running = False
                    break

        if confirm_delete_slot is not None:
            modal_dim = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
            modal_dim.fill((0, 0, 0, 160))
            screen.blit(modal_dim, (0, 0))

            modal_bg = pygame.Surface((modal_w, modal_h), pygame.SRCALPHA)
            modal_bg.fill((28, 26, 48, 250))
            screen.blit(modal_bg, modal_rect.topleft)

            pygame.draw.rect(screen, COLOR_RED, modal_rect, width=3, border_radius=10)
            draw_corner_brackets(screen, modal_rect, COLOR_GOLD, length=20, thickness=3, offset=5)

            caution_title = font_caution.render("CAUTION!", True, COLOR_RED)
            caution_rect = caution_title.get_rect(center=(center_x, modal_rect.top + 35))
            screen.blit(caution_title, caution_rect)

            msg_surf = font_small.render(
                f"Are you sure you want to delete Slot {confirm_delete_slot}?",
                True, COLOR_WHITE
            )
            msg_rect = msg_surf.get_rect(center=(center_x, modal_rect.top + 85))
            screen.blit(msg_surf, msg_rect)

            if confirm_yes_btn.draw(screen):
                delete_save_data(confirm_delete_slot)
                confirm_delete_slot = None
                wait_for_mouse_release()
            elif confirm_no_btn.draw(screen):
                confirm_delete_slot = None
                wait_for_mouse_release()

        if tutorial_prompt_slot is not None:
            modal_dim = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
            modal_dim.fill((0, 0, 0, 160))
            screen.blit(modal_dim, (0, 0))

            tut_bg = pygame.Surface((tut_modal_w, tut_modal_h), pygame.SRCALPHA)
            tut_bg.fill((28, 26, 48, 250))
            screen.blit(tut_bg, tut_modal_rect.topleft)

            pygame.draw.rect(screen, COLOR_BORDER, tut_modal_rect, width=3, border_radius=10)
            draw_corner_brackets(screen, tut_modal_rect, COLOR_GOLD, length=22, thickness=3, offset=5)

            tut_title = font_caution.render("TUTORIAL", True, COLOR_GOLD)
            tut_title_rect = tut_title.get_rect(center=(center_x, tut_modal_rect.top + 38))
            screen.blit(tut_title, tut_title_rect)

            pygame.draw.line(screen, COLOR_BORDER,
                             (tut_modal_rect.left + 40, tut_modal_rect.top + 68),
                             (tut_modal_rect.right - 40, tut_modal_rect.top + 68),
                             2)

            msg1 = font_small.render(
                "Would you like to see a quick tutorial",
                True, COLOR_WHITE
            )
            msg2 = font_small.render(
                "before starting your adventure?",
                True, COLOR_WHITE
            )
            screen.blit(msg1, msg1.get_rect(center=(center_x, tut_modal_rect.top + 100)))
            screen.blit(msg2, msg2.get_rect(center=(center_x, tut_modal_rect.top + 128)))

            sub = font_btn.render(
                "(Covers controls, elements, combat, and gameplay)",
                True, COLOR_GRAY
            )
            screen.blit(sub, sub.get_rect(center=(center_x, tut_modal_rect.top + 165)))

            tutorial_yes_btn.rect.y = tut_modal_rect.bottom - 70
            tutorial_no_btn.rect.y = tut_modal_rect.bottom - 70

            if tutorial_yes_btn.draw(screen):
                chosen_slot = tutorial_prompt_slot
                tutorial_prompt_slot = None
                wait_for_mouse_release()

                run_tutorial(screen)

                run_transition(screen, message="Awakening Prologue...", duration_sec=1.2)
                result = run_prologue(screen, chosen_slot)
                wait_for_mouse_release()

                if result == "QUIT_TO_MENU":
                    running = False

            elif tutorial_no_btn.draw(screen):
                chosen_slot = tutorial_prompt_slot
                tutorial_prompt_slot = None
                wait_for_mouse_release()

                run_transition(screen, message="Awakening Prologue...", duration_sec=1.2)
                result = run_prologue(screen, chosen_slot)
                wait_for_mouse_release()

                if result == "QUIT_TO_MENU":
                    running = False

        pygame.display.flip()