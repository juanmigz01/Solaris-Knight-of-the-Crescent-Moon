
import os
import sys
import math
import random
import pygame

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


SPRITE_FOLDERS = [
    os.path.join("asset", "deco_img", "particles"),
    os.path.join("asset", "deco_img"),
]


SPRITE_PRESCALE = 1.5


INTENSITY_COUNTS = {
    "off":    0,
    "low":    30,
    "medium": 70,
    "high":   140,
}

FIREFLY_INTENSITY_COUNTS = {
    "off":    0,
    "low":    20,
    "medium": 45,
    "high":   80,
}

RED_FALL_INTENSITY_COUNTS = {
    "off":    0,
    "low":    25,
    "medium": 55,
    "high":   95,
}

BLUE_FALL_INTENSITY_COUNTS = {
    "off":    0,
    "low":    25,
    "medium": 55,
    "high":   95,
}

INTENSITY_ORDER = ["off", "low", "medium", "high"]

REFERENCE_W = 1280
REFERENCE_H = 720


def find_leaf_sprite_paths(names=("mparticle",)):
    names_lower = tuple(n.lower() for n in names)
    paths = []
    for rel_folder in SPRITE_FOLDERS:
        folder = os.path.join(PROJECT_ROOT, rel_folder)
        if not os.path.isdir(folder):
            continue
        for fname in sorted(os.listdir(folder)):
            lower = fname.lower()
            if not lower.endswith(".png"):
                continue
            if not any(n in lower for n in names_lower):
                continue
            paths.append(os.path.join(folder, fname))
    return paths


_FIREFLY_DOT_CACHE = {}


def _get_firefly_dot(size):
    if size not in _FIREFLY_DOT_CACHE:
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        surf.fill((255, 255, 255, 255))
        _FIREFLY_DOT_CACHE[size] = surf
    return _FIREFLY_DOT_CACHE[size]


_DOT_CACHE = {}


def _get_dot(size, color):
    key = (size, color)
    if key not in _DOT_CACHE:
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        surf.fill((color[0], color[1], color[2], 255))
        _DOT_CACHE[key] = surf
    return _DOT_CACHE[key]


def _get_red_dot(size):
    return _get_dot(size, (230, 55, 45))


def _get_blue_dot(size):
    return _get_dot(size, (90, 180, 255))


class Leaf:


    def __init__(self, sprites, world_w, world_h, initial=True):
        self.sprites = sprites
        self.world_w = world_w
        self.world_h = world_h
        self.reset(initial=initial)

    def reset(self, initial=False):
        if initial:
            self.y = random.uniform(-50, self.world_h)
        else:
            self.y = random.uniform(-120, -20)

        self.base_x = random.uniform(-40, self.world_w + 40)
        self.x = self.base_x

        self.vy = random.uniform(18, 42)
        self.sway_amp = random.uniform(10, 26)
        self.sway_freq = random.uniform(0.4, 1.1)
        self.sway_phase = random.uniform(0, math.tau)

        self.frame_index = random.randint(0, max(0, len(self.sprites) - 1))
        self.frame_timer = 0.0
        self.frame_speed = random.uniform(0.10, 0.22)

        self.scale = random.uniform(0.70, 1.15)
        self.angle = random.uniform(0, 360)
        self.rotation_speed = random.uniform(-45, 45)

    def update(self, dt, t):
        self.y += self.vy * dt

        offset = math.sin(t * self.sway_freq + self.sway_phase) * self.sway_amp
        self.x = self.base_x + offset

        self.angle = (self.angle + self.rotation_speed * dt) % 360

        if self.sprites:
            self.frame_timer += dt
            if self.frame_timer >= self.frame_speed:
                self.frame_timer = 0.0
                self.frame_index = (self.frame_index + 1) % len(self.sprites)

        if self.y > self.world_h + 60:
            self.reset(initial=False)

    def is_outside(self, view_rect, margin=80):
        if view_rect is None:
            return False
        return (self.x + margin < view_rect.left or
                self.x - margin > view_rect.right or
                self.y + margin < view_rect.top or
                self.y - margin > view_rect.bottom)

    def draw(self, surface):
        if not self.sprites:
            return
        img = self.sprites[self.frame_index]

        if abs(self.scale - 1.0) > 0.01:
            w = max(1, int(img.get_width() * self.scale))
            h = max(1, int(img.get_height() * self.scale))
            img = pygame.transform.scale(img, (w, h))

        if abs(self.angle) > 0.5:
            img = pygame.transform.rotate(img, self.angle)

        rect = img.get_rect(center=(int(self.x), int(self.y)))
        surface.blit(img, rect)


class ParticleSystem:


    def __init__(self, world_w=1280, world_h=1088, intensity="medium",
                 sprite_names=("mparticle",), outline_color=None):
        self.world_w = world_w
        self.world_h = world_h
        self.intensity = intensity
        self.sprite_names = sprite_names
        self.outline_color = outline_color
        self.sprites = self._load_sprites()
        self.leaves = []
        self.time = 0.0

        area_ratio = ((self.world_w * self.world_h)
                      / float(REFERENCE_W * REFERENCE_H))
        self._scaled_counts = {
            key: int(round(base * area_ratio))
            for key, base in INTENSITY_COUNTS.items()
        }
        if self._scaled_counts["medium"] < 1:
            self._scaled_counts["medium"] = 1

        self._populate()

    def _load_sprites(self):
        paths = find_leaf_sprite_paths(names=self.sprite_names)

        if not paths:
            alt = ("oparticle",) if "mparticle" in self.sprite_names else ("mparticle",)
            paths = find_leaf_sprite_paths(names=alt)
            if paths:
                print(f"[Particles] No '{self.sprite_names}' sprites; "
                      f"using fallback set '{alt}'.")

        sprites = []
        for path in paths:
            try:
                img = pygame.image.load(path).convert_alpha()
                if SPRITE_PRESCALE and abs(SPRITE_PRESCALE - 1.0) > 0.01:
                    new_w = max(1, int(img.get_width() * SPRITE_PRESCALE))
                    new_h = max(1, int(img.get_height() * SPRITE_PRESCALE))
                    img = pygame.transform.scale(img, (new_w, new_h))

                if self.outline_color is not None:
                    try:
                        from Modules.char import add_outline
                        img = add_outline(img, color=self.outline_color)
                    except Exception as e:
                        print(f"[Particles] outline failed for "
                              f"{os.path.basename(path)}: {e}")

                sprites.append(img)
            except Exception as e:
                print(f"[Particles] Failed to load {os.path.basename(path)}: {e}")

        if not sprites:
            surf = pygame.Surface((6, 6), pygame.SRCALPHA)
            pygame.draw.rect(surf, (220, 130, 70, 210), surf.get_rect(),
                             border_radius=2)
            if self.outline_color is not None:
                try:
                    from Modules.char import add_outline
                    surf = add_outline(surf, color=self.outline_color)
                except Exception:
                    pass
            sprites.append(surf)
            print("[Particles] No leaf sprites found. Using fallback square. "
                  "Looked in: " + ", ".join(SPRITE_FOLDERS))

        return sprites

    def _target_count(self):
        return self._scaled_counts.get(self.intensity,
                                        self._scaled_counts["medium"])

    def _populate(self):
        target = self._target_count()
        while len(self.leaves) < target:
            self.leaves.append(
                Leaf(self.sprites, self.world_w, self.world_h, initial=True)
            )
        while len(self.leaves) > target:
            self.leaves.pop()

    def set_intensity(self, intensity):
        if intensity not in INTENSITY_COUNTS:
            intensity = "medium"
        self.intensity = intensity
        self._populate()

    def update(self, dt):
        if not self.leaves:
            return
        dt = min(dt, 0.05)
        self.time += dt
        for leaf in self.leaves:
            leaf.update(dt, self.time)

    def update_at_fixed_rate(self):
        self.update(1.0 / 60.0)

    def draw(self, surface, view_rect=None):
        if not self.leaves:
            return
        for leaf in self.leaves:
            if leaf.is_outside(view_rect):
                continue
            leaf.draw(surface)


class Firefly:

    def __init__(self, world_w, world_h, initial=True):
        self.world_w = world_w
        self.world_h = world_h
        self.reset(initial=initial)

    def reset(self, initial=False):
        self.home_x = random.uniform(20, self.world_w - 20)
        self.home_y = random.uniform(20, self.world_h - 20)

        self.wander_amp_x = random.uniform(10, 32)
        self.wander_amp_y = random.uniform(8, 24)
        self.wander_freq_x = random.uniform(0.08, 0.22)
        self.wander_freq_y = random.uniform(0.10, 0.24)
        self.wander_phase_x = random.uniform(0, math.tau)
        self.wander_phase_y = random.uniform(0, math.tau)

        self.pulse_speed = random.uniform(1.4, 2.6)
        self.pulse_phase = random.uniform(0, math.tau)
        self.max_alpha = random.randint(220, 255)

        self.dot_size = random.choice((3, 4, 4, 5))
        self.sprite = _get_firefly_dot(self.dot_size)

        self.x = self.home_x
        self.y = self.home_y

    def update(self, dt, t):
        self.x = self.home_x + math.sin(
            t * self.wander_freq_x * math.tau + self.wander_phase_x
        ) * self.wander_amp_x

        self.y = self.home_y + math.sin(
            t * self.wander_freq_y * math.tau + self.wander_phase_y
        ) * self.wander_amp_y

    def is_outside(self, view_rect, margin=40):
        if view_rect is None:
            return False
        return (self.x + margin < view_rect.left or
                self.x - margin > view_rect.right or
                self.y + margin < view_rect.top or
                self.y - margin > view_rect.bottom)

    def _current_alpha(self, t):
        raw = (math.sin(t * self.pulse_speed + self.pulse_phase) + 1.0) * 0.5
        shaped = 0.20 + 0.80 * (raw ** 1.6)
        return int(shaped * self.max_alpha)

    def draw(self, surface, t):
        alpha = self._current_alpha(t)
        if alpha <= 0:
            return
        self.sprite.set_alpha(alpha)
        rect = self.sprite.get_rect(center=(int(self.x), int(self.y)))
        surface.blit(self.sprite, rect)


class FireflySystem:

    def __init__(self, world_w=1280, world_h=1088, intensity="medium"):
        self.world_w = world_w
        self.world_h = world_h
        self.intensity = intensity
        self.fireflies = []
        self.time = 0.0

        area_ratio = ((self.world_w * self.world_h)
                      / float(REFERENCE_W * REFERENCE_H))
        self._scaled_counts = {
            key: int(round(base * area_ratio))
            for key, base in FIREFLY_INTENSITY_COUNTS.items()
        }
        if self._scaled_counts["medium"] < 1:
            self._scaled_counts["medium"] = 1

        self._populate()

    def _target_count(self):
        return self._scaled_counts.get(self.intensity,
                                        self._scaled_counts["medium"])

    def _populate(self):
        target = self._target_count()
        while len(self.fireflies) < target:
            self.fireflies.append(
                Firefly(self.world_w, self.world_h, initial=True)
            )
        while len(self.fireflies) > target:
            self.fireflies.pop()

    def set_intensity(self, intensity):
        if intensity not in FIREFLY_INTENSITY_COUNTS:
            intensity = "medium"
        self.intensity = intensity
        self._populate()

    def update(self, dt):
        if not self.fireflies:
            return
        dt = min(dt, 0.05)
        self.time += dt
        for f in self.fireflies:
            f.update(dt, self.time)

    def draw(self, surface, view_rect=None):
        if not self.fireflies:
            return
        for f in self.fireflies:
            if f.is_outside(view_rect):
                continue
            f.draw(surface, self.time)


class RedFallParticle:

    def __init__(self, world_w, world_h, initial=True):
        self.world_w = world_w
        self.world_h = world_h
        self.reset(initial=initial)

    def reset(self, initial=False):
        self.base_x = random.uniform(20, self.world_w - 20)
        self.x = self.base_x

        if initial:
            self.y = random.uniform(-40, self.world_h)
        else:
            self.y = random.uniform(-120, -30)

        self.fall_speed = random.uniform(35, 95)
        self.sway_amp = random.uniform(5, 16)
        self.sway_freq = random.uniform(0.6, 1.4)
        self.sway_phase = random.uniform(0, math.tau)

        self.pulse_speed = random.uniform(1.6, 3.2)
        self.pulse_phase = random.uniform(0, math.tau)
        self.max_alpha = random.randint(150, 235)

        self.dot_size = random.choice((2, 3, 3, 4))
        self.sprite = _get_red_dot(self.dot_size)

        self.time = 0.0

    def update(self, dt):
        self.time += dt
        self.y += self.fall_speed * dt
        offset = math.sin(
            self.time * self.sway_freq * math.tau + self.sway_phase
        ) * self.sway_amp
        self.x = self.base_x + offset

        if self.y > self.world_h + 50:
            self.reset(initial=False)

    def is_outside(self, view_rect, margin=40):
        if view_rect is None:
            return False
        return (self.x + margin < view_rect.left or
                self.x - margin > view_rect.right or
                self.y + margin < view_rect.top or
                self.y - margin > view_rect.bottom)

    def _current_alpha(self):
        raw = (math.sin(self.time * self.pulse_speed + self.pulse_phase)
               + 1.0) * 0.5
        shaped = 0.35 + 0.65 * raw
        return int(shaped * self.max_alpha)

    def draw(self, surface):
        alpha = self._current_alpha()
        if alpha <= 0:
            return
        self.sprite.set_alpha(alpha)
        rect = self.sprite.get_rect(center=(int(self.x), int(self.y)))
        surface.blit(self.sprite, rect)


class RedFallSystem:

    def __init__(self, world_w=1280, world_h=1088, intensity="medium"):
        self.world_w = world_w
        self.world_h = world_h
        self.intensity = intensity
        self.particles = []

        area_ratio = ((self.world_w * self.world_h)
                      / float(REFERENCE_W * REFERENCE_H))
        self._scaled_counts = {
            key: int(round(base * area_ratio))
            for key, base in RED_FALL_INTENSITY_COUNTS.items()
        }
        if self._scaled_counts["medium"] < 1:
            self._scaled_counts["medium"] = 1

        self._populate()

    def _target_count(self):
        return self._scaled_counts.get(self.intensity,
                                        self._scaled_counts["medium"])

    def _populate(self):
        target = self._target_count()
        while len(self.particles) < target:
            self.particles.append(
                RedFallParticle(self.world_w, self.world_h, initial=True)
            )
        while len(self.particles) > target:
            self.particles.pop()

    def set_intensity(self, intensity):
        if intensity not in RED_FALL_INTENSITY_COUNTS:
            intensity = "medium"
        self.intensity = intensity
        self._populate()

    def update(self, dt):
        if not self.particles:
            return
        dt = min(dt, 0.05)
        for p in self.particles:
            p.update(dt)

    def draw(self, surface, view_rect=None):
        if not self.particles:
            return
        for p in self.particles:
            if p.is_outside(view_rect):
                continue
            p.draw(surface)


class BlueFallParticle:

    def __init__(self, world_w, world_h, initial=True):
        self.world_w = world_w
        self.world_h = world_h
        self.reset(initial=initial)

    def reset(self, initial=False):
        self.base_x = random.uniform(20, self.world_w - 20)
        self.x = self.base_x

        if initial:
            self.y = random.uniform(-40, self.world_h)
        else:
            self.y = random.uniform(-120, -30)

        self.fall_speed = random.uniform(35, 95)
        self.sway_amp = random.uniform(5, 16)
        self.sway_freq = random.uniform(0.6, 1.4)
        self.sway_phase = random.uniform(0, math.tau)

        self.pulse_speed = random.uniform(1.6, 3.2)
        self.pulse_phase = random.uniform(0, math.tau)
        self.max_alpha = random.randint(150, 235)

        self.dot_size = random.choice((2, 3, 3, 4))
        self.sprite = _get_blue_dot(self.dot_size)

        self.time = 0.0

    def update(self, dt):
        self.time += dt
        self.y += self.fall_speed * dt
        offset = math.sin(
            self.time * self.sway_freq * math.tau + self.sway_phase
        ) * self.sway_amp
        self.x = self.base_x + offset

        if self.y > self.world_h + 50:
            self.reset(initial=False)

    def is_outside(self, view_rect, margin=40):
        if view_rect is None:
            return False
        return (self.x + margin < view_rect.left or
                self.x - margin > view_rect.right or
                self.y + margin < view_rect.top or
                self.y - margin > view_rect.bottom)

    def _current_alpha(self):
        raw = (math.sin(self.time * self.pulse_speed + self.pulse_phase)
               + 1.0) * 0.5
        shaped = 0.35 + 0.65 * raw
        return int(shaped * self.max_alpha)

    def draw(self, surface):
        alpha = self._current_alpha()
        if alpha <= 0:
            return
        self.sprite.set_alpha(alpha)
        rect = self.sprite.get_rect(center=(int(self.x), int(self.y)))
        surface.blit(self.sprite, rect)


class BlueFallSystem:

    def __init__(self, world_w=1280, world_h=1088, intensity="medium"):
        self.world_w = world_w
        self.world_h = world_h
        self.intensity = intensity
        self.particles = []

        area_ratio = ((self.world_w * self.world_h)
                      / float(REFERENCE_W * REFERENCE_H))
        self._scaled_counts = {
            key: int(round(base * area_ratio))
            for key, base in BLUE_FALL_INTENSITY_COUNTS.items()
        }
        if self._scaled_counts["medium"] < 1:
            self._scaled_counts["medium"] = 1

        self._populate()

    def _target_count(self):
        return self._scaled_counts.get(self.intensity,
                                        self._scaled_counts["medium"])

    def _populate(self):
        target = self._target_count()
        while len(self.particles) < target:
            self.particles.append(
                BlueFallParticle(self.world_w, self.world_h, initial=True)
            )
        while len(self.particles) > target:
            self.particles.pop()

    def set_intensity(self, intensity):
        if intensity not in BLUE_FALL_INTENSITY_COUNTS:
            intensity = "medium"
        self.intensity = intensity
        self._populate()

    def update(self, dt):
        if not self.particles:
            return
        dt = min(dt, 0.05)
        for p in self.particles:
            p.update(dt)

    def draw(self, surface, view_rect=None):
        if not self.particles:
            return
        for p in self.particles:
            if p.is_outside(view_rect):
                continue
            p.draw(surface)


class ParticleBundle:

    def __init__(self, *systems):
        self.systems = [s for s in systems if s is not None]
        self.intensity = "medium"

    def update(self, dt):
        for s in self.systems:
            s.update(dt)

    def draw(self, surface, view_rect=None):
        for s in self.systems:
            s.draw(surface, view_rect=view_rect)

    def set_intensity(self, intensity):
        self.intensity = intensity
        for s in self.systems:
            if hasattr(s, "set_intensity"):
                s.set_intensity(intensity)


def make_midnight_overlay(w, h, base_alpha=35, edge_alpha=150):
    small_w, small_h = 320, 180
    small = pygame.Surface((small_w, small_h), pygame.SRCALPHA)
    cx, cy = small_w / 2.0, small_h / 2.0
    max_dist = math.hypot(cx, cy)

    for y in range(small_h):
        for x in range(small_w):
            d = math.hypot(x - cx, y - cy) / max_dist
            t = max(0.0, (d - 0.35) / 0.65)
            edge = int(edge_alpha * min(1.0, t))
            alpha = min(220, base_alpha + edge)
            small.set_at((x, y), (8, 0, 20, alpha))

    return pygame.transform.smoothscale(small, (w, h))