
import os
import sys
import json
import random
import pygame

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from enemies.enemy import Enemy
from enemies.enemy_element import ElementComponent
from Modules.char import add_outline


_ANIM_ALIASES = {
    "attk1": "attack1",
    "attk2": "attack2",
    "attk3": "attack3",
    "atk1":  "attack1",
    "atk2":  "attack2",
    "atk3":  "attack3",
    "idledown": "idle",
    "idle_down": "idle",
    "speical": "special",
    "spcl": "special",
    "atk": "attack1",
}


class Gorgona(Enemy):
    DEATH_NAMES = ("death", "dead", "die", "defeat")
    DEATH_FRAME_TIME = 0.18

    ALLOWED_WEAPONS = (
        "the_suns_ray",
        "eclipsis_dagger",
        "crimson_petal_katana",
        "demon_blade",
    )

    PHASES = [
        {
            "name":        "Venom",
            "sprite_stem": "1Gorgona",
            "element":     "Wind",
            "bar_hp":      500,
            "atk":         22,
            "def":         20,
            "evade":       0.05,
        },
        {
            "name":        "Gilded",
            "sprite_stem": "2Gorgona",
            "element":     "Earth",
            "bar_hp":      600,
            "atk":         27,
            "def":         40,
            "evade":       0.05,
        },
        {
            "name":        "Eclipse",
            "sprite_stem": "3Gorgona",
            "element":     "Fire",
            "bar_hp":      770,
            "atk":         32,
            "def":         45,
            "evade":       0.05,
        },
    ]

    TAIL_WHIP = {
        "name":      "Tail Whip",
        "min_dmg":   10,
        "max_dmg":   14,
        "animation": "attack2",
        "status":    ("poison", 1),
    }
    GALE_SLAM = {
        "name":      "Gale Slam",
        "min_dmg":   13,
        "max_dmg":   16,
        "animation": "attack3",
    }
    CYCLONE_COIL = {
        "name":      "Cyclone Coil",
        "animation": "attack1",
        "self_buff": ("atk", 5),
    }

    QUAKE_SLAM = {
        "name":      "Quake Slam",
        "min_dmg":   15,
        "max_dmg":   18,
        "animation": "attack3",
    }
    SUNDER_WHIP = {
        "name":      "Sunder Whip",
        "min_dmg":   12,
        "max_dmg":   18,
        "animation": "attack2",
        "status":    ("weak", 2),
    }
    STONE_SKIN = {
        "name":      "Stone Skin",
        "animation": "attack1",
        "self_buff": ("defense", 5),
    }
    RADIANT_MEND = {
        "name":      "Radiant Mend",
        "animation": "attack1",
        "self_buff": ("defense", 3),
    }
    STONE_GAZE = {
        "name":      "Stone Gaze",
        "animation": "special",
        "status":    ("stun", 1),
    }

    RENDING_WHIP = {
        "name":      "Rending Whip",
        "min_dmg":   15,
        "max_dmg":   18,
        "animation": "attack2",
        "status":    ("bleed", 1),
    }
    INFERNO_SLAM = {
        "name":      "Inferno Slam",
        "min_dmg":   18,
        "max_dmg":   25,
        "animation": "attack3",
        "status":    ("burn", 1),
    }
    WRATH_COIL = {
        "name":      "Wrath Coil",
        "animation": "attack1",
        "self_buff": ("atk", 4),
    }
    ECLIPSE_GAZE = {
        "name":      "Eclipse Gaze",
        "min_dmg":   21,
        "max_dmg":   26,
        "animation": "special",
        "status":    ("bleed", 2),
        "status_if_absent": [("burn", 2)],
    }

    def __init__(self, x=0, y=0, scale=1.0):
        phase0 = self.PHASES[0]

        super().__init__(
            x=x, y=y,
            max_hp=phase0["bar_hp"],
            atk=phase0["atk"],
            defense=phase0["def"],
            evade=phase0["evade"],
            detection_radius=200,
            scale=scale,
            name="Gorgona",
        )

        self.is_boss = True
        self.battle_scale = 2.0

        self.allowed_weapons = self.ALLOWED_WEAPONS

        self.current_phase = 0
        self._turn_counter = 0
        self._phase1_cycle_idx = 0

        self.phase_anim_red  = [None, None, None]
        self.phase_anim_blue = [None, None, None]

        for i, phase in enumerate(self.PHASES):
            red, blue = self._load_phase_sheets(phase["sprite_stem"])
            self.phase_anim_red[i]  = red
            self.phase_anim_blue[i] = blue

        self._apply_phase(0)
        self.set_animation("idle")
        self.anim_timer = 0.0

    @property
    def phase_name(self):
        return self.PHASES[self.current_phase]["name"]

    @property
    def is_final_phase(self):
        return self.current_phase >= len(self.PHASES) - 1

    def try_advance_phase(self):
        if self.is_final_phase:
            return False
        self._apply_phase(self.current_phase + 1)
        self.set_animation("special")
        return True

    def try_self_heal(self, percent=0.10):
        heal_amt = int(self.max_hp * percent)
        before = self.hp
        self.hp = min(self.max_hp, self.hp + heal_amt)
        return self.hp - before

    def _load_phase_sheets(self, sprite_stem):
        base = os.path.join("asset", "enemy_img", "Gorgona")
        image_path = os.path.join(base, f"{sprite_stem}.png")
        json_path  = os.path.join(base, f"{sprite_stem}.json")

        if not os.path.exists(image_path) or not os.path.exists(json_path):
            alt_img  = os.path.join(PROJECT_ROOT, image_path)
            alt_json = os.path.join(PROJECT_ROOT, json_path)
            if os.path.exists(alt_img):
                image_path = alt_img
            if os.path.exists(alt_json):
                json_path = alt_json

        if not os.path.exists(image_path) or not os.path.exists(json_path):
            print(f"[Gorgona] missing sprite sheet: {sprite_stem}")
            return {}, {}

        try:
            sheet = pygame.image.load(image_path).convert_alpha()
            with open(json_path, "r") as f:
                data = json.load(f)

            frames_info = data.get("frames", {})
            frame_list = (list(frames_info.values())
                          if isinstance(frames_info, dict) else frames_info)

            raw = []
            for entry in frame_list:
                fd = entry.get("frame", {})
                fx, fy = fd.get("x", 0), fd.get("y", 0)
                fw, fh = fd.get("w", 128), fd.get("h", 128)
                sub = sheet.subsurface(pygame.Rect(fx, fy, fw, fh))
                scaled = pygame.transform.scale(
                    sub, (int(fw * self.scale), int(fh * self.scale)))
                raw.append(scaled)

            tags = data.get("meta", {}).get("frameTags", [])

            def _build(color):
                s = {}
                for tag in tags:
                    name = self.normalize_name(tag.get("name", "idle"))
                    start = tag.get("from", 0)
                    end = tag.get("to", 0)
                    s[name] = [add_outline(raw[i], color=color)
                               for i in range(start, end + 1)
                               if i < len(raw)]

                for src, dst in _ANIM_ALIASES.items():
                    if src in s and dst not in s:
                        s[dst] = s[src]

                if "idle" not in s and s:
                    s["idle"] = s[list(s.keys())[0]]
                return s

            red  = _build(self.outline_color)
            blue = _build(self.STUN_OUTLINE_COLOR)

            return red, blue

        except Exception as e:
            print(f"[Gorgona] failed loading {sprite_stem}: {e}")
            return {}, {}

    def _apply_phase(self, idx):
        data = self.PHASES[idx]
        self.current_phase = idx

        self.max_hp  = data["bar_hp"]
        self.hp      = data["bar_hp"]
        self.atk     = data["atk"]
        self.defense = data["def"]
        self.evade   = data["evade"]
        self.element = ElementComponent(data["element"])

        self._anim_red  = self.phase_anim_red[idx]
        self._anim_blue = self.phase_anim_blue[idx]
        self.animations = self._anim_blue if self.is_stunned else self._anim_red

        self._turn_counter = 0
        self._phase1_cycle_idx = 0

        frames = self.animations.get(self.current_animation, [])
        if frames:
            self.frame_index = min(self.frame_index, len(frames) - 1)
            self.image = frames[self.frame_index]
        elif "idle" in self.animations and self.animations["idle"]:
            self.image = self.animations["idle"][0]

    def pick_enemy_move(self):
        self._turn_counter += 1
        hp_ratio = self.hp / max(1, self.max_hp)

        if self.current_phase == 0:
            return self._pick_phase1()
        if self.current_phase == 1:
            return self._pick_phase2(hp_ratio)
        return self._pick_phase3(hp_ratio)

    def _pick_phase1(self):
        cycle = [self.TAIL_WHIP, self.TAIL_WHIP,
                 self.GALE_SLAM, self.CYCLONE_COIL]
        move = cycle[self._phase1_cycle_idx % len(cycle)]
        self._phase1_cycle_idx += 1
        return dict(move)

    def _pick_phase2(self, hp_ratio):
        if hp_ratio <= 0.30:
            if self._turn_counter % 2 == 0:
                return dict(self.STONE_SKIN)
            return dict(self.RADIANT_MEND)

        if hp_ratio <= 0.05 or self._turn_counter % 8 == 0:
            return dict(self.STONE_GAZE)

        if random.random() < 0.30:
            return dict(self.SUNDER_WHIP)
        return dict(self.QUAKE_SLAM)

    def _pick_phase3(self, hp_ratio):
        if hp_ratio <= 0.20 or self._turn_counter % 10 == 0:
            return dict(self.ECLIPSE_GAZE)

        if random.random() < 0.20:
            return dict(self.WRATH_COIL)

        if self._turn_counter % 2 == 0:
            return dict(self.RENDING_WHIP)
        return dict(self.INFERNO_SLAM)

    def _find_animation(self, names):
        for key in getattr(self, "animations", {}):
            if key.lower() in names:
                return key
        return None

    def _update_death(self, delta_time):
        if not self.is_final_phase:
            if self.current_animation != "idle":
                self.set_animation("idle")
            return

        death_key = self._find_animation(self.DEATH_NAMES)
        if death_key is None:
            return

        frames = self.animations.get(death_key, [])
        if not frames:
            return

        if self.current_animation != death_key:
            self.set_animation(death_key)
            self.frame_index = 0
            self.anim_timer = 0.0
        elif self.frame_index < len(frames) - 1:
            self.anim_timer += delta_time
            if self.anim_timer >= self.DEATH_FRAME_TIME:
                self.anim_timer = 0.0
                self.frame_index += 1

        self.image = frames[min(self.frame_index, len(frames) - 1)]

    def update(self, delta_time=0.016, player=None, **kwargs):
        if self.hp <= 0:
            self._update_death(delta_time)
            self.rect = self.image.get_rect(midbottom=(int(self.x), int(self.y)))
            self.hitbox = pygame.Rect(self.rect.x, self.rect.y,
                                      self.rect.width, self.rect.height)
            return
        super().update(delta_time=delta_time, player=player)