import os
import sys
import math
import pygame

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from enemies.enemy import Enemy
from Modules.char import OUTLINE_COLOR_WHITE


class Wizard(Enemy):

    # NPC - white outline. Overrides Enemy's default red.
    outline_color = OUTLINE_COLOR_WHITE

    def __init__(self, x=100, y=100, scale=2.0):
        super().__init__(
            x=x,
            y=y,
            max_hp=999,
            atk=0,
            defense=99,
            evade=0.0,
            detection_radius=85,
            scale=scale,
            name="Wizard Oz"
        )

        self.dialogue_state = "PART_1"
        self.show_hitbox = False

        self.hb_w = 10
        self.hb_h = 6
        self.hb_offset_x = 0
        self.hb_offset_y = -68

        image_path = os.path.join("asset", "enemy_img", "Wizard", "Wizard.png")
        json_path = os.path.join("asset", "enemy_img", "Wizard", "Wizard.json")

        self.load_spritesheet_and_json(image_path, json_path)

        if "idledown" in self.animations and "idle" not in self.animations:
            self.animations["idle"] = self.animations["idledown"]

        self.set_animation("idle")

    @property
    def hitbox(self):

        hb_x = int(self.rect.centerx - (self.hb_w // 2)) + self.hb_offset_x
        hb_y = int(self.rect.bottom - self.hb_h + self.hb_offset_y)
        return pygame.Rect(hb_x, hb_y, self.hb_w, self.hb_h)

    @hitbox.setter
    def hitbox(self, value):

        pass

    def get_hitbox(self):
        return self.hitbox

    def can_interact(self, player):

        if not player:
            return False

        player_rect = getattr(player, "hitbox", getattr(player, "rect", None))
        if player_rect:
            px, py = player_rect.centerx, player_rect.centery
        else:
            px = getattr(player, "x", 0)
            py = getattr(player, "y", 0)

        dist = math.hypot(px - self.rect.centerx, py - (self.rect.centery - 10))
        return dist <= self.detection_radius

    def draw(self, surface):
        super().draw(surface)
        if self.show_hitbox:
            pygame.draw.rect(surface, (0, 255, 255), self.hitbox, 2)