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


def run_about(screen):

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
    COLOR_TAB_INACT    = (22, 22, 40)
    COLOR_TAB_INACT_BD = (90, 75, 45)
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
        font_name   = pygame.font.Font(FONT_PATH, 26)
    except FileNotFoundError:
        font_title  = pygame.font.SysFont("Georgia", 44, bold=True)
        font_tab    = pygame.font.SysFont("Georgia", 24, bold=True)
        font_header = pygame.font.SysFont("Georgia", 22, bold=True)
        font_body   = pygame.font.SysFont("Georgia", 20)
        font_small  = pygame.font.SysFont("Georgia", 18)
        font_name   = pygame.font.SysFont("Georgia", 26)

    panel_w, panel_h = 1300, 920
    container_rect = pygame.Rect(
        screen_w // 2 - panel_w // 2,
        screen_h // 2 - panel_h // 2,
        panel_w, panel_h,
    )

    tab_w, tab_h = 380, 46
    tab_gap_x = 40
    tab_gap_y = 12
    tabs_row1_y = container_rect.top + 100
    tabs_row2_y = tabs_row1_y + tab_h + tab_gap_y

    row_w = (tab_w * 2) + tab_gap_x
    tabs_x = container_rect.left + (panel_w - row_w) // 2

    credits_tab_rect   = pygame.Rect(tabs_x,                        tabs_row1_y, tab_w, tab_h)
    creators_tab_rect  = pygame.Rect(tabs_x + tab_w + tab_gap_x,    tabs_row1_y, tab_w, tab_h)
    story_tab_rect     = pygame.Rect(tabs_x,                        tabs_row2_y, tab_w, tab_h)
    tutorial_tab_rect  = pygame.Rect(tabs_x + tab_w + tab_gap_x,    tabs_row2_y, tab_w, tab_h)

    title_center = (screen_w // 2, container_rect.top + 45)
    hint_center  = (screen_w // 2, container_rect.bottom - 24)

    panel_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
    panel_surf.fill((*COLOR_PANEL, 245))

    content_top  = tabs_row2_y + tab_h + 16
    content_left = container_rect.left + 70

    HEADER_STEP = 30
    BODY_STEP   = 24
    GAP_STEP    = 6

    btn_w, btn_h = 180, 42
    btn_y = container_rect.bottom - 76

    text_bottom_limit = btn_y - 20

    story_pages = [
        {
            "title": "THE KINGDOM OF AURELIA",
            "content": [
                ("header", "A LAND OF PEACE"),
                ("body",   "For generations, the Kingdom of Aurelia stood"),
                ("body",   "as a land of peace and beauty. Golden towers"),
                ("body",   "rose above the mist, and gardens spilled with"),
                ("body",   "flowers long into the warm nights."),
                ("gap",    ""),
                ("header", "THE CASTLE"),
                ("body",   "At the heart of Aurelia sits its castle. King"),
                ("body",   "Sethos rules from its throne room, and his"),
                ("body",   "only daughter, Princess Lunaire, walks its"),
                ("body",   "halls. The kingdom has known peace for a very"),
                ("body",   "long time."),
            ],
        },
        {
            "title": "SOLARIS & LUNAIRE",
            "content": [
                ("header", "THE GIRL IN THE GARDEN"),
                ("body",   "Lunaire was the only daughter of the royal"),
                ("body",   "family. Despite the servants and tutors"),
                ("body",   "around her, she was often alone."),
                ("gap",    ""),
                ("header", "THE BOY WHO DIDN'T BOW"),
                ("body",   "They met when they were seven. Solaris"),
                ("body",   "wandered into the gardens during one of his"),
                ("body",   "father's visits. He didn't bow. He didn't call"),
                ("body",   "her 'Your Highness.' He simply asked why she"),
                ("body",   "was sitting by herself."),
                ("gap",    ""),
                ("header", "A PROMISE"),
                ("body",   "From that day they were inseparable. Before"),
                ("body",   "Solaris left for training, Lunaire pressed a"),
                ("body",   "small silver crescent pendant into his hand."),
                ("body",   "'So you'll always know where to return,' she"),
                ("body",   "told him. He smiled. 'And I'll always come"),
                ("body",   "back.'"),
            ],
        },
        {
            "title": "THE NIGHT THE MOON WENT DARK",
            "content": [
                ("header", "THE SHADOW"),
                ("body",   "Gorgona, the Vain Empress, was an ancient"),
                ("body",   "serpent sorceress consumed by one obsession:"),
                ("body",   "beauty that would never fade."),
                ("gap",    ""),
                ("header", "THE RAID"),
                ("body",   "When she learned of Lunaire's grace, that"),
                ("body",   "obsession found its target. In a single"),
                ("body",   "midnight raid, Gorgona slipped past the"),
                ("body",   "castle's defenses and took the princess."),
                ("gap",    ""),
                ("header", "THE MORNING AFTER"),
                ("body",   "By morning, Lunaire was gone. The whole"),
                ("body",   "kingdom woke to the news."),
            ],
        },
        {
            "title": "THE OATH RENEWED",
            "content": [
                ("header", "THE KING"),
                ("body",   "King Sethos remained in his throne room -"),
                ("body",   "safe, but frantic, hollowed by worry for his"),
                ("body",   "daughter."),
                ("gap",    ""),
                ("header", "THE KNIGHT"),
                ("body",   "Solaris - now a fully trained knight -"),
                ("body",   "stepped forward. He touched the crescent"),
                ("body",   "pendant at his chest and remembered the"),
                ("body",   "promise he'd made as a boy."),
                ("gap",    ""),
                ("header", "I'LL ALWAYS COME BACK."),
                ("body",   "Now it was time to keep it."),
            ],
        },
    ]

    tutorial_pages = [
        {
            "title": "1. MOVEMENT & CONTROLS",
            "content": [
                ("header", "MOVEMENT"),
                ("body",   "W A S D  or  Arrow Keys   :   Walk"),
                ("body",   "SHIFT                     :   Sprint"),
                ("gap",    ""),
                ("header", "INTERACTION"),
                ("body",   "E                         :   Talk to NPCs,"),
                ("body",   "                               open doors, chests"),
                ("body",   "Left Mouse Button         :   Menus & UI"),
                ("gap",    ""),
                ("header", "GAME HOTKEYS"),
                ("body",   "ESC                       :   Pause menu"),
                ("body",   "Z                         :   Cycle zoom"),
                ("body",   "M                         :   World map"),
                ("body",   "TAB                       :   Switch About tabs"),
                ("body",   "LEFT / RIGHT (arrows)     :   Change page"),
                ("gap",    ""),
                ("header", "SETTINGS-ONLY TOGGLES"),
                ("body",   "Hitboxes, zone outlines, and particles are"),
                ("body",   "adjusted in Settings - not via hotkeys."),
            ],
        },
        {
            "title": "2. BATTLE - THE BASICS",
            "content": [
                ("header", "HOW A FIGHT STARTS"),
                ("body",   "'THE BATTLE BEGINS!' flashes, then combat."),
                ("body",   "Walk close to an enemy to trigger it."),
                ("gap",    ""),
                ("header", "TURN ORDER"),
                ("body",   "Turn-based. You act, then the enemy acts,"),
                ("body",   "then you act again."),
                ("gap",    ""),
                ("header", "ACTION BUTTONS (left panel)"),
                ("body",   "ATTACK          :   Hit one. Infinite uses."),
                ("body",   "ELEMENT ATTACK  :   Hits ALL. Half dmg. 10 uses."),
                ("body",   "ELEMENT BURST   :   Hits ALL. Full dmg. 5 uses."),
                ("body",   "RUN AWAY        :   Leave battle. Enemies regen"),
                ("body",   "                    to FULL HP after you confirm."),
                ("gap",    ""),
                ("header", "CHARGES"),
                ("body",   "Button text shows uses left, e.g. ELEM (8)."),
                ("body",   "Charges do NOT reset between waves."),
            ],
        },
        {
            "title": "3. TARGETING & MULTIPLE ENEMIES",
            "content": [
                ("header", "WHICH ENEMY DO I HIT?"),
                ("body",   "The enemy with the gold triangle above its"),
                ("body",   "head is your current target."),
                ("gap",    ""),
                ("header", "HOW TO CHANGE TARGET"),
                ("body",   "Left-click on any living enemy on screen."),
                ("body",   "Clicking the ground or menus does NOT"),
                ("body",   "retarget."),
                ("gap",    ""),
                ("header", "SINGLE TARGET vs ALL"),
                ("body",   "ATTACK hits only the current target."),
                ("body",   "ELEMENT ATTACK and BURST hit every enemy."),
                ("gap",    ""),
                ("header", "WHO ATTACKS ON THE ENEMY TURN"),
                ("body",   "1-2 enemies alive  :   one of them attacks."),
                ("body",   "3 enemies alive    :   two of them attack."),
            ],
        },
        {
            "title": "4. ELEMENTS & THE WHEEL",
            "content": [
                ("header", "FOUR ELEMENTS"),
                ("body",   "FIRE     WIND     EARTH     WATER"),
                ("gap",    ""),
                ("header", "THE WHEEL"),
                ("body",   "FIRE  >  WIND  >  EARTH  >  WATER  >  FIRE"),
                ("body",   "Fire beats Wind. Wind beats Earth. Earth beats"),
                ("body",   "Water. Water beats Fire."),
                ("gap",    ""),
                ("header", "DAMAGE MULTIPLIERS"),
                ("body",   "Strong against   :   1.5x damage"),
                ("body",   "Weak against     :   0.5x damage"),
                ("body",   "Neutral          :   1.0x damage"),
                ("gap",    ""),
                ("header", "PHYSICAL ATTACKS"),
                ("body",   "Weapons tagged 'Neutral' deal plain damage."),
                ("gap",    ""),
                ("header", "READING THE HUD"),
                ("body",   "Each enemy shows its element in a coloured"),
                ("body",   "chip next to its name."),
            ],
        },
        {
            "title": "5. STATUS EFFECTS",
            "content": [
                ("header", "WHAT THEY ARE"),
                ("body",   "Weapons and enemy skills can apply a status."),
                ("body",   "Most tick damage at the end of every round."),
                ("body",   "Main hand rolls 55%; off-hand rolls 60%;"),
                ("body",   "enemy skills roll 70%. PLAIN ATTACK procs"),
                ("body",   "Bleed + Stun only."),
                ("gap",    ""),
                ("header", "THE SEVEN STATUSES"),
                ("body",   "BURN       B  orange     1 dmg per stack"),
                ("body",   "BLEED      L  crimson    3% current HP / turn"),
                ("body",   "POISON     P  purple     0.5% max HP per stack"),
                ("body",   "BLUE FLAME F  ice blue   1% max HP per stack"),
                ("body",   "WEAK       W  blue-gray  -5 out dmg / stack"),
                ("body",   "STUN       S  cyan       skips a turn"),
                ("body",   "HEALING    H  green      +2% missing HP / stack"),
            ],
        },
        {
            "title": "6. STATUS IN DETAIL",
            "content": [
                ("header", "STACKS & DURATION"),
                ("body",   "Most lose ONE stack per turn (Stun doesn't)."),
                ("body",   "Max: Burn 5 / Bleed 3 / Poison 5 /"),
                ("body",   "Blue 5 / Weak 5 / Stun 2 / Healing 3."),
                ("gap",    ""),
                ("header", "READING THE BADGES"),
                ("body",   "Coloured badges appear under HP bars. The"),
                ("body",   "gold pill at the top-right shows stacks."),
                ("body",   "Hover a badge to see a tooltip."),
                ("gap",    ""),
                ("header", "STATUS LETTERS"),
                ("body",   "B = Burn          L = Bleed       P = Poison"),
                ("body",   "F = Blue Flame    W = Weak        S = Stun"),
                ("body",   "H = Healing"),
                ("gap",    ""),
                ("header", "BURN vs BLUE FLAME"),
                ("body",   "Burn and Blue Flame cannot coexist on the"),
                ("body",   "same target. Applying one converts the other."),
            ],
        },
        {
            "title": "7. GEAR & DUAL-WIELD",
            "content": [
                ("header", "FIVE EQUIP SLOTS"),
                ("body",   "Helmet  Chestplate  Weapon  Off-Hand  Ring"),
                ("gap",    ""),
                ("header", "DUAL-WIELDING"),
                ("body",   "MAIN WEAPON (blue)  :   full damage + element"),
                ("body",   "OFF-HAND    (red)   :   passives only."),
                ("body",   "Off-hand only triggers on ELEMENT ATTACK /"),
                ("body",   "BURST. It does nothing on a plain ATTACK."),
                ("gap",    ""),
                ("header", "POTIONS"),
                ("body",   "Healing / Attack / Defense potions can be"),
                ("body",   "used mid-fight from the inventory panel."),
                ("body",   "Heal: +55% missing HP + Healing x3."),
                ("body",   "ATK / DEF: +10 for 5 player turns."),
            ],
        },
        {
            "title": "8. SAVING, WAVES & OUTSKIRTS",
            "content": [
                ("header", "SAVING"),
                ("body",   "Press ESC. Choose SAVE GAME. Saving heals"),
                ("body",   "you and every ALIVE enemy."),
                ("gap",    ""),
                ("header", "WAVES"),
                ("body",   "Some encounters chain waves. ELEM / BURST"),
                ("body",   "charges carry over between waves."),
                ("gap",    ""),
                ("header", "OUTSKIRTS HORDES"),
                ("body",   "Fight the three hordes west of the castle in"),
                ("body",   "ANY order. Clear all three to open the road."),
                ("gap",    ""),
                ("header", "THE WORLD MAP (M)"),
                ("body",   "Press M in any zone to see your journey."),
                ("body",   "Locked zones appear grayed out until earned."),
            ],
        },
    ]

    creators_list = [
        "Ortega, Juan Miguel",
        "Caasi, Reigne Darius R.",
        "Tagra, Jade Ian",
        "Llamera, John Andrei",
        "Angeles, Azhgel D.",
        "Lisan, John Marvin S.",
    ]

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

    page_indicator_y = btn_y + btn_h // 2

    current_tab = "tutorial"
    story_page = 0
    tutorial_page = 0

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

    def draw_tab(surface, rect, label, is_active):
        if is_active:
            bg = COLOR_BTN_BG; bd = COLOR_BORDER; tc = COLOR_GOLD; w = 3
        else:
            bg = COLOR_TAB_INACT; bd = COLOR_TAB_INACT_BD; tc = COLOR_TEXT_GRAY; w = 2

        pygame.draw.rect(surface, bg, rect, border_radius=8)
        pygame.draw.rect(surface, bd, rect, width=w, border_radius=8)

        draw_outlined_text(surface, label, font_tab, tc,
                           center=rect.center, outline_color=COLOR_OUTLINE)

        if is_active:
            pygame.draw.line(surface, COLOR_GOLD,
                             (rect.left + 15, rect.bottom - 6),
                             (rect.right - 15, rect.bottom - 6), 3)

    credits_columns = [
        [
            ("CHARACTERS", [
                ("Knight, Tiny Orc", "zerie - itch.io"),
                ("Tiny Devil",       "zerie - itch.io"),
                ("Wizard Oz",        "gandalfhardcore - itch.io"),
            ]),
            ("ELITE / BOSSES", [
                ("Gorgona", "CraftPix"),
                ("Kitsune", "CraftPix"),
            ]),
            ("MAPS / TILESETS", [
                ("Castle",               "r/PixelArt - Reddit"),
                ("Mystic Forest Tiles",  "immunitys - itch.io"),
                ("Final Zone Catacombs", "szadiart - itch.io"),
                ("Houses",               "szadiart - itch.io"),
                ("Chest",      "crumpaloo - itch.io"),

            ]),
        ],
        [
            ("ICONS & ARMOR", [
                ("Accessories",                 "dusk-games - itch.io"),
                ("Helm, & Chest", "willibab - itch.io"),
            ]),
            ("FONTS", [
                ("Antiquity Script Font", "ninjikin - itch.io"),
                ("Fantasy Medieval Font", "1001fonts.com"),
            ]),
            ("SOUND & ANIMATIONS", [
                ("Sound Effects",         "Pixabay"),
                ("Sound Effects", "YouTube"),
            ]),
            ("MADE WITH", [
                ("Code Editor", "VISUAL STUDIO CODE"),
                ("Pixel Art",   "Aseprite"),
                ("Design",      "Canva"),
            ]),
        ],
    ]

    def draw_credits_content(surface):
        draw_outlined_text(surface, "CREDITS", font_title, COLOR_GOLD,
                           center=(screen_w // 2, content_top + 40),
                           outline_color=COLOR_OUTLINE)

        pygame.draw.line(surface, COLOR_BORDER,
                         (container_rect.left + 120, content_top + 75),
                         (container_rect.right - 120, content_top + 75),
                         2)

        col_width = 540
        col_gap = 60

        left_edge = screen_w // 2 - (col_width * 2 + col_gap) // 2

        for col_index, sections in enumerate(credits_columns):
            col_x = left_edge + col_index * (col_width + col_gap)
            y = content_top + 100

            for header, items in sections:
                draw_outlined_text(surface, header, font_header, COLOR_GOLD,
                                   pos=(col_x, y),
                                   outline_color=COLOR_OUTLINE)
                y += HEADER_STEP

                for name, source in items:
                    draw_outlined_text(surface, name, font_body, COLOR_TEXT,
                                       pos=(col_x + 20, y),
                                       outline_color=COLOR_OUTLINE)

                    source_w = font_small.size(source)[0]
                    draw_outlined_text(surface, source, font_small, COLOR_TEXT_GRAY,
                                       pos=(col_x + col_width - source_w, y + 2),
                                       outline_color=COLOR_OUTLINE)
                    y += BODY_STEP

                y += GAP_STEP * 2

        draw_outlined_text(surface,
                           "Thank you to all the artists and creators who shared their work!",
                           font_small, COLOR_TEXT_GRAY,
                           center=(screen_w // 2, text_bottom_limit - 12),
                           outline_color=COLOR_OUTLINE)

    def draw_creators_content(surface):
        draw_outlined_text(surface, "TEAM PASAWAB", font_title, COLOR_GOLD,
                           center=(screen_w // 2, content_top + 50),
                           outline_color=COLOR_OUTLINE)

        pygame.draw.line(surface, COLOR_BORDER,
                         (screen_w // 2 - 260, content_top + 90),
                         (screen_w // 2 + 260, content_top + 90),
                         2)

        start_y = content_top + 160
        row_spacing = 58
        for index, name in enumerate(creators_list):
            draw_outlined_text(surface, name, font_name, COLOR_TEXT,
                               center=(screen_w // 2, start_y + index * row_spacing),
                               outline_color=COLOR_OUTLINE)

        draw_outlined_text(surface, "123 kanya kanya nah!",
                           font_small, COLOR_TEXT_GRAY,
                           center=(screen_w // 2, content_top + 560),
                           outline_color=COLOR_OUTLINE)

    def draw_paged_content(surface, page, page_idx, total):
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

        draw_outlined_text(surface, f"Page {page_idx + 1} / {total}",
                           font_small, COLOR_TEXT_GRAY,
                           center=(screen_w // 2, page_indicator_y),
                           outline_color=COLOR_OUTLINE)

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
                    running = False

                elif event.key == pygame.K_TAB:
                    order = ["credits", "creators", "story", "tutorial"]
                    current_tab = order[(order.index(current_tab) + 1) % len(order)]

                elif event.key == pygame.K_LEFT:
                    if current_tab == "story":
                        story_page = max(0, story_page - 1)
                    elif current_tab == "tutorial":
                        tutorial_page = max(0, tutorial_page - 1)

                elif event.key == pygame.K_RIGHT:
                    if current_tab == "story":
                        story_page = min(len(story_pages) - 1, story_page + 1)
                    elif current_tab == "tutorial":
                        tutorial_page = min(len(tutorial_pages) - 1, tutorial_page + 1)

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if credits_tab_rect.collidepoint(mouse_pos):
                    current_tab = "credits"
                    continue
                if creators_tab_rect.collidepoint(mouse_pos):
                    current_tab = "creators"
                    continue
                if story_tab_rect.collidepoint(mouse_pos):
                    current_tab = "story"
                    continue
                if tutorial_tab_rect.collidepoint(mouse_pos):
                    current_tab = "tutorial"
                    continue

                if current_tab == "story":
                    if prev_btn.rect.collidepoint(mouse_pos):
                        story_page = max(0, story_page - 1)
                    elif next_btn.rect.collidepoint(mouse_pos):
                        story_page = min(len(story_pages) - 1, story_page + 1)
                elif current_tab == "tutorial":
                    if prev_btn.rect.collidepoint(mouse_pos):
                        tutorial_page = max(0, tutorial_page - 1)
                    elif next_btn.rect.collidepoint(mouse_pos):
                        tutorial_page = min(len(tutorial_pages) - 1, tutorial_page + 1)

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

        draw_outlined_text(screen, "ABOUT", font_title, COLOR_GOLD,
                           center=title_center, outline_color=COLOR_OUTLINE)
        pygame.draw.line(screen, COLOR_BORDER,
                         (container_rect.left + 70, container_rect.top + 80),
                         (container_rect.right - 70, container_rect.top + 80),
                         2)

        draw_tab(screen, credits_tab_rect,  "CREDITS",       current_tab == "credits")
        draw_tab(screen, creators_tab_rect, "CREATORS",      current_tab == "creators")
        draw_tab(screen, story_tab_rect,    "GAME STORY",    current_tab == "story")
        draw_tab(screen, tutorial_tab_rect, "GAME TUTORIAL", current_tab == "tutorial")

        if current_tab == "credits":
            draw_credits_content(screen)
        elif current_tab == "creators":
            draw_creators_content(screen)
        elif current_tab == "story":
            draw_paged_content(screen, story_pages[story_page],
                               story_page, len(story_pages))
            try: prev_btn.update(mouse_pos)
            except TypeError: prev_btn.update()
            try: prev_btn.draw(screen, mouse_pos)
            except TypeError: prev_btn.draw(screen)
            try: next_btn.update(mouse_pos)
            except TypeError: next_btn.update()
            try: next_btn.draw(screen, mouse_pos)
            except TypeError: next_btn.draw(screen)
        elif current_tab == "tutorial":
            draw_paged_content(screen, tutorial_pages[tutorial_page],
                               tutorial_page, len(tutorial_pages))
            try: prev_btn.update(mouse_pos)
            except TypeError: prev_btn.update()
            try: prev_btn.draw(screen, mouse_pos)
            except TypeError: prev_btn.draw(screen)
            try: next_btn.update(mouse_pos)
            except TypeError: next_btn.update()
            try: next_btn.draw(screen, mouse_pos)
            except TypeError: next_btn.draw(screen)

        draw_outlined_text(screen,
                           "[Press ESC to Return | TAB to Switch Tabs | LEFT/RIGHT for Pages]",
                           font_small, COLOR_TEXT_GRAY,
                           center=hint_center, outline_color=COLOR_OUTLINE)

        pygame.display.flip()