
import os
import sys
import math
import random
import pygame

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    from enemies.enemy_element import ElementComponent
except ImportError:
    ElementComponent = None

try:
    from Modules.sound_manager import game_manager
except ImportError:
    game_manager = None


SPLASH_DURATION    = 0.9
SPLASH_FADE_IN     = 0.15
SPLASH_FADE_OUT    = 0.30
SPLASH_CENTER      = (640, 240)
SPLASH_RISE_PIXELS = 20

WEAPON_STATUS_CHANCE  = 0.55
OFF_HAND_STATUS_CHANCE = 0.60

COLOR_WHITE = (255, 255, 255)

PLAYER_ACTION_COLOR = (140, 200, 255)
ENEMY_ACTION_COLOR  = (255, 130, 130)


HURT_FLASH_DURATION  = 0.50
HURT_FLASH_MAX_ALPHA = 200
LOW_HP_THRESHOLD     = 0.30
LOW_HP_BORDER_THICKNESS = 10
LOW_HP_PULSE_SPEED   = 3.0
LOW_HP_MIN_ALPHA     = 60
LOW_HP_MAX_ALPHA     = 120


DROP_FADE_IN = 0.30
DROP_HOLD    = 0.55
DROP_FLY     = 0.45
DROP_TOTAL   = DROP_FADE_IN + DROP_HOLD + DROP_FLY

DROP_TARGET_X = 1760
DROP_TARGET_Y = 480


ENEMY_LAYOUTS = {
    1: [(900,  380, 1.10)],
    2: [(870,  395, 0.85), (1060, 375, 0.85)],
    3: [(800,  410, 0.70), (960,  375, 0.70), (1120, 410, 0.70)],
}


def get_enemy_layout(count):
    if count <= 1:
        return ENEMY_LAYOUTS[1]
    if count >= 3:
        return ENEMY_LAYOUTS[3]
    return ENEMY_LAYOUTS[count]


ELEMENT_COLORS = {
    "Fire":    {"text": (255, 214, 180), "border": (240, 110, 60),  "bg": (58, 22, 16)},
    "Water":   {"text": (190, 225, 255), "border": (80, 160, 240),  "bg": (16, 36, 66)},
    "Earth":   {"text": (230, 214, 168), "border": (185, 140, 80),  "bg": (48, 36, 18)},
    "Wind":    {"text": (210, 255, 215), "border": (120, 220, 150), "bg": (16, 46, 28)},
    "Neutral": {"text": (225, 225, 235), "border": (150, 150, 170), "bg": (30, 30, 38)},
    "True":    {"text": (245, 220, 255), "border": (190, 140, 220), "bg": (40, 20, 50)},
    "Moon":    {"text": (225, 210, 255), "border": (170, 140, 220), "bg": (30, 20, 50)},
}

_NEUTRAL_ELEMENTS = ("Neutral", "True", "Moon")


def get_element_text_color(element):
    elem_str = getattr(element, "element_type", element)
    if not elem_str or elem_str in _NEUTRAL_ELEMENTS:
        return COLOR_WHITE
    info = ELEMENT_COLORS.get(elem_str)
    if not info:
        return COLOR_WHITE
    return info["border"]


class ScreenShake:

    def __init__(self):
        self._intensity = 0.0
        self._duration  = 0.0
        self._elapsed   = 0.0
        self.offset = (0, 0)

    def trigger(self, intensity=6.0, duration=0.25):
        if intensity >= self._intensity:
            self._intensity = float(intensity)
        self._duration = max(self._duration, float(duration))
        self._elapsed = 0.0

    def update(self, dt):
        if self._duration <= 0:
            self.offset = (0, 0)
            return
        self._elapsed += dt
        if self._elapsed >= self._duration:
            self._intensity = 0.0
            self._duration = 0.0
            self._elapsed = 0.0
            self.offset = (0, 0)
            return

        progress = self._elapsed / self._duration
        decay = (1.0 - progress) ** 2
        amp = self._intensity * decay
        amp_i = max(1, int(amp))
        self.offset = (
            random.randint(-amp_i, amp_i),
            random.randint(-amp_i, amp_i),
        )

    @staticmethod
    def intensity_for_damage(dmg):
        if dmg <= 0:
            return 0.0
        if dmg <= 5:
            return 3.0
        if dmg <= 15:
            return 5.0
        if dmg <= 30:
            return 8.0
        return 12.0


_STATUS_NAME_TO_LETTER = {
    "Burn":       "B",
    "Bleed":      "L",
    "Poison":     "P",
    "Blue Flame": "F",
    "Weak":       "W",
    "Stun":       "S",
    "Healing":    "H",
}


def _format_action_line(move_name, damage, statuses=None):
    line = f"{move_name}: {damage}"
    if not statuses:
        return line

    seen = set()
    for entry in statuses:
        if not isinstance(entry, tuple) or len(entry) < 2:
            continue
        name, stacks = entry[0], entry[1]
        letter = _STATUS_NAME_TO_LETTER.get(name)
        if letter is None:
            continue
        if letter in seen:
            continue
        seen.add(letter)
        line += f"  [{letter}]: {stacks}"
    return line


_FLOAT_FONT_CACHE = {}


def _get_float_font(size):
    size = int(max(8, min(72, size)))
    if size not in _FLOAT_FONT_CACHE:
        font_path = os.path.join(PROJECT_ROOT, "asset", "font",
                                 "TheGothicRite.otf")
        if os.path.exists(font_path):
            _FLOAT_FONT_CACHE[size] = pygame.font.Font(font_path, size)
        else:
            _FLOAT_FONT_CACHE[size] = pygame.font.SysFont(
                "Georgia", size, bold=True)
    return _FLOAT_FONT_CACHE[size]


FLOATING_ELEMENT_COLORS = {
    "Fire":    (255, 140, 60),
    "Water":   (110, 190, 255),
    "Earth":   (220, 180, 90),
    "Wind":    (130, 240, 160),
    "Neutral": (245, 245, 245),
    "True":    (225, 190, 255),
    "Moon":    (215, 200, 255),
}

FLOATING_STATUS_COLORS = {
    "burn":       (255, 130, 60),
    "bleed":      (230, 60, 90),
    "poison":     (170, 220, 110),
    "blue_flame": (90, 180, 255),
    "weak":       (180, 180, 210),
    "stun":       (200, 230, 255),
    "healing":    (120, 255, 140),
}

FLOATING_POTION_COLORS = {
    "heal": (120, 255, 140),
    "atk":  (255, 140, 120),
    "def":  (150, 210, 255),
}


def get_element_float_color(element):
    elem_str = getattr(element, "element_type", element)
    if not elem_str:
        return FLOATING_ELEMENT_COLORS["Neutral"]
    return FLOATING_ELEMENT_COLORS.get(elem_str,
                                        FLOATING_ELEMENT_COLORS["Neutral"])


def get_status_float_color(status_key):
    return FLOATING_STATUS_COLORS.get(status_key, (230, 220, 255))


def _size_from_damage(dmg, base_min=20, base_max=46, scale=0.75):
    try:
        d = max(0, int(dmg))
    except (TypeError, ValueError):
        d = 0
    size = base_min + int(d * scale)
    size = max(base_min, min(base_max, size))
    size += random.randint(-2, 2)
    return max(base_min - 2, min(base_max + 4, size))


def get_burst_flash_color(element):
    elem_str = getattr(element, "element_type", element)
    if not elem_str:
        return (255, 255, 255)
    base = FLOATING_ELEMENT_COLORS.get(elem_str, (255, 255, 255))
    return (
        min(255, base[0] + 60),
        min(255, base[1] + 60),
        min(255, base[2] + 60),
    )


def _flash_surface(target, color, strength):
    try:
        w, h = target.get_size()
    except Exception:
        return
    alpha = int(230 * max(0.0, min(1.0, strength)))
    if alpha <= 0:
        return
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    surf.fill((int(color[0]), int(color[1]), int(color[2]), alpha))
    target.blit(surf, (0, 0))


def _make_hit_flash(img, alpha):
    try:
        mask = pygame.mask.from_surface(img, 100)
        sil = mask.to_surface(setcolor=(255, 255, 255, int(alpha)),
                              unsetcolor=(0, 0, 0, 0))
        return sil
    except Exception:
        return None


class FloatingText:

    MIN_SIZE       = 20
    MAX_SIZE       = 34
    BASE_LIFETIME  = 1.25

    def __init__(self, text, x, y, color, size=None, lifetime=None):
        self.text = str(text)
        self.x = float(x)
        self.y = float(y)
        self.color = color
        self.font_size = (size if size
                          else random.randint(self.MIN_SIZE, self.MAX_SIZE))
        self.lifetime = lifetime if lifetime else self.BASE_LIFETIME
        self.elapsed = 0.0
        self.drift_x = random.uniform(-14.0, 14.0)
        self.rise_speed = random.uniform(36.0, 58.0)

    def update(self, dt):
        self.elapsed += dt
        self.y -= self.rise_speed * dt
        self.x += self.drift_x * dt
        return self.elapsed < self.lifetime

    def draw(self, surface):
        t = self.elapsed / self.lifetime

        if t < 0.15:
            alpha = int(255 * (t / 0.15))
        elif t < 0.60:
            alpha = 255
        else:
            alpha = int(255 * (1.0 - (t - 0.60) / 0.40))
        alpha = max(0, min(255, alpha))
        if alpha <= 0:
            return

        if t < 0.10:
            scale = 0.55 + (t / 0.10) * 0.55
        elif t < 0.20:
            scale = 1.10 - ((t - 0.10) / 0.10) * 0.10
        else:
            scale = 1.0

        font = _get_float_font(self.font_size)
        base = font.render(self.text, True, self.color)
        outline = font.render(self.text, True, (0, 0, 0))

        if abs(scale - 1.0) > 0.01:
            w = max(1, int(base.get_width() * scale))
            h = max(1, int(base.get_height() * scale))
            base = pygame.transform.scale(base, (w, h))
            outline = pygame.transform.scale(outline, (w, h))

        base.set_alpha(alpha)
        outline.set_alpha(alpha)

        rect = base.get_rect(center=(int(self.x), int(self.y)))
        for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
            surface.blit(outline, (rect.x + dx, rect.y + dy))
        surface.blit(base, rect)


class FloatingTextManager:

    def __init__(self):
        self.texts = []

    def spawn(self, text, x, y, color, size=None):
        self.texts.append(FloatingText(text, x, y, color, size=size))

    def update(self, dt):
        if not self.texts:
            return
        self.texts = [t for t in self.texts if t.update(dt)]

    def draw(self, surface):
        for t in self.texts:
            t.draw(surface)


class StatusPopIcon:

    LIFETIME = 0.65

    def __init__(self, letter, color, start_xy, end_xy):
        self.letter = letter
        self.color = color
        self.x0, self.y0 = start_xy
        self.x1, self.y1 = end_xy
        self.elapsed = 0.0
        mid_x = (self.x0 + self.x1) * 0.5
        mid_y = min(self.y0, self.y1) - 80
        self.cx, self.cy = mid_x, mid_y

    def update(self, dt):
        self.elapsed += dt
        return self.elapsed < self.LIFETIME

    def _bezier(self, t):
        u = 1.0 - t
        x = u * u * self.x0 + 2 * u * t * self.cx + t * t * self.x1
        y = u * u * self.y0 + 2 * u * t * self.cy + t * t * self.y1
        return x, y

    def draw(self, surface):
        t = self.elapsed / self.LIFETIME
        tt = t * t
        x, y = self._bezier(tt)

        if t > 0.75:
            alpha = int(255 * (1.0 - (t - 0.75) / 0.25))
        else:
            alpha = 255
        alpha = max(0, min(255, alpha))
        if alpha <= 0:
            return

        size = int(24 + (1.0 - t) * 14)
        size = max(12, size)

        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(surf, self.color, (size // 2, size // 2), size // 2)
        pygame.draw.circle(surf, (0, 0, 0), (size // 2, size // 2),
                           size // 2, 2)

        font = _get_float_font(max(10, int(size * 0.75)))
        letter_surf = font.render(self.letter, True, (0, 0, 0))
        ls_shadow   = font.render(self.letter, True, (255, 255, 255))
        lrect = letter_surf.get_rect(center=(size // 2, size // 2))
        surf.blit(ls_shadow, (lrect.x + 1, lrect.y + 1))
        surf.blit(letter_surf, lrect)

        surf.set_alpha(alpha)
        surface.blit(surf, surf.get_rect(center=(int(x), int(y))))


class HealSparkle:

    LIFETIME = 0.85

    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.vx = random.uniform(-50.0, 50.0)
        self.vy = random.uniform(-110.0, -60.0)
        self.gravity = 60.0
        self.elapsed = 0.0
        self.size = random.choice((2, 3, 3, 4))
        self.color = random.choice(((120, 255, 140), (160, 255, 180),
                                     (200, 255, 210)))

    def update(self, dt):
        self.elapsed += dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += self.gravity * dt
        return self.elapsed < self.LIFETIME

    def draw(self, surface):
        t = self.elapsed / self.LIFETIME
        alpha = int(255 * max(0.0, 1.0 - t))
        if alpha <= 0:
            return
        dot = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
        dot.fill((self.color[0], self.color[1], self.color[2], alpha))
        surface.blit(dot, dot.get_rect(center=(int(self.x), int(self.y))))


class HealSparkleSystem:

    def __init__(self, count=0):
        self.sparkles = []
        if count > 0:
            self.spawn_burst(count)

    def spawn_burst(self, count, base_x=300, base_y=420):
        for _ in range(count):
            ox = random.randint(-26, 26)
            oy = random.randint(-10, 20)
            self.sparkles.append(HealSparkle(base_x + ox, base_y + oy))

    def update(self, dt):
        if not self.sparkles:
            return
        self.sparkles = [s for s in self.sparkles if s.update(dt)]

    def draw(self, surface):
        for s in self.sparkles:
            s.draw(surface)


class JuiceManager:

    def __init__(self):
        self.float_texts = FloatingTextManager()
        self.status_pops = []
        self.heal_sparkles = HealSparkleSystem(count=0)

    def spawn_float(self, text, x, y, color, size=None):
        self.float_texts.spawn(text, x, y, color, size=size)

    def spawn_status_pop(self, letter, color, start_xy, end_xy):
        self.status_pops.append(StatusPopIcon(letter, color, start_xy, end_xy))

    def spawn_heal_sparkles(self, count=14, base_x=300, base_y=420):
        self.heal_sparkles.spawn_burst(count, base_x, base_y)

    def update(self, dt):
        self.float_texts.update(dt)
        if self.status_pops:
            self.status_pops = [p for p in self.status_pops if p.update(dt)]
        self.heal_sparkles.update(dt)

    def draw(self, surface):
        self.float_texts.draw(surface)
        for p in self.status_pops:
            p.draw(surface)
        self.heal_sparkles.draw(surface)


ELEMENT_SFX_MAP = {
    "Fire":    "fire.mp3",
    "Water":   "water.mp3",
    "Earth":   "earth.mp3",
    "Wind":    "wind.mp3",
    "Neutral": "slash.mp3",
    "True":    "slash.mp3",
    "Moon":    "slash.mp3",
}

SKILL_SFX_MAP = {
    "ATTACK":            "slash.mp3",
    "ELEMENTAL SLASH":   "slash.mp3",
    "ELEMENTAL BURST":   "boom.mp3",

    "Club Swing":        "thud.mp3",
    "Kindling Toss":     "fire.mp3",
    "Mud-Bomb":          "earth.mp3",
    "Geyser Spit":       "water.mp3",
    "Wind Slashes":      "wind.mp3",

    "Slimeball":         "water.mp3",
    "Slime Slime":       "powerup.mp3",
    "Gelatinous Rush":   "thud.mp3",

    "Demonic Claw":      "slash.mp3",
    "Demonic Slash":     "slash.mp3",

    "Azure Splash":      "slash.mp3",
    "Azure Freeze":      "darkmagic.mp3",

    "Tail Whip":         "thud.mp3",
    "Gale Slam":         "wind.mp3",
    "Cyclone Coil":      "powerup.mp3",
    "Quake Slam":        "earth.mp3",
    "Sunder Whip":       "slash.mp3",
    "Stone Skin":        "powerup.mp3",
    "Radiant Mend":      "heal.mp3",
    "Stone Gaze":        "darkmagic.mp3",
    "Rending Whip":      "slash.mp3",
    "Inferno Slam":      "fire.mp3",
    "Wrath Coil":        "powerup.mp3",
    "Eclipse Gaze":      "darkmagic.mp3",

    "STRIKE":            "thud.mp3",
}

DEFAULT_SKILL_SFX_VOLUME  = 0.50
DEFAULT_ATTACK_SFX_VOLUME = 0.55
DEFAULT_BURST_SFX_VOLUME  = 0.65
DEFAULT_STATUS_SFX_VOLUME = 0.40
DEFAULT_BUFF_SFX_VOLUME   = 0.45
DEFAULT_HEAL_SFX_VOLUME   = 0.55
DEFAULT_ROAR_SFX_VOLUME   = 0.65
DEFAULT_MISSED_SFX_VOLUME = 0.45

WIN_SFX_NAME  = "win.mp3"
LOSE_SFX_NAME = "lose.mp3"

WIN_SFX_VOL   = 1.0
LOSE_SFX_VOL  = 1.0

WARNING_SFX_NAME     = "warning.mp3"
WARNING_SFX_FALLBACK = "roar.mp3"
WARNING_SFX_VOL      = 0.70

TRANSITION_SFX_NAME = "text.mp3"
TRANSITION_SFX_VOL  = 0.55

_WARNING_FALLBACK_WARNED = False


def get_element_sfx(element):
    elem_str = getattr(element, "element_type", element)
    if not elem_str:
        return "slash.mp3"
    return ELEMENT_SFX_MAP.get(elem_str, "slash.mp3")


def get_skill_sfx(move_name):
    if not move_name:
        return None
    return SKILL_SFX_MAP.get(move_name)


def play_skill_sfx(name, volume=None):
    if not name:
        return
    if game_manager is None:
        return
    if not getattr(game_manager, "sfx_enabled", True):
        return
    try:
        game_manager.play_sfx(
            name,
            volume=(volume if volume is not None
                    else DEFAULT_SKILL_SFX_VOLUME))
    except Exception:
        pass


def _sfx_file_exists(name):
    if not name:
        return False
    path = os.path.join(PROJECT_ROOT, "asset", "sfx", name)
    return os.path.exists(path)


def play_status_sfx(volume=None):
    play_skill_sfx("darkmagic.mp3",
                   volume=volume if volume is not None
                   else DEFAULT_STATUS_SFX_VOLUME)


def play_heal_sfx(volume=None):
    play_skill_sfx("heal.mp3",
                   volume=volume if volume is not None
                   else DEFAULT_HEAL_SFX_VOLUME)


def play_buff_sfx(volume=None):
    play_skill_sfx("powerup.mp3",
                   volume=volume if volume is not None
                   else DEFAULT_BUFF_SFX_VOLUME)


def play_missed_sfx(volume=None):
    play_skill_sfx("missed.mp3",
                   volume=volume if volume is not None
                   else DEFAULT_MISSED_SFX_VOLUME)


def play_roar_sfx(volume=None):
    play_skill_sfx("roar.mp3",
                   volume=volume if volume is not None
                   else DEFAULT_ROAR_SFX_VOLUME)


def play_battle_win_sfx(volume=None):
    play_skill_sfx(WIN_SFX_NAME,
                   volume=volume if volume is not None else WIN_SFX_VOL)


def play_battle_lose_sfx(volume=None):
    play_skill_sfx(LOSE_SFX_NAME,
                   volume=volume if volume is not None else LOSE_SFX_VOL)


def play_transition_sfx(volume=None):
    play_skill_sfx(TRANSITION_SFX_NAME,
                   volume=volume if volume is not None
                   else TRANSITION_SFX_VOL)


def play_warning_sfx(volume=None):
    global _WARNING_FALLBACK_WARNED

    if not _sfx_file_exists(WARNING_SFX_NAME):
        if not _WARNING_FALLBACK_WARNED:
            print(f"[Battle] WARNING: '{WARNING_SFX_NAME}' not found in "
                  f"asset/sfx/. Using '{WARNING_SFX_FALLBACK}' instead. "
                  f"Add warning.mp3 to hear the intended alert.")
            _WARNING_FALLBACK_WARNED = True
        play_skill_sfx(WARNING_SFX_FALLBACK,
                       volume=volume if volume is not None else WARNING_SFX_VOL)
        return

    play_skill_sfx(WARNING_SFX_NAME,
                   volume=volume if volume is not None else WARNING_SFX_VOL)


def stop_player_move_sfx():
    if game_manager is None:
        return
    try:
        game_manager.stop_sfx("walk")
        game_manager.stop_sfx("run")
    except Exception:
        pass


_hurt_vignette_cache = {}


def get_hurt_vignette(w, h):
    key = (w, h)
    cached = _hurt_vignette_cache.get(key)
    if cached is not None:
        return cached

    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    max_thickness = max(20, min(w, h) // 6)
    for i in range(max_thickness):
        t = i / float(max_thickness)
        alpha = int(160 * (1.0 - t) ** 1.8)
        if alpha <= 0:
            continue
        rect = pygame.Rect(i, i, w - i * 2, h - i * 2)
        pygame.draw.rect(surf, (180, 15, 15, alpha), rect, width=1)

    _hurt_vignette_cache[key] = surf
    return surf


def _make_element_chip(element_str, font, color_info):
    text_surf = font.render(element_str, True, color_info["text"])
    pad_x = 10
    pad_y = 3
    bw = text_surf.get_width() + pad_x * 2 + 1
    bh = text_surf.get_height() + pad_y * 2

    surf = pygame.Surface((bw, bh), pygame.SRCALPHA)
    pygame.draw.rect(surf, color_info["bg"], (0, 0, bw, bh), border_radius=5)
    surf.blit(text_surf, (pad_x, pad_y))
    surf.blit(text_surf, (pad_x + 1, pad_y))
    pygame.draw.rect(surf, color_info["border"], (0, 0, bw, bh),
                     width=2, border_radius=5)
    return surf


STATUS_INFO = {
    "burn":       {"letter": "B", "color": (255, 120, 60),
                   "desc": "Burn: takes damage each turn."},
    "bleed":      {"letter": "L", "color": (220, 50, 80),
                   "desc": "Bleed: takes 3% current HP per turn."},
    "poison":     {"letter": "P", "color": (150, 90, 200),
                   "desc": "Poison: 0.5% max HP damage per stack."},
    "blue_flame": {"letter": "F", "color": (90, 180, 255),
                   "desc": "Blue Flame: upgraded Burn. 1% max HP damage per stack."},
    "weak":       {"letter": "W", "color": (140, 160, 200),
                   "desc": "Weak: deals 5 less damage per stack."},
    "stun":       {"letter": "S", "color": (200, 230, 255),
                   "desc": "Stun: skips the target's next turn."},
    "healing":    {"letter": "H", "color": (120, 255, 140),
                   "desc": "Healing: restores 2% of missing HP per stack each turn."},
}

_BADGE_SIZE = 26
_BADGE_GAP  = 4

_TOOLTIP_FONT = None
_COUNT_FONT = None
_STUN_FONT = None


def _get_tooltip_font():
    global _TOOLTIP_FONT
    if _TOOLTIP_FONT is None:
        font_path = os.path.join(PROJECT_ROOT, "asset", "font", "TheGothicRite.otf")
        if os.path.exists(font_path):
            _TOOLTIP_FONT = pygame.font.Font(font_path, 16)
        else:
            _TOOLTIP_FONT = pygame.font.SysFont("Georgia", 16)
    return _TOOLTIP_FONT


def _get_count_font():
    global _COUNT_FONT
    if _COUNT_FONT is None:
        _COUNT_FONT = pygame.font.SysFont("Arial", 14, bold=True)
    return _COUNT_FONT


def _get_stun_font():
    global _STUN_FONT
    if _STUN_FONT is None:
        font_path = os.path.join(PROJECT_ROOT, "asset", "font", "TheGothicRite.otf")
        if os.path.exists(font_path):
            _STUN_FONT = pygame.font.Font(font_path, 22)
        else:
            _STUN_FONT = pygame.font.SysFont("Georgia", 22, bold=True)
    return _STUN_FONT


def _status_badge_width(status_manager):
    if status_manager is None:
        return 0
    active_count = sum(1 for c in status_manager.stacks.values() if c > 0)
    if active_count == 0:
        return 0
    return active_count * _BADGE_SIZE + (active_count - 1) * _BADGE_GAP


def _draw_status_badges(surface, status_manager, x, y, mouse_pos, hover_rects):
    if status_manager is None:
        return

    letter_font = _get_tooltip_font()
    count_font = _get_count_font()
    cur_x = x

    for key, count in status_manager.stacks.items():
        if count <= 0:
            continue
        info = STATUS_INFO.get(key)
        if not info:
            continue

        rect = pygame.Rect(cur_x, y, _BADGE_SIZE, _BADGE_SIZE)
        is_hovered = mouse_pos is not None and rect.collidepoint(mouse_pos)
        border_color = (255, 255, 255) if is_hovered else (0, 0, 0)
        border_w = 3 if is_hovered else 2

        pygame.draw.rect(surface, info["color"], rect, border_radius=4)
        pygame.draw.rect(surface, border_color, rect,
                         width=border_w, border_radius=4)

        letter = letter_font.render(info["letter"], True, (0, 0, 0))
        letter_shadow = letter_font.render(info["letter"], True, (255, 255, 255))
        lrect = letter.get_rect(center=(rect.centerx, rect.centery))
        surface.blit(letter_shadow, (lrect.x + 1, lrect.y + 1))
        surface.blit(letter, lrect)

        if count > 1:
            num_surf = count_font.render(str(count), True, (255, 255, 255))
            pill_w = num_surf.get_width() + 8
            pill_h = num_surf.get_height() + 4
            pill_rect = pygame.Rect(rect.right - pill_w + 6, rect.top - 4,
                                    pill_w, pill_h)

            pygame.draw.rect(surface, (255, 215, 0), pill_rect, border_radius=6)
            inner = pill_rect.inflate(-4, -4)
            pygame.draw.rect(surface, (0, 0, 0), inner, border_radius=4)
            surface.blit(num_surf, num_surf.get_rect(center=inner.center))

        if is_hovered:
            hover_rects.append((rect, key))

        cur_x += _BADGE_SIZE + _BADGE_GAP


def _draw_status_tooltip(surface, hover_rects):
    if not hover_rects:
        return
    rect, key = hover_rects[0]
    info = STATUS_INFO.get(key)
    if not info:
        return

    font_small = _get_tooltip_font()
    text_surf = font_small.render(info["desc"], True, (240, 235, 210))

    pad = 8
    tooltip = pygame.Rect(rect.left, rect.bottom + 6,
                          text_surf.get_width() + pad * 2,
                          text_surf.get_height() + pad * 2)
    if tooltip.right > surface.get_width() - 4:
        tooltip.right = surface.get_width() - 4
    if tooltip.left < 4:
        tooltip.left = 4
    if tooltip.bottom > surface.get_height() - 4:
        tooltip.bottom = rect.top - 6

    pygame.draw.rect(surface, (20, 20, 30), tooltip, border_radius=6)
    pygame.draw.rect(surface, (212, 175, 55), tooltip, width=2, border_radius=6)
    surface.blit(text_surf, (tooltip.x + pad, tooltip.y + pad))


def draw_splash_text(surface, text, font, alpha, rise_offset=0, color=None):
    if not text or alpha <= 0:
        return
    text_color = color if color is not None else (255, 230, 100)
    base = font.render(text, True, text_color)
    outline = font.render(text, True, (0, 0, 0))

    cx, cy = SPLASH_CENTER
    rect = base.get_rect(center=(cx, cy + rise_offset))

    outline.set_alpha(alpha)
    for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2),
                   (-2, -2), (2, -2), (-2, 2), (2, 2)):
        surface.blit(outline, (rect.x + dx, rect.y + dy))

    base.set_alpha(alpha)
    surface.blit(base, rect)


def is_clicked(btn, pos):
    x = getattr(btn, "x", None)
    y = getattr(btn, "y", None)
    w = getattr(btn, "w", getattr(btn, "width", None))
    h = getattr(btn, "h", getattr(btn, "height", None))
    if x is not None and y is not None and w is not None and h is not None:
        return pygame.Rect(x, y, w, h).collidepoint(pos)
    rect = getattr(btn, "rect", None)
    if isinstance(rect, pygame.Rect):
        return rect.collidepoint(pos)
    return False


def has_elemental_weapon(player):
    if hasattr(player, "inventory") and player.inventory:
        eq_w = getattr(player.inventory, "equipped_weapon", None)
        if eq_w and getattr(eq_w, "max_elem_atk", 0) > 0:
            return True
        if eq_w and getattr(eq_w, "element", "Neutral") not in ("Neutral", "True"):
            return True
    return False


def has_burst_weapon(player):
    if hasattr(player, "inventory") and player.inventory:
        eq_w = getattr(player.inventory, "equipped_weapon", None)
        if eq_w is not None and getattr(eq_w, "burst", None):
            return True
    return False


def get_main_weapon(player):
    if hasattr(player, "inventory") and player.inventory:
        return getattr(player.inventory, "equipped_weapon", None)
    return None


def get_off_weapon(player):
    if hasattr(player, "inventory") and player.inventory:
        return getattr(player.inventory, "equipped_weapon_off", None)
    return None


def _atk_mult(player):
    return float(getattr(player, "atk_mult", 0.0))


def _elem_atk_mult(player):
    return float(getattr(player, "elem_atk_mult", 0.0))


def _elem_dmg_bonus(player, element):
    bonuses = getattr(player, "elem_dmg_bonus", None) or {}
    return float(bonuses.get(element, 0.0))


def _status_dmg_bonus(player, status_key):
    bonuses = getattr(player, "status_dmg_bonus", None) or {}
    return float(bonuses.get(status_key, 0.0))


def _effective_player_atk(player):
    base = int(getattr(player, "atk", 0))
    temp = int(getattr(player, "temp_atk_bonus", 0))
    return base + temp


def _effective_player_def(player):
    base = int(getattr(player, "defense", 0))
    temp = int(getattr(player, "temp_def_bonus", 0))
    return base + temp


def _strip_temp_potion_buffs(player):
    player.temp_atk_bonus = 0
    player.temp_def_bonus = 0
    player.temp_atk_bonus_turns = 0
    player.temp_def_bonus_turns = 0


def _tick_potion_buff_durations(player):
    if getattr(player, "temp_atk_bonus", 0) > 0:
        turns = int(getattr(player, "temp_atk_bonus_turns", 0))
        if turns > 0:
            turns -= 1
            player.temp_atk_bonus_turns = turns
            if turns <= 0:
                player.temp_atk_bonus = 0
                player.temp_atk_bonus_turns = 0

    if getattr(player, "temp_def_bonus", 0) > 0:
        turns = int(getattr(player, "temp_def_bonus_turns", 0))
        if turns > 0:
            turns -= 1
            player.temp_def_bonus_turns = turns
            if turns <= 0:
                player.temp_def_bonus = 0
                player.temp_def_bonus_turns = 0


def draw_potion_buffs_indicator(surface, rect, time_sec, has_atk, has_def,
                                atk_turns=0, def_turns=0):
    if rect is None:
        return
    if not has_atk and not has_def:
        return

    font = _get_stun_font()
    view_h = surface.get_height()

    bob = int(math.sin(time_sec * 4.5) * 3)
    cx = rect.centerx
    banner_y = rect.bottom + 14 + bob
    banner_y = min(view_h - 20, banner_y)

    labels = []
    if has_atk:
        txt = "ATK+" if atk_turns <= 0 else f"ATK+ ({atk_turns})"
        labels.append((txt, (255, 130, 120)))
    if has_def:
        txt = "DEF+" if def_turns <= 0 else f"DEF+ ({def_turns})"
        labels.append((txt, (150, 210, 255)))

    if labels:
        gap = 12
        surfaces = []
        for text, color in labels:
            surf = font.render(text, True, color)
            out  = font.render(text, True, (0, 0, 0))
            surfaces.append((surf, out))

        total_w = sum(s.get_width() for s, _ in surfaces) + gap * (len(surfaces) - 1)
        cur_x = cx - total_w // 2
        for text_surf, outline in surfaces:
            r = text_surf.get_rect(topleft=(cur_x, banner_y))
            for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2),
                           (-2, -2), (2, -2), (-2, 2), (2, 2)):
                surface.blit(outline, (r.x + dx, r.y + dy))
            surface.blit(text_surf, r)
            cur_x += text_surf.get_width() + gap

    orbits = []
    if has_atk and has_def:
        orbits.append(("atk", 0.0))
        orbits.append(("def", math.pi / 3))
    elif has_atk:
        orbits.append(("atk", 0.0))
    else:
        orbits.append(("def", 0.0))

    orbit_rx = max(14, int(rect.width * 0.42))
    orbit_ry = max(10, int(rect.height * 0.28))
    cy_spark = rect.centery

    for key, phase in orbits:
        if key == "atk":
            halo_color   = (140, 40, 40)
            dim_color    = (220, 90, 90)
            bright_color = (255, 150, 120)
            core_color   = (255, 230, 210)
        else:
            halo_color   = (40, 90, 160)
            dim_color    = (100, 160, 230)
            bright_color = (150, 210, 255)
            core_color   = (220, 240, 255)

        for i in range(3):
            angle = time_sec * 7.0 + phase + (i * (2 * math.pi / 3))
            sx = int(cx + math.cos(angle) * orbit_rx)
            sy = int(cy_spark + math.sin(angle) * orbit_ry)

            halo_surf = pygame.Surface((24, 24), pygame.SRCALPHA)
            pygame.draw.circle(halo_surf, (*halo_color, 90), (12, 12), 12)
            pygame.draw.circle(halo_surf, (*dim_color, 130), (12, 12), 8)
            surface.blit(halo_surf, (sx - 12, sy - 12))

            pygame.draw.circle(surface, dim_color,    (sx, sy), 9)
            pygame.draw.circle(surface, bright_color, (sx, sy), 6)
            pygame.draw.circle(surface, core_color,   (sx, sy), 3)


def _defense_multiplier(defense):
    try:
        d = max(0.0, float(defense))
    except (TypeError, ValueError):
        d = 0.0
    return 100.0 / (100.0 + d * 1.5)


def _target_resistance_mult(target, element):
    resistances = getattr(target, "elemental_resistances", None)
    if not resistances:
        return 1.0
    elem_str = getattr(element, "element_type", element)
    if not elem_str:
        return 1.0
    try:
        return float(resistances.get(elem_str, 1.0))
    except (TypeError, ValueError):
        return 1.0


def element_multiplier(attacker_element, defender_element):
    if ElementComponent is None:
        return 1.0
    atk_str = getattr(attacker_element, "element_type", attacker_element)
    def_str = getattr(defender_element, "element_type", defender_element)
    if not atk_str or atk_str in _NEUTRAL_ELEMENTS:
        return 1.0
    return ElementComponent(atk_str).get_damage_multiplier(def_str)


def apply_weapon_status(weapon, target_status, is_off_hand=False, is_basic=False,
                        other_weapon=None):
    if weapon is None or target_status is None:
        return []

    chance = OFF_HAND_STATUS_CHANCE if is_off_hand else WEAPON_STATUS_CHANCE

    special = getattr(weapon, "special_effects", {})
    msgs = []

    if "inflict_bleed" in special:
        if random.random() < chance:
            target_status.add_status("bleed", 1)
            msgs.append(("Bleed", 1))

    if "inflict_burn" in special:
        if random.random() < chance:
            stacks = special["inflict_burn"]
            target_status.add_status("burn", stacks)
            msgs.append(("Burn", stacks))

    if "stun_chance" in special:
        try:
            stun_chance = float(special["stun_chance"])
        except (TypeError, ValueError):
            stun_chance = 0.0
        if random.random() < stun_chance:
            target_status.add_status("stun", 1)
            msgs.append(("Stun", 1))

    if special.get("transform_blue_flame", False):
        other_special = getattr(other_weapon, "special_effects", {}) if other_weapon else {}
        other_has_burn = "inflict_burn" in other_special

        if other_has_burn:
            converted = target_status.convert_burn_to_blue_flame()
            if converted > 0:
                msgs.append(("Blue Flame", converted))

    if is_basic:
        return msgs

    if "inflict_poison" in special:
        if random.random() < chance:
            permanent = special.get("permanent_poison", False)
            if is_off_hand and special.get("permanent_poison_off_hand", False):
                permanent = True
            target_status.add_status("poison", 1, permanent=permanent)
            msgs.append(("Poison", 1))

    if "inflict_weak" in special:
        if random.random() < chance:
            stacks = special["inflict_weak"]
            target_status.add_status("weak", stacks)
            msgs.append(("Weak", stacks))

    return msgs


def try_trigger_burn_instantly(weapon, target_status, target):
    if weapon is None or target_status is None or target is None:
        return 0

    special = getattr(weapon, "special_effects", {})
    if not special.get("trigger_burn_instantly", False):
        return 0

    burn_stacks = target_status.stacks.get("burn", 0)
    blue_stacks = target_status.stacks.get("blue_flame", 0)
    fuel = burn_stacks + blue_stacks

    if fuel <= 0:
        return 0

    dmg = max(1, min(4, int(fuel)))
    target.hp = max(0, int(getattr(target, "hp", 0)) - dmg)
    return dmg


def consume_stun_if_any(entity, status_manager):
    if status_manager is None:
        return False
    if status_manager.stacks.get("stun", 0) <= 0:
        return False

    status_manager.stacks["stun"] = max(0, status_manager.stacks["stun"] - 1)
    set_entity_animation(entity, "idle")
    return True


def draw_stun_indicator(surface, rect, time_sec):
    if rect is None:
        return

    font = _get_stun_font()
    view_h = surface.get_height()

    bob = int(math.sin(time_sec * 4.5) * 3)
    cx = rect.centerx
    banner_y = rect.bottom + 14 + bob
    banner_y = min(view_h - 20, banner_y)

    pulse = (math.sin(time_sec * 6.0) + 1.0) * 0.5
    alpha = int(180 + 75 * pulse)

    text_surf = font.render("STUNNED!", True, (200, 230, 255))
    outline   = font.render("STUNNED!", True, (0, 0, 0))

    text_surf.set_alpha(alpha)
    outline.set_alpha(alpha)

    r = text_surf.get_rect(center=(cx, banner_y))
    for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2),
                   (-2, -2), (2, -2), (-2, 2), (2, 2)):
        surface.blit(outline, (r.x + dx, r.y + dy))
    surface.blit(text_surf, r)

    orbit_rx = max(14, int(rect.width * 0.42))
    orbit_ry = max(10, int(rect.height * 0.28))
    cy_spark = rect.centery

    halo_color   = (60, 110, 180)
    dim_color    = (140, 190, 240)
    bright_color = (200, 230, 255)
    core_color   = (255, 255, 255)

    for i in range(3):
        angle = time_sec * 9.0 + (i * (2 * math.pi / 3))
        sx = int(cx + math.cos(angle) * orbit_rx)
        sy = int(cy_spark + math.sin(angle) * orbit_ry)

        halo_surf = pygame.Surface((26, 26), pygame.SRCALPHA)
        pygame.draw.circle(halo_surf, (*halo_color, 90), (13, 13), 13)
        pygame.draw.circle(halo_surf, (*dim_color, 140), (13, 13), 9)
        surface.blit(halo_surf, (sx - 13, sy - 13))

        pygame.draw.circle(surface, dim_color,    (sx, sy), 10)
        pygame.draw.circle(surface, bright_color, (sx, sy), 6)
        pygame.draw.circle(surface, core_color,   (sx, sy), 3)


def set_entity_animation(entity, *names):
    if not hasattr(entity, "set_animation"):
        return
    anims = getattr(entity, "animations", None)
    if not anims:
        entity.set_animation(names[0])
        return
    lookup = {k.lower(): k for k in anims}
    for name in names:
        key = lookup.get(name.lower())
        if key:
            entity.set_animation(key)
            return


def play_hurt_animation(entity):
    set_entity_animation(entity,
                         "hurt", "damage", "hit", "takehit",
                         "take_hit", "damaged", "receivedamage")


def play_start_transition(screen, frame):
    try:
        play_transition_sfx()
    except Exception:
        pass

    clock = pygame.time.Clock()
    screen_w, screen_h = screen.get_size()

    font_path = os.path.join(PROJECT_ROOT, "asset", "font", "TheGothicRite.otf")
    if os.path.exists(font_path):
        font_banner = pygame.font.Font(font_path, 76)
    else:
        font_banner = pygame.font.SysFont("Georgia", 76, bold=True)

    banner_text = "THE BATTLE BEGINS!"
    banner_gold = font_banner.render(banner_text, True, (255, 215, 0))
    banner_out  = font_banner.render(banner_text, True, (0, 0, 0))

    dark = pygame.Surface((screen_w, screen_h))
    dark.fill((0, 0, 0))

    total_frames = 150
    half_h = screen_h // 2

    for i in range(total_frames):
        clock.tick(60)
        t = i / float(total_frames - 1)

        frame.draw(screen)

        if t < 0.15:
            bar_h = int(half_h * (t / 0.15))
        elif t < 0.85:
            bar_h = half_h
        else:
            bar_h = int(half_h * (1.0 - (t - 0.85) / 0.15))

        overlay_a = int(160 * min(1.0, t / 0.20))
        if t > 0.85:
            overlay_a = int(160 * (1.0 - (t - 0.85) / 0.15))
        if overlay_a > 0:
            dark.set_alpha(overlay_a)
            screen.blit(dark, (0, 0))

        if bar_h > 0:
            pygame.draw.rect(screen, (0, 0, 0),
                             pygame.Rect(0, 0, screen_w, bar_h))
            pygame.draw.rect(screen, (0, 0, 0),
                             pygame.Rect(0, screen_h - bar_h, screen_w, bar_h))

            seam_alpha = 255 if t < 0.82 else int(255 * max(0.0, 1.0 - (t - 0.82) / 0.18))
            seam_alpha = max(0, min(255, seam_alpha))
            if seam_alpha > 0:
                seam = pygame.Surface((screen_w, 4), pygame.SRCALPHA)
                seam.fill((255, 215, 0, seam_alpha))
                screen.blit(seam, (0, bar_h - 2))
                screen.blit(seam, (0, screen_h - bar_h - 2))

        if t < 0.15:
            text_alpha = 0
            scale = 0.65
        elif t < 0.30:
            local = (t - 0.15) / 0.15
            text_alpha = int(255 * local)
            scale = 0.65 + 0.35 * (1 - (1 - local) ** 3)
        elif t < 0.72:
            text_alpha = 255
            scale = 1.0
        elif t < 0.88:
            local = (t - 0.72) / 0.16
            text_alpha = int(255 * (1.0 - local))
            scale = 1.0
        else:
            text_alpha = 0
            scale = 1.0

        if text_alpha > 0:
            bw = max(1, int(banner_gold.get_width() * scale))
            bh = max(1, int(banner_gold.get_height() * scale))
            gold_scaled = pygame.transform.scale(banner_gold, (bw, bh))
            out_scaled = pygame.transform.scale(banner_out, (bw, bh))
            gold_scaled.set_alpha(text_alpha)
            out_scaled.set_alpha(text_alpha)

            cx = screen_w // 2
            cy = screen_h // 2

            for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2),
                           (-2, -2), (2, -2), (-2, 2), (2, 2)):
                r = out_scaled.get_rect(center=(cx + dx, cy + dy))
                screen.blit(out_scaled, r)
            r = gold_scaled.get_rect(center=(cx, cy))
            screen.blit(gold_scaled, r)

        if 0.30 < t < 0.42:
            local = (t - 0.30) / 0.12
            flash_a = int(200 * (1.0 - abs(local * 2 - 1)))
            flash_a = max(0, min(200, flash_a))
            if flash_a > 0:
                flash = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
                flash.fill((255, 255, 255, flash_a))
                screen.blit(flash, (0, 0))

        pygame.display.flip()


def draw_scaled_combatant(surface, entity, target_x, target_y,
                          facing_right=True, battle_scale=None,
                          shadow_mult=0.0,
                          pixel_offset=(0, 0),
                          alpha=255,
                          extra_scale=1.0,
                          hit_flash=0.0):
    if battle_scale is None:
        battle_scale = getattr(entity, "battle_scale", 5.0)

    battle_scale = battle_scale * max(0.05, float(extra_scale))

    img = getattr(entity, "image", None)
    if img is None and hasattr(entity, "animations"):
        anim = entity.animations.get(getattr(entity, "current_animation", "idle"), [])
        if anim:
            img = anim[getattr(entity, "frame_index", 0) % len(anim)]

    if img is None:
        if hasattr(entity, "draw"):
            entity.draw(surface)
        return None

    entity_scale = getattr(entity, "scale", 1.0)
    rel_scale = battle_scale / entity_scale if entity_scale > 0 else battle_scale

    scaled_w = int(img.get_width() * rel_scale)
    scaled_h = int(img.get_height() * rel_scale)
    scaled_img = pygame.transform.scale(img, (scaled_w, scaled_h))

    if not facing_right:
        scaled_img = pygame.transform.flip(scaled_img, True, False)

    if alpha < 255:
        scaled_img = scaled_img.copy()
        scaled_img.set_alpha(max(0, min(255, int(alpha))))

    if extra_scale == 1.0:
        anchor_offset = getattr(entity, "_battle_anchor_offset", None)
    else:
        anchor_offset = None

    if anchor_offset is None:
        v_rect = scaled_img.get_bounding_rect()
        if v_rect.width > 0 and v_rect.height > 0:
            offset_x = (scaled_w // 2) - v_rect.centerx
            offset_y = scaled_h - v_rect.bottom
        else:
            offset_x = 0
            offset_y = 0
        anchor_offset = (offset_x, offset_y)
        if extra_scale == 1.0:
            try:
                entity._battle_anchor_offset = anchor_offset
            except Exception:
                pass

    offset_x, offset_y = anchor_offset

    pos = (int(target_x - scaled_w // 2 + offset_x) + pixel_offset[0],
           int(target_y - scaled_h + offset_y) + pixel_offset[1])

    eff_shadow = shadow_mult * (alpha / 255.0)
    if eff_shadow > 0.02:
        shadow_w = int(160 * eff_shadow)
        shadow_h = int(40 * eff_shadow)
        shadow = pygame.Surface((shadow_w, shadow_h), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (20, 25, 30, 150), shadow.get_rect())
        surface.blit(shadow,
                     (int(target_x - shadow_w // 2) + pixel_offset[0],
                      int(target_y - shadow_h // 2) + pixel_offset[1]))

    surface.blit(scaled_img, pos)

    if hit_flash > 0.001:
        try:
            flash_a = int(210 * max(0.0, min(1.0, hit_flash)))
            sil = _make_hit_flash(scaled_img, flash_a)
            if sil is not None:
                surface.blit(sil, pos)
        except Exception:
            pass

    final_v = scaled_img.get_bounding_rect()
    if final_v.width > 0 and final_v.height > 0:
        return final_v.move(pos)
    return pygame.Rect(pos[0], pos[1], scaled_w, scaled_h)


def draw_target_marker(surface, rect, bob=0):
    if rect is None:
        return
    cx = rect.centerx
    top = rect.top - 14 + bob
    points = [(cx, top + 12), (cx - 11, top), (cx + 11, top)]
    pygame.draw.polygon(surface, (255, 215, 0), points)
    pygame.draw.polygon(surface, (0, 0, 0), points, 2)


def draw_huds(surface, player, enemies, font_large, font_main,
              player_status=None, enemy_statuses=None,
              target_index=0, mouse_pos=None):
    if enemy_statuses is None:
        enemy_statuses = [None] * len(enemies)

    hover_rects = []

    p_text = font_large.render(
        f"{getattr(player, 'name', 'Solaris')}: "
        f"{int(player.hp)} / {int(getattr(player, 'max_hp', 100))}",
        True, (255, 220, 100))
    surface.blit(p_text, (60, 30))

    if player_status is not None:
        _draw_status_badges(surface, player_status, 60, 72, mouse_pos, hover_rects)

    BLOCK_H = 66
    BASE_Y  = 30
    RIGHT_X = 1220

    target_enemy = None
    if 0 <= target_index < len(enemies):
        target_enemy = enemies[target_index]

    for i, enemy in enumerate(enemies):
        block_y = BASE_Y + i * BLOCK_H
        is_dead = getattr(enemy, "hp", 0) <= 0

        if is_dead:
            line_col = (140, 140, 140)
        elif i == target_index:
            line_col = (255, 230, 120)
        else:
            line_col = (255, 220, 100)

        marker = "> " if i == target_index and not is_dead else ""

        name = getattr(enemy, "name", "Enemy")
        elem = getattr(enemy, "element", None)
        elem_str = getattr(elem, "element_type", None) or "Neutral"

        left_surf = font_main.render(f"{marker}{name}", True, line_col)
        right_surf = font_main.render(
            f"{int(enemy.hp)} / {int(getattr(enemy, 'max_hp', 65))}", True, line_col)

        elem_color = ELEMENT_COLORS.get(elem_str, ELEMENT_COLORS["Neutral"])
        chip_surf = _make_element_chip(elem_str, font_main, elem_color)

        gap = 8
        total_w = (left_surf.get_width() + gap + chip_surf.get_width() + gap
                   + right_surf.get_width())
        start_x = RIGHT_X - total_w

        surface.blit(left_surf, (start_x, block_y))
        chip_x = start_x + left_surf.get_width() + gap
        chip_y = block_y + (left_surf.get_height() - chip_surf.get_height()) // 2
        surface.blit(chip_surf, (chip_x, chip_y))
        surface.blit(right_surf, (chip_x + chip_surf.get_width() + gap, block_y))

        st = enemy_statuses[i] if i < len(enemy_statuses) else None
        if st is not None and not is_dead:
            badge_w = _status_badge_width(st)
            if badge_w > 0:
                _draw_status_badges(surface, st, RIGHT_X - badge_w,
                                    block_y + 30, mouse_pos, hover_rects)

    if target_enemy is not None and getattr(target_enemy, "hp", 0) > 0:
        stats_y = BASE_Y + len(enemies) * BLOCK_H + 8
        evade_val = getattr(target_enemy, "evade", 0.0)
        evade_pct = (int(evade_val * 100)
                     if isinstance(evade_val, float) and evade_val <= 1.0
                     else int(evade_val))
        stats_str = (f"ATK: {getattr(target_enemy, 'atk', 0)}  |  "
                     f"DEF: {getattr(target_enemy, 'defense', 0)}  |  "
                     f"EVADE: {evade_pct}%")
        stats_surface = font_main.render(stats_str, True, (200, 200, 200))
        surface.blit(stats_surface,
                     stats_surface.get_rect(topright=(RIGHT_X, stats_y)))

    _draw_status_tooltip(surface, hover_rects)


def _dedupe_status_msgs(msgs, cap=4):
    seen = set()
    out = []
    for m in msgs:
        key = m[0] if isinstance(m, tuple) and len(m) >= 1 else m
        if key in seen:
            continue
        seen.add(key)
        out.append(m)
        if len(out) >= cap:
            break
    return out


def _compute_quests(player):
    return ["Defeat the enemies"]


def _collect_drops(enemies, player):
    try:
        from Modules.inv import get_enemy_drop, player_has_item
    except ImportError:
        return []

    drops = []
    for enemy in enemies:
        item_id = get_enemy_drop(enemy)
        if item_id is None:
            continue
        if item_id in drops:
            continue
        if player_has_item(player, item_id):
            continue
        drops.append(item_id)
    return drops


def _play_drop_animations(screen, drops, font_large, font_body):
    if not drops:
        return

    try:
        from Modules.inv import get_item_image
        from classes.armory_item import ItemDatabase
    except ImportError:
        return

    clock = pygame.time.Clock()
    screen_w, screen_h = screen.get_size()
    cx, cy = screen_w // 2, screen_h // 2
    snapshot = screen.copy()

    for item_id in drops:
        item = ItemDatabase.get_item(item_id)
        if item is None:
            continue

        img_base = get_item_image(getattr(item, "image_path", ""), size=(96, 96))
        name_surf = font_large.render(item.name, True, (255, 215, 0))
        sub_surf  = font_body.render("Added to inventory", True, (220, 220, 220))

        elapsed = 0.0
        skipped = False
        while elapsed < DROP_TOTAL and not skipped:
            dt = clock.tick(60) / 1000.0
            elapsed += dt

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                    skipped = True
                    break

            if skipped:
                break

            t = elapsed
            if t < DROP_FADE_IN:
                p = t / DROP_FADE_IN
                alpha = int(255 * p)
                scale = 0.6 + 0.4 * p
                x, y = cx, cy - 40
                overlay_alpha = int(140 * p)
            elif t < DROP_FADE_IN + DROP_HOLD:
                alpha = 255
                scale = 1.0
                x, y = cx, cy - 40
                overlay_alpha = 140
            else:
                p = (t - DROP_FADE_IN - DROP_HOLD) / DROP_FLY
                eased = p * p
                alpha = int(255 * (1.0 - p))
                scale = 1.0 - 0.6 * p
                x = cx + (DROP_TARGET_X - cx) * eased
                y = (cy - 40) + (DROP_TARGET_Y - (cy - 40)) * eased
                overlay_alpha = int(140 * (1.0 - p))

            screen.blit(snapshot, (0, 0))

            if overlay_alpha > 0:
                ov = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
                ov.fill((0, 0, 0, overlay_alpha))
                screen.blit(ov, (0, 0))

            if t < DROP_FADE_IN + DROP_HOLD:
                glow_size = max(40, int(150 * scale))
                glow = pygame.Surface((glow_size, glow_size), pygame.SRCALPHA)
                pygame.draw.circle(glow, (255, 215, 0, 70),
                                   (glow_size // 2, glow_size // 2),
                                   glow_size // 2)
                screen.blit(glow, (int(x - glow_size // 2), int(y - glow_size // 2)))

            sw = max(1, int(img_base.get_width() * scale))
            sh = max(1, int(img_base.get_height() * scale))
            scaled_img = pygame.transform.scale(img_base, (sw, sh))
            scaled_img.set_alpha(alpha)
            screen.blit(scaled_img, scaled_img.get_rect(center=(int(x), int(y))))

            if t < DROP_FADE_IN + DROP_HOLD:
                name_surf.set_alpha(alpha)
                sub_surf.set_alpha(alpha)
                screen.blit(name_surf, name_surf.get_rect(center=(cx, cy + 60)))
                screen.blit(sub_surf, sub_surf.get_rect(center=(cx, cy + 100)))

            pygame.display.flip()


def _handle_victory_drops(screen, player, enemies, font_large, font_body):
    drops = _collect_drops(enemies, player)
    if not drops:
        return

    try:
        from Modules.inv import give_item_by_id
        for item_id in drops:
            try:
                give_item_by_id(player, item_id)
            except Exception as e:
                print(f"[Battle] give_item_by_id failed for {item_id}: {e}")
    except ImportError:
        return

    try:
        _play_drop_animations(screen, drops, font_large, font_body)
    except Exception as e:
        print(f"[Battle] Drop animation failed: {e}")


def _draw_hurt_flash(viewport, timer):
    if timer <= 0:
        return
    progress = timer / HURT_FLASH_DURATION
    alpha = int(HURT_FLASH_MAX_ALPHA * progress)
    alpha = max(0, min(255, alpha))
    if alpha <= 0:
        return

    vw, vh = viewport.get_size()
    vignette = get_hurt_vignette(vw, vh)
    vignette.set_alpha(alpha)
    viewport.blit(vignette, (0, 0))


def _draw_low_hp_border(viewport, player, time_sec):
    try:
        max_hp = float(getattr(player, "max_hp", 100)) or 1.0
        cur_hp = float(getattr(player, "hp", 0))
    except Exception:
        return
    if cur_hp <= 0:
        return
    ratio = cur_hp / max_hp
    if ratio > LOW_HP_THRESHOLD:
        return

    severity = 1.0 - (ratio / LOW_HP_THRESHOLD)
    pulse = (math.sin(time_sec * LOW_HP_PULSE_SPEED) + 1.0) * 0.5

    alpha = LOW_HP_MIN_ALPHA + int(
        (LOW_HP_MAX_ALPHA - LOW_HP_MIN_ALPHA) * (0.5 * severity + 0.5 * pulse)
    )
    alpha = max(0, min(200, alpha))

    vw, vh = viewport.get_size()
    vignette = get_hurt_vignette(vw, vh)
    vignette.set_alpha(alpha)
    viewport.blit(vignette, (0, 0))


def fade_to_black(screen, duration_ms=350, target_color=(0, 0, 0)):
    clock = pygame.time.Clock()
    screen_w, screen_h = screen.get_size()
    snapshot = screen.copy()

    start = pygame.time.get_ticks()
    while True:
        elapsed = pygame.time.get_ticks() - start
        if elapsed >= duration_ms:
            break
        clock.tick(60)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if elapsed > 150 and (
                event.type == pygame.KEYDOWN or
                (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1)
            ):
                elapsed = duration_ms
                break

        progress = min(1.0, elapsed / float(duration_ms))
        alpha = int(255 * progress)

        screen.blit(snapshot, (0, 0))
        fade = pygame.Surface((screen_w, screen_h))
        fade.fill(target_color)
        fade.set_alpha(alpha)
        screen.blit(fade, (0, 0))
        pygame.display.flip()

    screen.fill(target_color)
    pygame.display.flip()


def play_battle_end_banner(screen, player_won, duration_sec=2.2):
    clock = pygame.time.Clock()
    screen_w, screen_h = screen.get_size()

    try:
        if player_won:
            play_battle_win_sfx()
        else:
            play_battle_lose_sfx()
    except Exception as e:
        print(f"[Battle] end banner SFX failed: {e}")

    font_path = os.path.join(PROJECT_ROOT, "asset", "font", "TheGothicRite.otf")
    if os.path.exists(font_path):
        font_big = pygame.font.Font(font_path, 130)
        font_sub = pygame.font.Font(font_path, 38)
    else:
        font_big = pygame.font.SysFont("Georgia", 130, bold=True)
        font_sub = pygame.font.SysFont("Georgia", 38, bold=True)

    if player_won:
        big_text   = "YOU WIN"
        big_color  = (255, 215, 0)
        sub_text   = "VICTORY"
        sub_color  = (255, 230, 150)
    else:
        big_text   = "YOU LOSE"
        big_color  = (220, 40, 40)
        sub_text   = "GAME OVER"
        sub_color  = (240, 150, 150)

    big_base = font_big.render(big_text, True, big_color)
    big_out  = font_big.render(big_text, True, (0, 0, 0))
    sub_surf = font_sub.render(sub_text, True, sub_color)

    snapshot = screen.copy()

    start = pygame.time.get_ticks()
    while True:
        elapsed = (pygame.time.get_ticks() - start) / 1000.0
        if elapsed >= duration_sec:
            break

        clock.tick(60)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if elapsed > 0.6 and (
                event.type == pygame.KEYDOWN or
                (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1)
            ):
                return

        t = elapsed / duration_sec

        screen.blit(snapshot, (0, 0))
        dim = int(215 * min(1.0, t / 0.20))
        overlay = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, dim))
        screen.blit(overlay, (0, 0))

        if t < 0.10:
            scale = 0.30 + 0.90 * (t / 0.10)
        elif t < 0.20:
            scale = 1.20 - 0.20 * ((t - 0.10) / 0.10)
        else:
            scale = 1.0

        if t > 0.85:
            text_alpha = int(255 * max(0.0, 1.0 - (t - 0.85) / 0.15))
        else:
            text_alpha = 255
        text_alpha = max(0, min(255, text_alpha))

        if text_alpha > 0:
            bw = max(1, int(big_base.get_width() * scale))
            bh = max(1, int(big_base.get_height() * scale))
            big_scaled = pygame.transform.scale(big_base, (bw, bh))
            out_scaled = pygame.transform.scale(big_out, (bw, bh))
            big_scaled.set_alpha(text_alpha)
            out_scaled.set_alpha(text_alpha)

            cx = screen_w // 2
            cy = screen_h // 2 - 20

            for dx, dy in ((-4, 0), (4, 0), (0, -4), (0, 4),
                           (-4, -4), (4, -4), (-4, 4), (4, 4)):
                r = out_scaled.get_rect(center=(cx + dx, cy + dy))
                screen.blit(out_scaled, r)
            r = big_scaled.get_rect(center=(cx, cy))
            screen.blit(big_scaled, r)

            if t > 0.25:
                sub_alpha = min(255, int(255 * (t - 0.25) / 0.20))
                sub_alpha = min(sub_alpha, text_alpha)
                sub_surf.set_alpha(sub_alpha)
                screen.blit(sub_surf,
                            sub_surf.get_rect(center=(cx, cy + 120)))

        pygame.display.flip()