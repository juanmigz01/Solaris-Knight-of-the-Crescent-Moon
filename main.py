import sys
import os
import math
import random

# ---------------------------------------------------------------------------
# PATH SETUP
# Works both when running from VS Code (python main.py) AND when running the
# packaged Solaris.exe built by PyInstaller --onefile.
#
#   BUNDLE_ROOT  -> read-only files that ship with the game (asset/, map/,
#                   gameplay/, python modules).
#                     * VS Code : the folder containing main.py
#                     * .exe    : the PyInstaller temp folder (sys._MEIPASS)
#
#   DATA_ROOT    -> writable files (saves/, setting.json).
#                     * VS Code : the folder containing main.py
#                     * .exe    : the folder containing Solaris.exe, so saves
#                                 PERSIST between runs.
# ---------------------------------------------------------------------------
_FROZEN = bool(getattr(sys, "frozen", False))

if _FROZEN:
    BUNDLE_ROOT = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    DATA_ROOT   = os.path.dirname(sys.executable)
else:
    BUNDLE_ROOT = os.path.dirname(os.path.abspath(__file__))
    DATA_ROOT   = BUNDLE_ROOT

# Anchor every relative path lookup ("asset/...", "map/...") to BUNDLE_ROOT.
# Several modules (player.py, enemies/*.py, Modules/objects.py) use relative
# paths like "asset/enemy_img/Player/DPlayer.png". Without this chdir they
# resolve against the shell's current directory, and if that's wrong the
# player silently falls back to a placeholder surface -- which is the bright
# blue rectangle you were seeing.
try:
    os.chdir(BUNDLE_ROOT)
except OSError as _e:
    print(f"[main] WARNING: could not chdir to {BUNDLE_ROOT}: {_e}")

PROJECT_ROOT = BUNDLE_ROOT
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Keep bytecode caches inside a writable folder in both modes.
CACHE_DIR = os.path.join(DATA_ROOT, "saves", "__pycache__")
try:
    os.makedirs(CACHE_DIR, exist_ok=True)
    sys.pycache_prefix = CACHE_DIR
except OSError:
    pass

import pygame

from player.player import Player
from Fmain_menu.main_menu import run_main_menu
from Modules.sound_manager import game_manager
from Modules.button import Button


# ---------------------------------------------------------------------------
# SAVE REDIRECT + BUNDLED-SAVE SEEDING (frozen only)
#
# A onefile .exe extracts everything to a temp folder that gets DELETED on
# exit -- that would wipe every slot_*.json and setting.json after each run.
# We point save_manager + the sound manager at DATA_ROOT (next to the .exe).
#
# The .exe ships with saves/ bundled inside. On first run, any slot_*.json /
# setting.json that is NOT already present next to the exe gets copied out.
# Existing files are NEVER overwritten, so:
#   - first launch  : seeds slot_1.json, slot_2.json, setting.json
#   - later launches: leaves your real progress untouched
#   - if you delete a file from dist\saves\, it re-seeds from the exe
# ---------------------------------------------------------------------------
if _FROZEN:
    try:
        import shutil
        from Modules import save_manager as _save_manager

        _persistent_saves = os.path.join(DATA_ROOT, "saves")
        os.makedirs(_persistent_saves, exist_ok=True)

        _save_manager.SAVES_DIR = _persistent_saves

        # ---- SEED BUNDLED SAVES (first run only) --------------------------
        _bundled_saves = os.path.join(BUNDLE_ROOT, "saves")
        if os.path.isdir(_bundled_saves):
            for _fname in os.listdir(_bundled_saves):
                if not _fname.endswith(".json"):
                    continue
                _src = os.path.join(_bundled_saves, _fname)
                _dst = os.path.join(_persistent_saves, _fname)
                if not os.path.exists(_dst):
                    try:
                        shutil.copy2(_src, _dst)
                        print(f"[main] Seeded save: {_fname}")
                    except OSError as _e:
                        print(f"[main] Could not seed {_fname}: {_e}")

        game_manager.saves_dir     = _persistent_saves
        game_manager.settings_file = os.path.join(_persistent_saves,
                                                  "setting.json")
        game_manager.load_settings()   # re-read from the new location
    except Exception as _e:
        print(f"[main] WARNING: could not redirect saves: {_e}")


# ---------------------------------------------------------------------------
# Sanity check: verify the player sprite sheet exists where we expect.
# If it's missing, Player falls back to the blue placeholder rectangle.
# ---------------------------------------------------------------------------
_p_sprite = os.path.join(PROJECT_ROOT, "asset", "enemy_img", "Player",
                         "DPlayer.png")
_p_json   = os.path.join(PROJECT_ROOT, "asset", "enemy_img", "Player",
                         "DPlayer.json")
if not (os.path.exists(_p_sprite) and os.path.exists(_p_json)):
    print("[main] WARNING: player sprite sheet missing!")
    print(f"[main]   CWD      : {os.getcwd()}")
    print(f"[main]   expected : {_p_sprite}")
    print("[main]   -> The player will render as a blue rectangle until fixed.")


pygame.init()

SCREEN_WIDTH  = 1920
SCREEN_HEIGHT = 1080
FPS = 60

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Solaris: Knight of the Crescent Moon")
clock = pygame.time.Clock()

COLOR_BG        = (15, 15, 30)
COLOR_PANEL     = (28, 26, 48)
COLOR_BORDER    = (212, 175, 55)
COLOR_GOLD      = (255, 215, 0)
COLOR_GLOW_GOLD = (255, 230, 140)
COLOR_WHITE     = (240, 235, 210)
COLOR_BTN_BG    = (35, 30, 60)
COLOR_BTN_HOV   = (60, 50, 95)

FONT_PATH = os.path.join(PROJECT_ROOT, "asset", "font", "TheGothicRite.otf")
try:
    font_loading = pygame.font.Font(FONT_PATH, 34)
    font_sub = pygame.font.Font(FONT_PATH, 22)
except (FileNotFoundError, OSError):
    font_loading = pygame.font.SysFont("Georgia", 34, bold=True)
    font_sub = pygame.font.SysFont("Georgia", 22, bold=True)

MOON_PATH = os.path.join(PROJECT_ROOT, "asset", "img", "moon.png")
if os.path.exists(MOON_PATH):
    raw_moon = pygame.image.load(MOON_PATH).convert_alpha()
    orig_w, orig_h = raw_moon.get_size()
    target_h = 360
    target_w = int(target_h * (orig_w / orig_h))
    moon_img = pygame.transform.scale(raw_moon, (target_w, target_h))
else:
    moon_img = None


STAR_SURFACES = {}
for size in (1, 2, 3):
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    surf.fill((255, 255, 255, 255))
    STAR_SURFACES[size] = surf


def make_gradient_bg(w, h, top_color, bottom_color):
    surf = pygame.Surface((w, h))
    for y in range(h):
        t = y / float(h - 1)
        r = int(top_color[0] + (bottom_color[0] - top_color[0]) * t)
        g = int(top_color[1] + (bottom_color[1] - top_color[1]) * t)
        b = int(top_color[2] + (bottom_color[2] - top_color[2]) * t)
        pygame.draw.line(surf, (r, g, b), (0, y), (w, y))
    return surf


def make_vignette(w, h, strength=45):
    small_w, small_h = 240, 135
    small = pygame.Surface((small_w, small_h), pygame.SRCALPHA)
    cx, cy = small_w / 2.0, small_h / 2.0
    max_dist = math.hypot(cx, cy)

    for y in range(small_h):
        for x in range(small_w):
            d = math.hypot(x - cx, y - cy) / max_dist
            t = max(0.0, (d - 0.55) / 0.45)
            alpha = int(strength * min(1.0, t))
            if alpha > 0:
                small.set_at((x, y), (0, 0, 0, alpha))

    return pygame.transform.smoothscale(small, (w, h))


GRADIENT_BG = make_gradient_bg(SCREEN_WIDTH, SCREEN_HEIGHT,
                               COLOR_BG, (24, 22, 48))
VIGNETTE    = make_vignette(SCREEN_WIDTH, SCREEN_HEIGHT, strength=45)


hero = Player(x=120, y=740, scale=3.4)
hero.set_animation("walk")
hero.facing_right = True

stars = [
    {
        "x": random.randint(0, SCREEN_WIDTH),
        "y": random.randint(0, SCREEN_HEIGHT - 250),
        "speed": random.uniform(0.15, 0.4),
        "size": random.randint(1, 3),
    }
    for _ in range(60)
]

loading_phrases = [
    "The Moon Remembers His Name...",
    "Steel and Starlight Awaken...",
    "A Promise Still Unbroken...",
    "The Kingdom of Aurelia Awaits..."
]


def run_loading_screen():
    game_manager.play_music("intro.mp3", fade_ms=1500)

    skip_button = Button(
        x=40,
        y=40,
        width=130,
        height=42,
        text="Skip",
        font=font_sub,
        bg_color=COLOR_BTN_BG,
        hover_color=COLOR_BTN_HOV,
        text_color=COLOR_GOLD,
        border_color=COLOR_BORDER,
        border_radius=8,
    )

    progress = 0.0
    progress_speed = 0.35
    frame_count = 0

    moon_base_x = 1320
    moon_base_y = 160

    player_start_x = 100
    player_end_x = 480

    last_phrase_idx = -1
    phrase_alpha = 255.0
    PHRASE_FADE_SPEED = 12.0

    running = True
    fade_alpha = 0
    music_fade_started = False

    while running:
        clock.tick(FPS)
        frame_count += 1
        progress = min(100.0, progress + progress_speed)

        hero.x = player_start_x + (progress / 100.0) * (player_end_x - player_start_x)
        hero_bob = math.sin(frame_count * 0.18) * 3.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_SPACE, pygame.K_RETURN,
                                 pygame.K_KP_ENTER, pygame.K_ESCAPE):
                    if progress < 100.0:
                        progress = 100.0

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if progress < 100.0 and skip_button.rect.collidepoint(event.pos):
                    progress = 100.0

        screen.blit(GRADIENT_BG, (0, 0))

        for star in stars:
            star["x"] -= star["speed"]
            if star["x"] < 0:
                star["x"] = SCREEN_WIDTH
                star["y"] = random.randint(0, SCREEN_HEIGHT - 250)

            alpha = int(120 + math.sin(frame_count * 0.04 + star["x"]) * 90)
            alpha = max(0, min(255, alpha))

            dot = STAR_SURFACES[star["size"]]
            dot.set_alpha(alpha)
            screen.blit(dot, (star["x"], star["y"]))

        moon_float_y = moon_base_y + math.sin(frame_count * 0.03) * 12
        moon_x_pos = moon_base_x - (progress * 0.8)

        if moon_img:
            screen.blit(moon_img, (moon_x_pos, moon_float_y))

        hero.set_animation("walk")
        walk_frames = hero.animations.get("walk", [])
        if walk_frames:
            hero.frame_timer += 0.18
            if hero.frame_timer >= 1.0:
                hero.frame_timer = 0.0
                hero.frame_index = (hero.frame_index + 1) % len(walk_frames)

            curr_frame = walk_frames[hero.frame_index]
            if not hero.facing_right:
                curr_frame = pygame.transform.flip(curr_frame, True, False)

            player_rect = curr_frame.get_rect(
                midbottom=(int(hero.x), int(hero.y + hero_bob))
            )
            screen.blit(curr_frame, player_rect)

        phrase_idx = min(len(loading_phrases) - 1,
                         int((progress / 100.0) * len(loading_phrases)))

        if phrase_idx != last_phrase_idx:
            last_phrase_idx = phrase_idx
            phrase_alpha = 0.0
        else:
            phrase_alpha = min(255.0, phrase_alpha + PHRASE_FADE_SPEED)

        current_status = loading_phrases[phrase_idx]
        status_surf = font_loading.render(current_status, True, COLOR_WHITE)
        status_surf.set_alpha(int(phrase_alpha))
        status_rect = status_surf.get_rect(center=(SCREEN_WIDTH // 2, 880))
        screen.blit(status_surf, status_rect)

        bar_w, bar_h = 680, 12
        bar_x = (SCREEN_WIDTH - bar_w) // 2
        bar_y = 930

        pygame.draw.rect(screen, COLOR_BORDER,
                         (bar_x - 3, bar_y - 3, bar_w + 6, bar_h + 6),
                         width=2, border_radius=6)
        pygame.draw.rect(screen, COLOR_PANEL,
                         (bar_x, bar_y, bar_w, bar_h), border_radius=4)

        fill_w = int((progress / 100.0) * bar_w)
        if fill_w > 0:
            pygame.draw.rect(screen, COLOR_GOLD,
                             (bar_x, bar_y, fill_w, bar_h), border_radius=4)

        percent_surf = font_sub.render(f"{int(progress)}%", True, COLOR_GLOW_GOLD)
        screen.blit(percent_surf, (bar_x + bar_w + 22, bar_y - 5))

        if progress < 100.0:
            try:
                skip_button.draw(screen)
            except TypeError:
                skip_button.draw(screen)

        screen.blit(VIGNETTE, (0, 0))

        if progress >= 100.0:
            if not music_fade_started:
                game_manager.stop_music(fade_ms=2500)
                music_fade_started = True

            fade_alpha += 3
            fade_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            fade_surf.fill((0, 0, 0))
            fade_surf.set_alpha(min(255, fade_alpha))
            screen.blit(fade_surf, (0, 0))

            if fade_alpha >= 255:
                running = False

        pygame.display.flip()

    game_manager.stop_music(fade_ms=0)
    run_main_menu(screen)


if __name__ == "__main__":
    run_loading_screen()