
import os
import sys
import random
import pygame

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from enemies.enemy import Enemy
from enemies.enemy_element import ElementComponent


class TinyOrc(Enemy):
    DEATH_NAMES = ("death", "dead", "die", "defeat")
    DEATH_FRAME_TIME = 0.18

    CLUB_SWING = {
        "name":      "Club Swing",
        "min_dmg":   10,
        "max_dmg":   15,
        "animation": "attack1",
        "status":    None,
    }

    ELEMENT_SKILLS = {
        "Fire": {
            "name":      "Kindling Toss",
            "min_dmg":   15,
            "max_dmg":   15,
            "animation": "attack2",
            "status":    ("burn", 4),
        },
        "Earth": {
            "name":      "Mud-Bomb",
            "min_dmg":   16,
            "max_dmg":   16,
            "animation": "attack2",
            "status":    None,
        },
        "Water": {
            "name":      "Geyser Spit",
            "min_dmg":   16,
            "max_dmg":   16,
            "animation": "attack2",
            "status":    None,
        },
        "Wind": {
            "name":      "Wind Slashes",
            "min_dmg":   14,
            "max_dmg":   16,
            "animation": "attack2",
            "status":    None,
        },
    }

    SKILL_CHANCE = 0.5

    def __init__(self, x=100, y=100, element="random", scale=2.0):
        super().__init__(
            x=x,
            y=y,
            max_hp=80,
            atk=9,
            defense=3,
            evade=0.08,
            detection_radius=110,
            scale=scale,
            name="Tiny Orc",
        )

        self.element = ElementComponent(element)

        image_path = os.path.join("asset", "enemy_img", "tiny orc", "Tiny_Orc.png")
        json_path = os.path.join("asset", "enemy_img", "tiny orc", "Tiny_Orc.json")

        self.load_spritesheet_and_json(image_path, json_path)
        self.set_animation("idle")
        self.anim_timer = 0.0

    def pick_enemy_move(self):
        element_type = getattr(self.element, "element_type", "Fire")

        if (random.random() < self.SKILL_CHANCE
                and element_type in self.ELEMENT_SKILLS):
            return dict(self.ELEMENT_SKILLS[element_type])

        return dict(self.CLUB_SWING)

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

    def perform_attack(self, target):
        self.set_animation("attack1")
        target_def = getattr(target, "defense", 0)
        damage = max(1, self.atk - target_def)
        if hasattr(target, "hp"):
            target.hp = max(0, target.hp - damage)
        target_name = getattr(target, "name", "Hero")
        return f"{self.name} swings its club at {target_name} for {damage} damage!"

    def elemental_attack(self, target):
        if not target:
            return 0
        target_element = getattr(target, "element",
                                 getattr(target, "elemental_defense", None))
        multiplier = self.element.get_damage_multiplier(target_element)
        raw_damage = int(self.atk * multiplier)
        target_defense = getattr(target, "defense", 0)
        final_damage = max(1, raw_damage - target_defense)
        if hasattr(target, "hp"):
            target.hp = max(0, target.hp - final_damage)
        return final_damage