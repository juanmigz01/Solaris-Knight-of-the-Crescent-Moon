
import os
import sys
import pygame

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from Modules.button import Button, draw_corner_brackets



SCENE_LIST = [
    (1, "castle",   "Castle (Spawn)"),
    (1, "village",  "Village"),
    (1, "outskirts","Outskirts"),
    (2, "mystic",   "Mystic Forest"),
    (2, "deeper",   "Deeper Forest"),
    (2, "curse",    "Cursed Grove"),
    (2, "wizardoz", "Wizard Oz's Clearing"),
    (2, "kitsune",  "Kitsune's Shrine"),
    (2, "wizard3",  "Wizard Oz's Workshop"),
    (3, "final",    "Gorgona's Throne"),
]

ZONE_HEADERS = {
    1: "ZONE 1 - AURELIA",
    2: "ZONE 2 - THE MYSTIC FOREST",
    3: "ZONE 3 - GORGONA'S DOMAIN",
}

ROWS = [
    {"type": "header",    "text": ZONE_HEADERS[1]},
    {"type": "scene",     "key": "castle",   "name": "Castle (Spawn)"},
    {"type": "connector", "text": "v"},
    {"type": "scene",     "key": "village",  "name": "Village"},
    {"type": "connector", "text": "v"},
    {"type": "scene",     "key": "outskirts","name": "Outskirts"},
    {"type": "connector", "text": "v"},
    {"type": "gap"},

    {"type": "header",    "text": ZONE_HEADERS[2]},
    {"type": "scene",     "key": "mystic",   "name": "Mystic Forest"},
    {"type": "connector", "text": "v"},
    {"type": "scene",     "key": "deeper",   "name": "Deeper Forest"},
    {"type": "connector", "text": "v"},
    {"type": "scene",     "key": "curse",    "name": "Cursed Grove"},
    {"type": "connector", "text": "v"},
    {"type": "scene",     "key": "wizardoz", "name": "Wizard Oz's Clearing"},
    {"type": "connector", "text": "v"},
    {"type": "scene",     "key": "kitsune",  "name": "Kitsune's Shrine"},
    {"type": "connector", "text": "v"},
    {"type": "scene",     "key": "wizard3",  "name": "Wizard Oz's Workshop"},
    {"type": "connector", "text": "v"},
    {"type": "gap"},

    {"type": "header",    "text": ZONE_HEADERS[3]},
    {"type": "scene",     "key": "final",    "name": "Gorgona's Throne"},
]



def get_unlocked_scenes(player):

    unlocked = {"castle"}
    if player is None:
        return unlocked

    if (getattr(player, "wizard_dialogue_state", "PART_1") == "COMPLETED"
            or getattr(player, "village_orc_reward_done", False)):
        unlocked.add("village")
    if getattr(player, "village_orc_reward_done", False):
        unlocked.add("outskirts")

    if getattr(player, "outskirts_horde_defeated", False):
        unlocked.add("mystic")
    if getattr(player, "has_seen_mystic_intro", False):
        unlocked.add("deeper")

    deeper_done = bool(getattr(player, "deeper_devils_defeated", False))
    if not deeper_done:
        dlist = getattr(player, "deeper_horde_defeated_list", None)
        if dlist:
            try:
                deeper_done = all(dlist)
            except TypeError:
                deeper_done = False
    if deeper_done:
        unlocked.add("curse")

    if getattr(player, "has_seen_curse_intro", False):
        unlocked.add("wizardoz")
    if getattr(player, "wizardoz_reward_given", False):
        unlocked.add("kitsune")
    if getattr(player, "kitsune_defeated", False):
        unlocked.add("wizard3")

    if getattr(player, "wizard3_reward_given", False):
        unlocked.add("final")

    return unlocked



def show_map(screen, player=None, current_scene=None):

    clock = pygame.time.Clock()
    screen_w, screen_h = screen.get_size()
    bg_snapshot = screen.copy()

    font_path = os.path.join(PROJECT_ROOT, "asset", "font", "TheGothicRite.otf")
    if os.path.exists(font_path):
        font_title = pygame.font.Font(font_path, 42)
        font_zone  = pygame.font.Font(font_path, 24)
        font_scene = pygame.font.Font(font_path, 22)
        font_conn  = pygame.font.Font(font_path, 20)
        font_btn   = pygame.font.Font(font_path, 20)
    else:
        font_title = pygame.font.SysFont("Georgia", 42, bold=True)
        font_zone  = pygame.font.SysFont("Georgia", 24, bold=True)
        font_scene = pygame.font.SysFont("Georgia", 22, bold=True)
        font_conn  = pygame.font.SysFont("Georgia", 20, bold=True)
        font_btn   = pygame.font.SysFont("Georgia", 20, bold=True)

    COLOR_PANEL     = (28, 26, 48, 245)
    COLOR_BORDER    = (212, 175, 55)
    COLOR_GOLD      = (255, 215, 0)
    COLOR_BRIGHT    = (255, 235, 130)
    COLOR_TEXT      = (240, 235, 210)
    COLOR_LOCKED    = (110, 110, 125)
    COLOR_LOCKED_BD = (70, 70, 85)
    COLOR_BTN_BG    = (35, 30, 60)
    COLOR_BTN_HOV   = (60, 50, 95)

    if current_scene is None and player is not None:
        current_scene = getattr(player, "last_scene", "castle")
    if not current_scene:
        current_scene = "castle"

    current_display = "Unknown"
    for _, key, name in SCENE_LIST:
        if key == current_scene:
            current_display = name
            break

    unlocked = get_unlocked_scenes(player)
    unlocked.add(current_scene)  

    panel_w, panel_h = 900, 1000
    panel_rect = pygame.Rect(
        screen_w // 2 - panel_w // 2,
        screen_h // 2 - panel_h // 2,
        panel_w, panel_h,
    )

    close_btn = Button(
        panel_rect.centerx - 140,
        panel_rect.bottom - 68,
        280, 50,
        text="CLOSE [M]",
        font=font_btn,
        bg_color=COLOR_BTN_BG,
        hover_color=COLOR_BTN_HOV,
        text_color=COLOR_GOLD,
        border_color=COLOR_BORDER,
        border_radius=8,
    )

    while True:
        clock.tick(60)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_m, pygame.K_ESCAPE,
                                 pygame.K_RETURN, pygame.K_SPACE):
                    return
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if close_btn.rect.collidepoint(event.pos):
                    return

        screen.blit(bg_snapshot, (0, 0))
        dim = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 205))
        screen.blit(dim, (0, 0))

        panel_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel_surf.fill(COLOR_PANEL)
        screen.blit(panel_surf, panel_rect.topleft)
        pygame.draw.rect(screen, COLOR_BORDER, panel_rect,
                         width=3, border_radius=12)
        draw_corner_brackets(screen, panel_rect, COLOR_BORDER,
                             length=26, thickness=3, offset=8)

        title = font_title.render("WORLD MAP", True, COLOR_GOLD)
        screen.blit(title, title.get_rect(
            center=(panel_rect.centerx, panel_rect.top + 40)))

        loc_str = f"Current Location:  {current_display}"
        loc_surf = font_zone.render(loc_str, True, COLOR_BRIGHT)
        screen.blit(loc_surf, loc_surf.get_rect(
            center=(panel_rect.centerx, panel_rect.top + 82)))

        pygame.draw.line(screen, COLOR_BORDER,
                         (panel_rect.left + 60, panel_rect.top + 112),
                         (panel_rect.right - 60, panel_rect.top + 112),
                         2)

        content_y = panel_rect.top + 130
        content_x = panel_rect.left + 130

        for row in ROWS:
            rtype = row["type"]

            if rtype == "gap":
                content_y += 14
                continue

            if rtype == "header":
                txt = font_zone.render(row["text"], True, COLOR_BORDER)
                screen.blit(txt, (content_x, content_y))
                content_y += 32
                continue

            if rtype == "connector":
                surf = font_conn.render(row.get("text", "v"),
                                        True, COLOR_BORDER)
                screen.blit(surf, (content_x + 22, content_y))
                content_y += 22
                continue

            if rtype == "scene":
                key  = row["key"]
                name = row["name"]

                is_current  = (key == current_scene)
                is_unlocked = key in unlocked

                if is_current:
                    bd     = COLOR_GOLD
                    tc     = COLOR_BRIGHT
                    prefix = ">> "
                    suffix = "   <-- YOU ARE HERE"
                elif is_unlocked:
                    bd     = COLOR_BORDER
                    tc     = COLOR_TEXT
                    prefix = "   "
                    suffix = ""
                else:
                    bd     = COLOR_LOCKED_BD
                    tc     = COLOR_LOCKED
                    prefix = "   "
                    suffix = "   [ LOCKED ]"

                chip_label = f"{prefix}[ {name} ]"
                chip_surf  = font_scene.render(chip_label, True, tc)

                pad_x, pad_y = 14, 7
                chip_w = chip_surf.get_width()  + pad_x * 2
                chip_h = chip_surf.get_height() + pad_y * 2
                chip_rect = pygame.Rect(content_x, content_y, chip_w, chip_h)

                chip_bg = pygame.Surface((chip_w, chip_h), pygame.SRCALPHA)
                chip_bg.fill((18, 16, 30, 220))
                screen.blit(chip_bg, chip_rect.topleft)
                pygame.draw.rect(screen, bd, chip_rect,
                                 width=2, border_radius=6)
                screen.blit(chip_surf,
                            (chip_rect.x + pad_x, chip_rect.y + pad_y))

                if suffix:
                    sc = COLOR_BRIGHT if is_current else COLOR_LOCKED
                    suf_surf = font_scene.render(suffix, True, sc)
                    screen.blit(suf_surf,
                                (chip_rect.right + 12,
                                 chip_rect.y + pad_y + 2))

                content_y += chip_h + 2
                continue

        close_btn.draw(screen)

        pygame.display.flip()