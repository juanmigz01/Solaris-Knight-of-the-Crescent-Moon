# =====================================================================
# Enemy base class.
# ---------------------------------------------------------------------
# 17.9.26.x FIX:
#   * basic_attack() now uses the 17.9.19 % DEF multiplier
#     instead of the OLD flat "atk - defense" formula.
#     (Battle loop never calls this, but legacy previews do.)
# =====================================================================

import os
import sys
import math
import json
import pygame

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from Modules.char import add_outline


class Enemy:
    # Outline color applied to every sprite frame at load time.
    # All enemies default to RED. NPC subclasses (e.g. Wizard)
    # override this class attribute to WHITE.
    outline_color = (220, 40, 40, 255)

    # BATCH 17.9.13: outline used while the enemy is stunned.
    # The battle loop calls set_stunned(True/False) every frame
    # based on the enemy's StatusManager.
    STUN_OUTLINE_COLOR = (120, 200, 255, 255)

    def __init__(self, x=0, y=0, max_hp=100, atk=10, defense=5, evade=0.05,
                 detection_radius=110, scale=2.0, name="Base Enemy"):

        self.name = name
        self.x = float(x)
        self.y = float(y)
        self.scale = scale

        self.max_hp = max_hp
        self.hp = max_hp
        self.atk = atk
        self.defense = defense
        self.evade = evade
        self.detection_radius = detection_radius

        self.facing_right = True
        self.is_detected = False
        self.triggered_battle = False
        self.flee_cooldown = False

        self.animations = {}
        # BATCH 17.9.13: two parallel frame sets so we can swap
        # outline colour without regenerating sprites at runtime.
        self._anim_red = {}
        self._anim_blue = {}
        self.is_stunned = False

        self.current_animation = "idle"
        self.frame_index = 0
        self.animation_timer = 0.0
        self.animation_speed = 0.15

        default_size = int(32 * self.scale)
        self.image = pygame.Surface((default_size, default_size))
        self.image.fill((200, 50, 50))

        self.rect = self.image.get_rect(midbottom=(int(self.x), int(self.y)))
        self.hitbox = pygame.Rect(self.rect.x, self.rect.y, default_size, default_size)

    # -----------------------------------------------------------------
    # STUN OUTLINE SWAP
    # -----------------------------------------------------------------
    def set_stunned(self, on):
        """
        Swap the active sprite set between red and blue outlines.

        Called every frame by the battle loop. Cheap when the
        state hasn't changed (early return).
        """
        on = bool(on)
        if on == self.is_stunned:
            return

        self.is_stunned = on
        self.animations = self._anim_blue if on else self._anim_red

        # Refresh the current image immediately so the swap is
        # visible on this frame instead of the next animation tick.
        current_frames = self.animations.get(self.current_animation, [])
        if current_frames:
            self.frame_index = min(self.frame_index, len(current_frames) - 1)
            self.image = current_frames[self.frame_index]

    def normalize_name(self, name):
        clean = name.lower().replace(" ", "").replace("_", "").replace("-", "")
        if clean in ("attack01", "attack02", "attack03"):
            clean = clean.replace("0", "")
        return clean

    def load_spritesheet_and_json(self, image_path, json_path):

        if not os.path.exists(image_path) or not os.path.exists(json_path):
            alt_img = os.path.join(PROJECT_ROOT, image_path)
            alt_json = os.path.join(PROJECT_ROOT, json_path)
            if os.path.exists(alt_img):
                image_path = alt_img
            if os.path.exists(alt_json):
                json_path = alt_json

        if not os.path.exists(image_path) or not os.path.exists(json_path):
            print(f"[Warning] Asset files not found for '{self.name}': '{image_path}' or '{json_path}'")
            return

        try:
            sprite_sheet = pygame.image.load(image_path).convert_alpha()

            with open(json_path, "r") as json_file:
                json_data = json.load(json_file)

            # ---- 1) Collect RAW (un-outlined) scaled frames ----
            raw_unoutlined = []

            frames_info = json_data.get("frames", {})
            frame_list = list(frames_info.values()) if isinstance(frames_info, dict) else frames_info

            for frame_entry in frame_list:
                f_data = frame_entry.get("frame", {})
                fx, fy, fw, fh = f_data.get("x", 0), f_data.get("y", 0), f_data.get("w", 32), f_data.get("h", 32)

                sub_surface = sprite_sheet.subsurface(pygame.Rect(fx, fy, fw, fh))
                scaled_surface = pygame.transform.scale(sub_surface, (int(fw * self.scale), int(fh * self.scale)))
                raw_unoutlined.append(scaled_surface)

            frame_tags = json_data.get("meta", {}).get("frameTags", [])

            # ---- 2) Build BOTH outlined sets from the raw frames ----
            def _build_set(color):
                s = {}
                for tag in frame_tags:
                    tag_name = self.normalize_name(tag.get("name", "idle"))

                    start_index = tag.get("from", 0)
                    end_index = tag.get("to", 0)

                    frames = [
                        add_outline(raw_unoutlined[i], color=color)
                        for i in range(start_index, end_index + 1)
                        if i < len(raw_unoutlined)
                    ]

                    s[tag_name] = frames

                if not s and raw_unoutlined:
                    s["idle"] = [add_outline(f, color=color) for f in raw_unoutlined]

                if "idle" not in s and s:
                    first_key = list(s.keys())[0]
                    s["idle"] = s[first_key]

                return s

            self._anim_red  = _build_set(self.outline_color)
            self._anim_blue = _build_set(self.STUN_OUTLINE_COLOR)

            # Active set depends on stun state.
            self.animations = self._anim_blue if self.is_stunned else self._anim_red

            if "idle" in self.animations and self.animations["idle"]:
                self.image = self.animations["idle"][0]
                self.rect = self.image.get_rect(midbottom=(int(self.x), int(self.y)))
                self.hitbox = pygame.Rect(self.rect.x, self.rect.y, self.rect.width, self.rect.height)

        except Exception as error:
            print(f"[Error] Failed loading sprite sheet for '{self.name}': {error}")

    def set_animation(self, anim_name):
        clean_name = self.normalize_name(anim_name)

        if clean_name in self.animations and self.current_animation != clean_name:
            self.current_animation = clean_name
            self.frame_index = 0
            self.animation_timer = 0.0

    def is_player_detected(self, player):
        if not player:
            return False

        enemy_center_x = self.rect.centerx
        enemy_center_y = self.rect.centery

        player_rect = getattr(player, "hitbox", getattr(player, "rect", None))
        if player_rect:
            player_center_x = player_rect.centerx
            player_center_y = player_rect.centery
        else:
            player_center_x = getattr(player, "x", 0)
            player_center_y = getattr(player, "y", 0)

        distance = math.hypot(player_center_x - enemy_center_x, player_center_y - enemy_center_y)

        was_previously_detected = self.is_detected
        self.is_detected = distance <= self.detection_radius

        if self.flee_cooldown:
            outside_radius = distance > self.detection_radius * 1.3
            past_enemy = abs(player_center_x - enemy_center_x) > self.detection_radius
            if outside_radius or past_enemy:
                self.flee_cooldown = False

        if self.is_detected and not was_previously_detected and not self.flee_cooldown:
            self.triggered_battle = True

        return self.is_detected

    def reset_battle_trigger(self):
        self.triggered_battle = False

    def start_flee_cooldown(self):
        self.flee_cooldown = True
        self.triggered_battle = False
        self.is_detected = False

    # -----------------------------------------------------------------
    # LEGACY basic_attack
    # -----------------------------------------------------------------
    # BATCH 17.9.19 changed DEF from a flat subtraction to a %
    # multiplier. This legacy helper is only used by previews /
    # standalone tests, but we update it to match so damage
    # numbers stay consistent.
    #
    # Formula (matches battle_func._defense_multiplier):
    #     multiplier = 100 / (100 + defense * 1.5)
    #     damage     = round_half_up(atk * multiplier)
    #     floor at 1.
    # -----------------------------------------------------------------
    def basic_attack(self, target):
        if not target:
            return 0

        target_defense = getattr(target, "defense", 0)

        multiplier = 100.0 / (100.0 + target_defense * 1.5)
        damage = max(1, int(self.atk * multiplier + 0.5))

        if hasattr(target, "hp"):
            target.hp = max(0, target.hp - damage)

        return damage

    def update(self, delta_time=0.016, player=None):
        current_frame_list = self.animations.get(self.current_animation, [])

        if current_frame_list:
            self.animation_timer += delta_time
            if self.animation_timer >= self.animation_speed:
                self.animation_timer = 0.0
                self.frame_index = (self.frame_index + 1) % len(current_frame_list)
                self.image = current_frame_list[self.frame_index]

        self.rect = self.image.get_rect(midbottom=(int(self.x), int(self.y)))
        self.hitbox = pygame.Rect(self.rect.x, self.rect.y, self.rect.width, self.rect.height)

        if player is not None:
            if self.is_player_detected(player):
                player_x = getattr(player, "x", player.rect.centerx if hasattr(player, "rect") else 0)
                self.facing_right = player_x >= self.x

    def draw(self, surface):
        if self.image:
            image_to_draw = self.image

            if not self.facing_right:
                image_to_draw = pygame.transform.flip(image_to_draw, True, False)

            self.rect = image_to_draw.get_rect(midbottom=(int(self.x), int(self.y)))
            surface.blit(image_to_draw, self.rect)