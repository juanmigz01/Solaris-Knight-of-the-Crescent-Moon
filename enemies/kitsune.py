
import os
import sys
import random
import pygame

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from enemies.enemy import Enemy
from enemies.enemy_element import ElementComponent


class Kitsune(Enemy):
    DEATH_NAMES = ("death", "dead", "die", "defeat")
    DEATH_FRAME_TIME = 0.18

    MAIN_ELEMENT = "Fire"

    AZURE_SPLASH = {
        "name":      "Azure Splash",
        "min_dmg":   8,
        "max_dmg":   11,
        "animation": "attack1",
        "hits":      2,
        "status":    ("burn", 2),
    }

    AZURE_FREEZE = {
        "name":      "Azure Freeze",
        "min_dmg":   15,
        "max_dmg":   22,
        "animation": "attack2",
    }

    MOVE_TABLE = [
        (AZURE_SPLASH, 0.80),
        (AZURE_FREEZE, 0.20),
    ]

    INFERNAL_CLAW = AZURE_SPLASH
    INFERNAL_BALL = AZURE_FREEZE

    def __init__(self, x=100, y=100, scale=1.0):
        super().__init__(
            x=x, y=y,
            max_hp=130,
            atk=11,
            defense=4,
            evade=0.12,
            detection_radius=140,
            scale=scale,
            name="Kitsune",
        )

        self.element = ElementComponent(self.MAIN_ELEMENT)
        self.battle_scale = 1.7

        image_path = os.path.join("asset", "enemy_img", "Kitsune", "kitsune.png")
        json_path  = os.path.join("asset", "enemy_img", "Kitsune", "kitsune.json")

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
        return dict(self.AZURE_SPLASH)

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