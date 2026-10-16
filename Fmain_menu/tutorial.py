import math
import os
import random
import sys
import pygame

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from Modules.sound_manager import game_manager
from Modules.button import Button, draw_corner_brackets


OUTLINE_OFFSETS = [
    (-2, 0), (2, 0), (0, -2), (0, 2),
    (-1, -1), (1, -1), (-1, 1), (1, 1),
]


def draw_outlined_text(surface, text, font, text_color,
                       pos=None, center=None,
                       outline_color=(0, 0, 0), thickness_offsets=None):
    if thickness_offsets is None:
        thickness_offsets = OUTLINE_OFFSETS

    text_surf = font.render(text, True, text_color)

    if center is not None:
        rect = text_surf.get_rect(center=center)
    else:
        rect = text_surf.get_rect(topleft=(pos[0], pos[1]))

    outline_surf = font.render(text, True, outline_color)
    for dx, dy in thickness_offsets:
        surface.blit(outline_surf, (rect.x + dx, rect.y + dy))

    surface.blit(text_surf, rect)
    return rect


TUTORIAL_PAGES = [
    {
        "title": "1. MOVEMENT & CONTROLS",
        "content": [
            ("header", "MOVE"),
            ("body",   "W A S D   or   Arrow Keys   -   walk around"),
            ("body",   "SHIFT   -   sprint"),
            ("gap",    ""),
            ("header", "INTERACT"),
            ("body",   "E         -   talk, open chests, enter doors"),
            ("body",   "CLICK     -   use menus and buttons"),
            ("gap",    ""),
            ("header", "QUICK KEYS"),
            ("body",   "ESC       -   pause menu"),
            ("body",   "Z         -   cycle zoom"),
            ("body",   "C         -   character stats"),
            ("body",   "M         -   world map"),
        ],
    },
    {
        "title": "2. THE ELEMENTAL WHEEL",
        "content": [
            ("header", "FOUR ELEMENTS"),
            ("body",   "FIRE       WIND       EARTH       WATER"),
            ("gap",    ""),
            ("header", "THE WHEEL"),
            ("body",   "FIRE  >  WIND  >  EARTH  >  WATER  >  FIRE"),
            ("body",   "Each element beats the one to its right."),
            ("gap",    ""),
            ("header", "DAMAGE MULTIPLIERS"),
            ("body",   "STRONG    -   1.5x damage"),
            ("body",   "WEAK      -   0.5x damage"),
            ("body",   "NEUTRAL   -   1.0x damage"),
            ("gap",    ""),
            ("header", "PHYSICAL ATTACKS"),
            ("body",   "Neutral weapons always deal 1.0x."),
        ],
    },
    {
        "title": "3. BATTLE BASICS",
        "content": [
            ("header", "HOW A FIGHT STARTS"),
            ("body",   "'THE BATTLE BEGINS!' flashes, then you fight."),
            ("body",   "Walk close to an enemy to trigger it."),
            ("gap",    ""),
            ("header", "TURN ORDER"),
            ("body",   "You act, then your foe acts. Repeat."),
            ("gap",    ""),
            ("header", "YOUR ACTIONS"),
            ("body",   "ATTACK   -   hit one enemy.  Unlimited uses."),
            ("body",   "ELEM     -   hits all.  Half dmg.  10 uses."),
            ("body",   "BURST    -   hits all.  Full dmg.  5 uses."),
            ("body",   "RUN      -   leave. Enemies regen to FULL HP."),
            ("gap",    ""),
            ("header", "DUAL-WIELD"),
            ("body",   "MAIN weapon (blue)  -  full damage + element"),
            ("body",   "OFF-HAND    (red)   -  passive effects only"),
        ],
    },
    {
        "title": "4. STATUS EFFECTS",
        "content": [
            ("header", "WHAT THEY ARE"),
            ("body",   "Weapons and enemy skills can apply a status."),
            ("body",   "Most tick damage at the end of every round."),
            ("gap",    ""),
            ("header", "THE SEVEN STATUSES"),
            ("body",   "BURN       B   orange      1 dmg per stack"),
            ("body",   "BLEED      L   crimson     3% current HP / turn"),
            ("body",   "POISON     P   purple      0.5% max HP per stack"),
            ("body",   "BLUE FLAME F   ice blue    1% max HP per stack"),
            ("body",   "WEAK       W   blue-gray   -5 out dmg / stack"),
            ("body",   "STUN       S   cyan        skips a turn"),
            ("body",   "HEALING    H   green       +2% missing HP / stack"),
            ("gap",    ""),
            ("header", "PROC CHANCES"),
            ("body",   "MAIN hand    : 55% roll per hit."),
            ("body",   "OFF-HAND     : 60% roll per hit."),
            ("body",   "Enemy skills : 70% roll per hit."),
            ("body",   "PLAIN ATTACK : Bleed + Stun can proc."),
            ("gap",    ""),
            ("header", "STACKS & DURATION"),
            ("body",   "Most lose ONE stack per turn (Stun doesn't)."),
            ("body",   "Max Burn 5 / Bleed 3 / Poison 5 /"),
            ("body",   "Blue 5 / Weak 5 / Stun 2 / Healing 3."),
        ],
    },
    {
        "title": "5. EXPLORING AURELIA",
        "content": [
            ("header", "THE HUD"),
            ("body",   "LEFT   -   pause button + active quests"),
            ("body",   "RIGHT  -   equipment + inventory slots"),
            ("gap",    ""),
            ("header", "INVENTORY"),
            ("body",   "45 slots, 15 per page. Click an item to"),
            ("body",   "equip, use, or drop it."),
            ("gap",    ""),
            ("header", "CHESTS"),
            ("body",   "Walk up, press E. Every chest gives 2"),
            ("body",   "potions + 1 random armor or ring."),
            ("gap",    ""),
            ("header", "SAVING"),
            ("body",   "Press ESC, choose SAVE GAME."),
            ("body",   "Saving heals you and all alive enemies."),
        ],
    },
]


def run_tutorial(screen):

    game_manager.play_music("default.mp3")

    clock = pygame.time.Clock()
    running = True

    screen_w, screen_h = screen.get_size()

    COLOR_PANEL        = (28, 26, 48)
    COLOR_BORDER       = (212, 175, 55)
    COLOR_GOLD         = (255, 215, 0)
    COLOR_TEXT         = (245, 240, 220)
    COLOR_TEXT_GRAY    = (170, 170, 190)
    COLOR_BTN_BG       = (35, 30, 60)
    COLOR_BTN_HOV      = (60, 50, 95)
    COLOR_OUTLINE      = (0, 0, 0)

    bg_path = os.path.join(PROJECT_ROOT, "asset", "main_menu", "main_menu.png")
    if os.path.exists(bg_path):
        bg_image = pygame.image.load(bg_path).convert()
        bg_image = pygame.transform.scale(bg_image, (screen_w, screen_h))
    else:
        bg_image = pygame.Surface((screen_w, screen_h))
        bg_image.fill((15, 15, 30))

    dark_overlay = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
    dark_overlay.fill((10, 10, 20, 200))

    FONT_PATH = os.path.join(PROJECT_ROOT, "asset", "font", "TheGothicRite.otf")
    try:
        font_title  = pygame.font.Font(FONT_PATH, 44)
        font_tab    = pygame.font.Font(FONT_PATH, 24)
        font_header = pygame.font.Font(FONT_PATH, 22)
        font_body   = pygame.font.Font(FONT_PATH, 20)
        font_small  = pygame.font.Font(FONT_PATH, 18)
    except FileNotFoundError:
        font_title  = pygame.font.SysFont("Georgia", 44, bold=True)
        font_tab    = pygame.font.SysFont("Georgia", 24, bold=True)
        font_header = pygame.font.SysFont("Georgia", 22, bold=True)
        font_body   = pygame.font.SysFont("Georgia", 20)
        font_small  = pygame.font.SysFont("Georgia", 18)

    panel_w, panel_h = 1300, 920
    container_rect = pygame.Rect(
        screen_w // 2 - panel_w // 2,
        screen_h // 2 - panel_h // 2,
        panel_w, panel_h,
    )

    title_center = (screen_w // 2, container_rect.top + 45)

    panel_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
    panel_surf.fill((*COLOR_PANEL, 245))

    content_top  = container_rect.top + 130
    content_left = container_rect.left + 70

    HEADER_STEP = 30
    BODY_STEP   = 24
    GAP_STEP    = 6

    btn_w, btn_h = 180, 42
    btn_y = container_rect.bottom - 76
    text_bottom_limit = btn_y - 20

    prev_btn = Button(
        container_rect.left + 80, btn_y, btn_w, btn_h,
        text="< PREV", font=font_tab,
        bg_color=COLOR_BTN_BG, hover_color=COLOR_BTN_HOV,
        text_color=COLOR_GOLD, border_color=COLOR_BORDER,
        border_radius=8,
    )
    next_btn = Button(
        container_rect.right - 80 - btn_w, btn_y, btn_w, btn_h,
        text="NEXT >", font=font_tab,
        bg_color=COLOR_BTN_BG, hover_color=COLOR_BTN_HOV,
        text_color=COLOR_GOLD, border_color=COLOR_BORDER,
        border_radius=8,
    )
    skip_btn = Button(
        container_rect.right - 200, container_rect.top + 30, 170, 38,
        text="SKIP >", font=font_small,
        bg_color=COLOR_BTN_BG, hover_color=COLOR_BTN_HOV,
        text_color=COLOR_GOLD, border_color=COLOR_BORDER,
        border_radius=8,
    )

    page_indicator_y = btn_y + btn_h // 2

    current_page = 0
    total_pages = len(TUTORIAL_PAGES)

    stars = [
        {
            "x": random.randint(0, screen_w),
            "y": random.randint(0, screen_h),
            "speed": random.uniform(0.15, 0.4),
            "size": random.randint(1, 3),
        }
        for _ in range(70)
    ]
    frame_count = 0

    def draw_page_content(surface, page):
        draw_outlined_text(surface, page["title"], font_title, COLOR_GOLD,
                           center=(screen_w // 2, content_top + 40),
                           outline_color=COLOR_OUTLINE)

        pygame.draw.line(surface, COLOR_BORDER,
                         (container_rect.left + 120, content_top + 75),
                         (container_rect.right - 120, content_top + 75),
                         2)

        y = content_top + 100
        for kind, text in page["content"]:
            if kind == "gap":
                y += GAP_STEP
                continue

            step = HEADER_STEP if kind == "header" else BODY_STEP

            if y + step > text_bottom_limit:
                break

            if kind == "header":
                draw_outlined_text(surface, text, font_header, COLOR_GOLD,
                                   pos=(content_left, y),
                                   outline_color=COLOR_OUTLINE)
            else:
                draw_outlined_text(surface, text, font_body, COLOR_TEXT,
                                   pos=(content_left + 20, y),
                                   outline_color=COLOR_OUTLINE)
            y += step

    def _finalize():
        nonlocal running
        running = False

    while running:
        clock.tick(60)
        frame_count += 1
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    _finalize()
                elif event.key == pygame.K_LEFT:
                    current_page = max(0, current_page - 1)
                elif event.key == pygame.K_RIGHT:
                    if current_page < total_pages - 1:
                        current_page += 1
                    else:
                        _finalize()
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    if current_page < total_pages - 1:
                        current_page += 1
                    else:
                        _finalize()

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if skip_btn.rect.collidepoint(mouse_pos):
                    _finalize()
                elif prev_btn.rect.collidepoint(mouse_pos):
                    current_page = max(0, current_page - 1)
                elif next_btn.rect.collidepoint(mouse_pos):
                    if current_page < total_pages - 1:
                        current_page += 1
                    else:
                        _finalize()

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

        screen.blit(panel_surf, container_rect.topleft)
        pygame.draw.rect(screen, COLOR_BORDER, container_rect, width=3, border_radius=12)
        draw_corner_brackets(screen, container_rect, COLOR_BORDER,
                             length=28, thickness=3, offset=8)

        draw_outlined_text(screen, "TUTORIAL", font_title, COLOR_GOLD,
                           center=title_center, outline_color=COLOR_OUTLINE)

        pygame.draw.line(screen, COLOR_BORDER,
                         (container_rect.left + 70, container_rect.top + 80),
                         (container_rect.right - 70, container_rect.top + 80),
                         2)

        draw_page_content(screen, TUTORIAL_PAGES[current_page])

        draw_outlined_text(screen,
                           f"Page {current_page + 1} / {total_pages}",
                           font_small, COLOR_TEXT_GRAY,
                           center=(screen_w // 2, page_indicator_y),
                           outline_color=COLOR_OUTLINE)

        try: skip_btn.update(mouse_pos)
        except TypeError: skip_btn.update()
        try: skip_btn.draw(screen, mouse_pos)
        except TypeError: skip_btn.draw(screen)

        if current_page > 0:
            try: prev_btn.update(mouse_pos)
            except TypeError: prev_btn.update()
            try: prev_btn.draw(screen, mouse_pos)
            except TypeError: prev_btn.draw(screen)

        next_btn.text = "FINISH >" if current_page == total_pages - 1 else "NEXT >"
        try: next_btn.update(mouse_pos)
        except TypeError: next_btn.update()
        try: next_btn.draw(screen, mouse_pos)
        except TypeError: next_btn.draw(screen)

        draw_outlined_text(screen,
                           "[Press ESC to Skip | LEFT / RIGHT or PREV / NEXT to Page]",
                           font_small, COLOR_TEXT_GRAY,
                           center=(screen_w // 2, container_rect.bottom - 24),
                           outline_color=COLOR_OUTLINE)

        pygame.display.flip()

    return "DONE"