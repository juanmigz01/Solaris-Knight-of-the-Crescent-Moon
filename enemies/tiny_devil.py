
import os
import sys
import random
import pygame

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from enemies.enemy import Enemy
from enemies.enemy_element import ElementComponent


class TinyDevil(Enemy):
    DEATH_NAMES = ("death", "dead", "die", "defeat")
    DEATH_FRAME_TIME = 0.18

    MAIN_ELEMENT = "Fire"
    SECONDARY_ELEMENT = "Earth"
    EARTH_RESISTANCE = 0.5

    DEMONIC_CLAW = {
        "name":      "Demonic Claw",
        "min_dmg":   5,
        "max_dmg":   7,
        "animation": "attack1",
        "hits":      3,
        "status":    None,
    }

    DEMONIC_SLASH = {
        "name":      "Demonic Slash",
        "min_dmg":   15,
        "max_dmg":   19,
        "animation": "attack2",
        "status_if_absent": [("burn", 4)],
    }

    MOVE_TABLE = [
        (DEMONIC_CLAW,  0.55),
        (DEMONIC_SLASH, 0.45),
    ]

    def __init__(self, x=100, y=100, scale=2.0):
        super().__init__(
            x=x, y=y,
            max_hp=90,
            atk=10,
            defense=4,
            evade=0.07,
            detection_radius=120,
            scale=scale,
            name="Tiny Devil",
        )

        self.element = ElementComponent(self.MAIN_ELEMENT)
        self.secondary_element = self.SECONDARY_ELEMENT
        self.elemental_resistances = {self.SECONDARY_ELEMENT: self.EARTH_RESISTANCE}

        self.battle_scale = 4.0

        image_path = os.path.join("asset", "enemy_img", "small devil", "demon.png")
        json_path  = os.path.join("asset", "enemy_img", "small devil", "demon.json")

        self.load_spritesheet_and_json(image_path, json_path)
        self.set_animation("idle")
        self.anim_timer = 0.0

    def pick_enemy_move(self):
        roll = random.random()
        cumulative = 0.0
        for move, weight in self.MOVE_TABLE:
            cumulative += weight
            if roll <= cumulative:
                return dict(move)
        return dict(self.DEMONIC_CLAW)

    def _find_animation(self, names):
        for key in getattr(self, "animations", {}):
            if key.lower() in names:
                return key
        return None

    def _update_death(self, delta_time):
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

    def update(self, delta_time=0, player=None, **kwargs):
        if self.hp <= 0:
            self._update_death(delta_time)
            return
        super().update(delta_time=delta_time, player=player)