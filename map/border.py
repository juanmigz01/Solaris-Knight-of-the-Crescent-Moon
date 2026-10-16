
import os
import sys
import pygame

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

from Modules.game_frame import GameFrame
from floor.castle import CastleFloor


VISIBLE = False
BORDER_COLOR = (255, 0, 200)
VIEW_W = 1280
VIEW_H = 720

WALL_THICK = 12


DOOR_GAP_TOP    = 128
DOOR_GAP_BOTTOM = 640


top_x = 0
top_y = -2
top_w = VIEW_W
top_h = WALL_THICK


bottom_x = 0
bottom_y = VIEW_H - WALL_THICK
bottom_w = VIEW_W
bottom_h = WALL_THICK


left_top_x = 0
left_top_y = -5
left_top_w = WALL_THICK
left_top_h = DOOR_GAP_TOP - left_top_y

left_bot_x = 0
left_bot_y = DOOR_GAP_BOTTOM
left_bot_w = WALL_THICK
left_bot_h = VIEW_H - DOOR_GAP_BOTTOM + 5


right_top_x = VIEW_W - WALL_THICK
right_top_y = -5
right_top_w = WALL_THICK
right_top_h = DOOR_GAP_TOP - right_top_y

right_bot_x = VIEW_W - WALL_THICK
right_bot_y = DOOR_GAP_BOTTOM
right_bot_w = WALL_THICK
right_bot_h = VIEW_H - DOOR_GAP_BOTTOM + 5


BORDER_WALLS = [
    pygame.Rect(top_x,       top_y,       top_w,       top_h),
    pygame.Rect(bottom_x,    bottom_y,    bottom_w,    bottom_h),
    pygame.Rect(left_top_x,  left_top_y,  left_top_w,  left_top_h),
    pygame.Rect(left_bot_x,  left_bot_y,  left_bot_w,  left_bot_h),
    pygame.Rect(right_top_x, right_top_y, right_top_w, right_top_h),
    pygame.Rect(right_bot_x, right_bot_y, right_bot_w, right_bot_h),
]


def draw_borders(surface):
    if not VISIBLE:
        return

    for wall_rect in BORDER_WALLS:
        overlay = pygame.Surface(wall_rect.size, pygame.SRCALPHA)
        overlay.fill((BORDER_COLOR[0], BORDER_COLOR[1], BORDER_COLOR[2], 60))
        surface.blit(overlay, wall_rect.topleft)
        pygame.draw.rect(surface, BORDER_COLOR, wall_rect, 2)


def run_preview():
    pygame.init()

    screen = pygame.display.set_mode((1920, 1080))
    pygame.display.set_caption("Border Preview - press H to toggle, ESC to close")
    clock = pygame.time.Clock()

    font_path = os.path.join(PROJECT_ROOT, "asset", "font", "TheGothicRite.otf")
    if os.path.exists(font_path):
        font_title = pygame.font.Font(font_path, 36)
        font_debug = pygame.font.Font(font_path, 20)
    else:
        font_title = pygame.font.SysFont("Georgia", 36)
        font_debug = pygame.font.SysFont("Georgia", 20)

    frame = GameFrame(font_large=font_title, font_small=font_debug)
    frame.title_text = "Border Preview"

    castle_floor = CastleFloor(viewport_width=VIEW_W, viewport_height=VIEW_H)
    if hasattr(castle_floor, "current_index"):
        castle_floor.current_index = 0

    show = VISIBLE

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_h:
                    show = not show

        viewport = frame.get_viewport()
        castle_floor.draw(viewport)

        for x in range(0, VIEW_W + 1, 64):
            pygame.draw.line(viewport, (60, 120, 70), (x, 0), (x, VIEW_H), 1)
        for y in range(0, VIEW_H + 1, 64):
            pygame.draw.line(viewport, (60, 120, 70), (0, y), (VIEW_W, y), 1)

        if show:
            for wall_rect in BORDER_WALLS:
                overlay = pygame.Surface(wall_rect.size, pygame.SRCALPHA)
                overlay.fill((BORDER_COLOR[0], BORDER_COLOR[1], BORDER_COLOR[2], 60))
                viewport.blit(overlay, wall_rect.topleft)
                pygame.draw.rect(viewport, BORDER_COLOR, wall_rect, 2)

        frame.draw(screen)
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    run_preview()