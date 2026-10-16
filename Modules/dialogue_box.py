import os
import sys
import pygame

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from Modules.button import draw_corner_brackets

try:
    from Modules.sound_manager import game_manager
except ImportError:
    game_manager = None


COLOR_PANEL  = (28, 26, 48)
COLOR_BORDER = (212, 175, 55)
COLOR_GOLD   = (255, 215, 0)
COLOR_WHITE  = (240, 235, 210)
COLOR_CYAN   = (140, 200, 255)
COLOR_GRAY   = (150, 150, 170)
COLOR_CHOICE_BG    = (35, 30, 60)
COLOR_CHOICE_HOVER = (60, 50, 95)


VP_X, VP_Y, VP_W, VP_H = 320, 180, 1280, 720

BOX_W = 1240
BOX_H = 200
BOX_BOTTOM_MARGIN = 20

FONT_SPEAKER_SIZE = 28
FONT_TEXT_SIZE    = 22
FONT_HINT_SIZE    = 17
FONT_CHOICE_SIZE  = 22

LINE_HEIGHT = 28



def _font(path, size):
    if os.path.exists(path):
        return pygame.font.Font(path, size)
    return pygame.font.SysFont("Georgia", size, bold=True)


def _stop_walk_run_loops():
    if game_manager is None:
        return
    try:
        game_manager.stop_sfx("walk")
        game_manager.stop_sfx("run")
    except Exception:
        pass


def run_dialogue(screen, dialogue_list, bg_snapshot):

    _stop_walk_run_loops()

    clock = pygame.time.Clock()

    FONT_PATH = os.path.join(PROJECT_ROOT, "asset", "font",
                             "TheGothicRite.otf")
    font_speaker = _font(FONT_PATH, FONT_SPEAKER_SIZE)
    font_text    = _font(FONT_PATH, FONT_TEXT_SIZE)
    font_hint    = _font(FONT_PATH, FONT_HINT_SIZE)
    font_choice  = _font(FONT_PATH, FONT_CHOICE_SIZE)

    box_x = VP_X + (VP_W - BOX_W) // 2
    box_y = VP_Y + VP_H - BOX_H - BOX_BOTTOM_MARGIN
    panel_rect = pygame.Rect(box_x, box_y, BOX_W, BOX_H)

    overlay = pygame.Surface((VP_W, VP_H), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 130))

    idx = 0
    while idx < len(dialogue_list):
        clock.tick(60)
        line = dialogue_list[idx]
        speaker = line.get("speaker", "???")
        text = line.get("text", "")
        choices = line.get("choices")

        mouse_pos = pygame.mouse.get_pos()

        screen.blit(bg_snapshot, (0, 0))
        screen.blit(overlay, (VP_X, VP_Y))

        pygame.draw.rect(screen, COLOR_PANEL, panel_rect, border_radius=8)
        pygame.draw.rect(screen, COLOR_BORDER, panel_rect,
                         width=2, border_radius=8)
        draw_corner_brackets(screen, panel_rect, COLOR_BORDER,
                             length=22, thickness=3, offset=5)

        speaker_color = (COLOR_CYAN
                         if speaker.upper() in ("NARRATOR", "SYSTEM")
                         else COLOR_GOLD)
        speaker_surf = font_speaker.render(speaker, True, speaker_color)
        screen.blit(speaker_surf, (box_x + 24, box_y + 16))

        pygame.draw.line(screen, COLOR_BORDER,
                         (box_x + 24, box_y + 50),
                         (box_x + BOX_W - 24, box_y + 50),
                         1)

        text_top = box_y + 62
        for i, sub_l in enumerate(text.split("\n")):
            text_surf = font_text.render(sub_l, True, COLOR_WHITE)
            screen.blit(text_surf, (box_x + 24, text_top + i * LINE_HEIGHT))

        if not choices:
            hint_surf = font_hint.render("[Press E or Click to Continue]",
                                         True, COLOR_GRAY)
            hint_rect = hint_surf.get_rect(
                bottomright=(box_x + BOX_W - 20, box_y + BOX_H - 12))
            screen.blit(hint_surf, hint_rect)

        if choices:
            num_choices = len(choices)
            choice_h = 38
            choice_gap = 8
            choices_total_h = num_choices * choice_h + (num_choices - 1) * choice_gap

            choices_top = box_y + BOX_H - choices_total_h - 16
            choice_rects = []
            for i, ch in enumerate(choices):
                r = pygame.Rect(
                    box_x + 40,
                    choices_top + i * (choice_h + choice_gap),
                    BOX_W - 80,
                    choice_h,
                )
                choice_rects.append((r, ch))

            for r, ch in choice_rects:
                hovered = r.collidepoint(mouse_pos)
                fill = COLOR_CHOICE_HOVER if hovered else COLOR_CHOICE_BG
                pygame.draw.rect(screen, fill, r, border_radius=6)
                pygame.draw.rect(screen, COLOR_BORDER, r,
                                 width=2, border_radius=6)
                label = f"{choice_rects.index((r, ch)) + 1}. {ch['label']}"
                label_color = COLOR_GOLD if hovered else COLOR_WHITE
                lsurf = font_choice.render(label, True, label_color)
                screen.blit(lsurf, (r.x + 16, r.y + (r.h - lsurf.get_height()) // 2))

            pygame.display.flip()

            chosen = None
            while chosen is None:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        sys.exit()
                    elif event.type == pygame.KEYDOWN:
                        if pygame.K_1 <= event.key <= pygame.K_9:
                            n = event.key - pygame.K_1
                            if 0 <= n < len(choice_rects):
                                chosen = choice_rects[n][1]
                    elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        for r, ch in choice_rects:
                            if r.collidepoint(event.pos):
                                chosen = ch
                                break

                if chosen is None:
                    mouse_pos = pygame.mouse.get_pos()
                    for r, ch in choice_rects:
                        hovered = r.collidepoint(mouse_pos)
                        fill = COLOR_CHOICE_HOVER if hovered else COLOR_CHOICE_BG
                        pygame.draw.rect(screen, fill, r, border_radius=6)
                        pygame.draw.rect(screen, COLOR_BORDER, r,
                                         width=2, border_radius=6)
                        label = f"{choice_rects.index((r, ch)) + 1}. {ch['label']}"
                        label_color = COLOR_GOLD if hovered else COLOR_WHITE
                        lsurf = font_choice.render(label, True, label_color)
                        screen.blit(lsurf, (r.x + 16,
                                            r.y + (r.h - lsurf.get_height()) // 2))
                    pygame.display.flip()
                    clock.tick(60)

            return ("CHOICE", chosen.get("key", ""))

        pygame.display.flip()

        advanced = False
        while not advanced:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_e, pygame.K_SPACE, pygame.K_RETURN):
                        advanced = True
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    advanced = True
            clock.tick(60)

        idx += 1

    pygame.time.wait(150)
    pygame.event.clear()
    return None