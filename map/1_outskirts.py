
import os
import sys
import pygame

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

from Modules.objects import DecoObject
from Modules.game_frame import GameFrame
from floor.castle import CastleFloor


CELL_SIZE = 64
MAP_COLS = 20
MAP_ROWS = 17

TOP_TREE_ROWS = []
TREE_TOP_SHIFT = 0


PLAYER_HITBOX_W = 20
PLAYER_HITBOX_H = 38
PLAYER_HITBOX_CENTER_TO_FEET = 57


MAP_GRID = [
    "MBM.MRM.S.SB.MSR.M.M",
    "SR.H.....S.....H....",
    "M........M..........",
    "...M....S..........M",
    ".S.........M...B....",
    ".M.....B............",
    "....S......S...B....",
    ".....R..S...R..G....",
    "...B..M...M.........",
    "..M..SH..........M..",
    "M...........M.......",
    ".B..R.B.B...B..R.S..",
    ".M..R.M..M....M..B..",
    "..M.......M.....M..M",
    "M.M.S.......M.......",
    "....M...............",
    "....................",
]


MOB_GRID = [
    "....................",
    "....................",
    "....................",
    ".............W......",
    "....................",
    "......L.............",
    "....................",
    "....................",
    "....................",
    "..O.........L.......",
    "....................",
    "....................",
    "....................",
    "....................",
    "....................",
    "....................",
    "....................",
]


MOB_LEGEND = {
    'W': "wizard_oz",
    'L': "slime",
    'O': "tiny_orc",
}


GRID_TO_OBJECT = {
    'M': "maple",
    'B': "maplebush",
    'R': "rock_1",
    'S': "rock_2",
    'H': "house_1",
    'G': "house_2",
}


TRANSFER_ZONES_VISIBLE = False
SPAWN_ZONES_VISIBLE    = False


TRANSFER_ZONES = {
    "to_castle": {
        "x": 1268, "y": 128, "w": 12, "h": 512,
        "color": (255, 105, 180),
        "target": "GO_TO_CASTLE",
        "label":  "TO CASTLE",
    },
    "to_mystic": {
        "x": -4, "y": 128, "w": 12, "h": 512,
        "color": (140, 220, 255),
        "target": "GO_TO_MYSTIC",
        "label":  "TO MYSTIC FOREST",
        "gate":   "horde_done",
        "gate_message": "The Mystic Forest is not yet open.",
    },
}


LOCKED_DOORS = {}


SPAWN_ZONES = {
    "default": {
        "x": 1000, "y": 320, "w": 40, "h": 60,
        "color": (255, 255, 100),
        "label": "DEFAULT SPAWN",
    },
    "castle": {
        "x": 1200, "y": 330, "w": 40, "h": 60,
        "color": (100, 255, 100),
        "label": "SPAWN FROM CASTLE",
    },
    "mystic": {
        "x": 40, "y": 330, "w": 40, "h": 60,
        "color": (140, 220, 255),
        "label": "SPAWN FROM MYSTIC",
    },
}


def zone_rect(zone_data):
    return pygame.Rect(
        zone_data["x"], zone_data["y"],
        zone_data["w"], zone_data["h"],
    )


def zone_center(zone_data):
    return (zone_data["x"] + zone_data["w"] // 2,
            zone_data["y"] + zone_data["h"] // 2)


def zone_spawn_point(zone_data):
    hx = zone_data["x"] + zone_data["w"] // 2
    hy = zone_data["y"] + zone_data["h"] // 2
    return (hx, hy + PLAYER_HITBOX_CENTER_TO_FEET)


def build_objects_from_grid():
    objects = []
    for row_index, row_string in enumerate(MAP_GRID):
        for col_index, char in enumerate(row_string):
            sprite_name = GRID_TO_OBJECT.get(char)
            if sprite_name is None:
                continue
            pixel_x = col_index * CELL_SIZE
            pixel_y = row_index * CELL_SIZE
            if row_index in TOP_TREE_ROWS:
                pixel_y += TREE_TOP_SHIFT
            objects.append(DecoObject(sprite_name, x=pixel_x, y=pixel_y))
    return objects


def get_mob_spawns():
    spawns = []
    for row_index, row_string in enumerate(MOB_GRID):
        for col_index, char in enumerate(row_string):
            mob_type = MOB_LEGEND.get(char)
            if mob_type is None:
                continue
            pixel_x = col_index * CELL_SIZE
            pixel_y = row_index * CELL_SIZE
            spawns.append((mob_type, pixel_x, pixel_y))
    return spawns


def _draw_one_zone(surface, zone_data, show_spawn_marker=False):
    rect = zone_rect(zone_data)
    color = zone_data["color"]
    overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
    overlay.fill((color[0], color[1], color[2], 60))
    surface.blit(overlay, rect.topleft)
    pygame.draw.rect(surface, color, rect, 2)
    if show_spawn_marker:
        sx, sy = zone_spawn_point(zone_data)
        pygame.draw.circle(surface, color,
                           (sx, sy - PLAYER_HITBOX_CENTER_TO_FEET), 3)


def draw_transfer_zones(surface, force_show=False):
    if not (TRANSFER_ZONES_VISIBLE or force_show):
        return
    for data in TRANSFER_ZONES.values():
        _draw_one_zone(surface, data, show_spawn_marker=False)
    for data in LOCKED_DOORS.values():
        _draw_one_zone(surface, data, show_spawn_marker=False)


def draw_spawn_zones(surface, force_show=False):
    if not (SPAWN_ZONES_VISIBLE or force_show):
        return
    for data in SPAWN_ZONES.values():
        _draw_one_zone(surface, data, show_spawn_marker=True)


def run_preview():
    pygame.init()
    screen = pygame.display.set_mode((1920, 1080))
    pygame.display.set_caption("Outskirts Preview (H to toggle zones)")
    clock = pygame.time.Clock()

    font_path = os.path.join(PROJECT_ROOT, "asset", "font", "TheGothicRite.otf")
    if os.path.exists(font_path):
        font_title = pygame.font.Font(font_path, 36)
        font_debug = pygame.font.Font(font_path, 20)
    else:
        font_title = pygame.font.SysFont("Georgia", 36)
        font_debug = pygame.font.SysFont("Georgia", 20)

    frame = GameFrame(font_large=font_title, font_small=font_debug)
    frame.title_text = "Outskirts Preview"

    castle_floor = CastleFloor(viewport_width=1280, viewport_height=720)
    if hasattr(castle_floor, "current_index"):
        castle_floor.current_index = 0

    objects = build_objects_from_grid()
    show_zones = False

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_h:
                    show_zones = not show_zones

        viewport = frame.get_viewport()
        castle_floor.draw(viewport)

        for obj in sorted(
            objects,
            key=lambda o: o.hitbox.bottom if hasattr(o, "hitbox") else o.rect.bottom,
        ):
            obj.draw(viewport)

        for mob_type, mx, my in get_mob_spawns():
            pygame.draw.circle(viewport, (255, 60, 60), (mx, my), 6)
            pygame.draw.circle(viewport, (255, 255, 255), (mx, my), 6, 1)

        draw_transfer_zones(viewport, force_show=show_zones)
        draw_spawn_zones(viewport, force_show=show_zones)

        frame.draw(screen)
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    run_preview()