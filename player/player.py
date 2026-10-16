import os
import sys
import json
import random
import pygame
import importlib

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
saves_cache_dir = os.path.join(PROJECT_ROOT, "saves", "pycache")
if hasattr(sys, "pycache_prefix"):
    sys.pycache_prefix = saves_cache_dir

from Modules.char import add_outline, OUTLINE_COLOR_WHITE

PLAYER_SCALE = 1.7

DEATH_ANIM_NAMES = ("death", "dead", "die", "defeat", "dying")
DEATH_ANIMATION_SPEED = 0.10

PLAYER_HITBOX_CONFIG = {
    "width": 20,
    "height": 38,
    "y_offset": -38,
}


DEFAULT_WALK_SFX = "walk.mp3"
DEFAULT_RUN_SFX  = "running.mp3"
DEFAULT_WALK_VOL = 0.40
DEFAULT_RUN_VOL  = 1.00


def _start_move_loop(key, name, volume):
    try:
        from Modules.sound_manager import game_manager
        game_manager.play_sfx_loop(key, name, volume=volume)
    except Exception as e:
        print(f"[Player] _start_move_loop({key}) failed: {e}")


def _stop_move_loop(key):
    try:
        from Modules.sound_manager import game_manager
        game_manager.stop_sfx(key)
    except Exception:
        pass


class Player:
    def __init__(self, x=640, y=360, name="Solaris", scale=PLAYER_SCALE):
        self.name = name
        self.x = x
        self.y = y

        self.spawn_x = x
        self.spawn_y = y

        self.scale = scale
        self.speed = 3
        self.sprint_speed = 6
        self.facing_right = True
        self.show_hitbox = False
        self.can_move = True

        self.hp = 150
        self.max_hp = 150
        self.atk = 5
        self.defense = 5
        self.elemental_attack = 0
        self.evade = 0.02
        self.element = "Neutral"

        self.walk_sfx_name   = DEFAULT_WALK_SFX
        self.run_sfx_name    = DEFAULT_RUN_SFX
        self.walk_sfx_volume = DEFAULT_WALK_VOL
        self.run_sfx_volume  = DEFAULT_RUN_VOL

        try:
            from classes.armory_item import Inventory
            self.inventory = Inventory(self)
        except ImportError:
            try:
                from Modules.armory_item import Inventory
                self.inventory = Inventory(self)
            except ImportError:
                self.inventory = None

        self.animations = {}
        self.current_animation = "idle"
        self.frame_index = 0
        self.animation_speed = 0.15
        self.frame_timer = 0.0

        self.load_animations()
        first_frame = self.animations.get(self.current_animation, [pygame.Surface((32, 32))])[0]
        self.rect = first_frame.get_rect(midbottom=(int(self.x), int(self.y)))

    def respawn(self):
        self.hp = self.max_hp
        self.x = self.spawn_x
        self.y = self.spawn_y
        self.facing_right = True
        self.frame_timer = 0.0
        self.set_animation("idle")
        _stop_move_loop("walk")
        _stop_move_loop("run")

    def is_dead(self):
        return self.hp <= 0

    def _find_death_animation(self):
        for key in self.animations:
            k = key.lower()
            if k in DEATH_ANIM_NAMES or any(w in k for w in ("death", "dead", "defeat")):
                return key
        return None

    def _update_death(self):
        death_key = self._find_death_animation()
        if death_key is None:
            return

        frames = self.animations[death_key]
        if not frames:
            return

        if self.current_animation != death_key:
            self.set_animation(death_key)
            self.frame_index = 0
            self.frame_timer = 0.0
        elif self.frame_index < len(frames) - 1:
            self.frame_timer += DEATH_ANIMATION_SPEED
            if self.frame_timer >= 1.0:
                self.frame_timer = 0.0
                self.frame_index += 1

        self.frame_index = min(self.frame_index, len(frames) - 1)
        self.rect = frames[self.frame_index].get_rect(midbottom=(int(self.x), int(self.y)))

    def get_hitbox(self):
        hb_w = PLAYER_HITBOX_CONFIG["width"]
        hb_h = PLAYER_HITBOX_CONFIG["height"]
        y_off = PLAYER_HITBOX_CONFIG["y_offset"]

        hb_x = int(self.x - (hb_w // 2))
        hb_y = int(self.y - hb_h + y_off)

        return pygame.Rect(hb_x, hb_y, hb_w, hb_h)

    def set_name(self, new_name):
        if new_name and new_name.strip() != "":
            self.name = new_name.strip()

    def normalize_name(self, name):
        clean = name.lower().replace(" ", "").replace("_", "").replace("-", "")
        if clean in ("attack01", "attack02", "attack03"):
            clean = clean.replace("0", "")
        return clean

    def load_animations(self):
        image_path = os.path.join("asset", "enemy_img", "Player", "DPlayer.png")
        json_path = os.path.join("asset", "enemy_img", "Player", "DPlayer.json")

        if not os.path.exists(image_path) or not os.path.exists(json_path):
            fallback = pygame.Surface((32, 48), pygame.SRCALPHA)
            pygame.draw.rect(fallback, (0, 200, 255), (0, 0, 32, 48))
            self.animations["idle"] = [fallback]
            self.animations["walk"] = [fallback]
            return

        sprite_sheet = pygame.image.load(image_path).convert_alpha()

        with open(json_path, "r") as fplayer:
            json_data = json.load(fplayer)

        raw_frames = []
        frames_info = json_data["frames"]

        for frame_key in frames_info:
            frame_data = frames_info[frame_key]["frame"]
            x, y, w, h = frame_data["x"], frame_data["y"], frame_data["w"], frame_data["h"]
            sub_surface = sprite_sheet.subsurface(pygame.Rect(x, y, w, h))
            scaled_surface = pygame.transform.scale(sub_surface, (int(w * self.scale), int(h * self.scale)))
            raw_frames.append(add_outline(scaled_surface, color=OUTLINE_COLOR_WHITE))

        frame_tags = json_data["meta"]["frameTags"]
        for tag in frame_tags:
            tag_name = self.normalize_name(tag["name"])
            start_index, end_index = tag["from"], tag["to"]
            tag_frame_list = [raw_frames[i] for i in range(start_index, end_index + 1) if i < len(raw_frames)]
            self.animations[tag_name] = tag_frame_list

    def perform_attack(self, target):
        self.set_animation("attack1")

        target_name = getattr(target, "name", "Enemy")
        target_evade = getattr(target, "evade", 0.0)

        if random.random() < target_evade:
            return f"{self.name} attacked, but {target_name} evaded!"

        weapon = getattr(self.inventory, "equipped_weapon", None) if self.inventory else None

        if weapon:
            w_phys, w_elem = weapon.get_damage()
            raw_phys = self.atk + w_phys
            raw_elem = self.elemental_attack + w_elem
            is_true_dmg = weapon.special_effects.get("true_damage", False)
            attack_name = weapon.name
            weapon_element = weapon.element
        else:
            raw_phys = self.atk
            raw_elem = self.elemental_attack
            is_true_dmg = False
            attack_name = "Unarmed Punch"
            weapon_element = self.element

        target_def = getattr(target, "defense", 0)

        if is_true_dmg:
            final_phys_dmg = raw_phys
            base_elem_dmg = raw_elem
        else:
            mult = 100.0 / (100.0 + max(0, target_def) * 1.5)
            final_phys_dmg = max(1, int(raw_phys * mult))
            base_elem_dmg = max(0, int(raw_elem * mult))

        multiplier = 1.0
        target_element = getattr(target, "element_component", None) or getattr(target, "element", None)

        if weapon_element not in ("Neutral", "True") and base_elem_dmg > 0:
            ElementComponent = None
            possible_modules = [
                "Modules.enemy_element_2",
                "classes.enemy_element_2",
                "enemy_element_2",
                "Modules.enemy_element",
                "classes.enemy_element"
            ]
            for mod_path in possible_modules:
                try:
                    mod = importlib.import_module(mod_path)
                    if hasattr(mod, "ElementComponent"):
                        ElementComponent = getattr(mod, "ElementComponent")
                        break
                except ImportError:
                    continue

            if ElementComponent is not None:
                attacker_elem_comp = ElementComponent(weapon_element)
                multiplier = attacker_elem_comp.get_damage_multiplier(target_element)

        final_elem_dmg = int(base_elem_dmg * multiplier + 0.5)
        total_damage = final_phys_dmg + final_elem_dmg

        if hasattr(target, "hp"):
            target.hp = max(0, target.hp - total_damage)

        eff_str = ""
        if multiplier > 1.0:
            eff_str = " (Super Effective! 1.5x)"
        elif multiplier < 1.0:
            eff_str = " (Not Very Effective... 0.5x)"

        return (f"{self.name} used {attack_name}! "
                f"Dealt {total_damage} Total Damage ({final_phys_dmg} Phys + {final_elem_dmg} Elem{eff_str}) to {target_name}!")

    def handle_input_and_collision(self, viewport_width=1280, viewport_height=720, obstacles=None):
        if not getattr(self, "can_move", True):
            _stop_move_loop("walk")
            _stop_move_loop("run")
            return

        if obstacles is None:
            obstacles = []

        keys = pygame.key.get_pressed()
        moving = False
        dx, dy = 0, 0

        is_sprinting = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        current_speed = self.sprint_speed if is_sprinting else self.speed

        if keys[pygame.K_w] or keys[pygame.K_UP]:
            dy -= 1
            moving = True
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            dy += 1
            moving = True
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            dx -= 1
            moving = True
            self.facing_right = False
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            dx += 1
            moving = True
            self.facing_right = True

        move_x, move_y = 0, 0
        if dx != 0 and dy != 0:
            move_x = dx * current_speed * 0.70710678
            move_y = dy * current_speed * 0.70710678
        else:
            move_x = dx * current_speed
            move_y = dy * current_speed

        if move_x != 0:
            self.x += move_x
            hitbox = self.get_hitbox()
            for obs in obstacles:
                obs_rect = obs.hitbox if hasattr(obs, 'hitbox') else obs
                if hitbox.colliderect(obs_rect):
                    if move_x > 0:
                        self.x -= (hitbox.right - obs_rect.left)
                    elif move_x < 0:
                        self.x += (obs_rect.right - hitbox.left)

        if move_y != 0:
            self.y += move_y
            hitbox = self.get_hitbox()
            for obs in obstacles:
                obs_rect = obs.hitbox if hasattr(obs, 'hitbox') else obs
                if hitbox.colliderect(obs_rect):
                    if move_y > 0:
                        self.y -= (hitbox.bottom - obs_rect.top)
                    elif move_y < 0:
                        self.y += (obs_rect.bottom - hitbox.top)

        padding = 4
        self.x = max(padding, min(viewport_width - padding, self.x))
        self.y = max(padding, min(viewport_height - padding, self.y))

        has_run_anim = "run" in self.animations

        if moving:
            if is_sprinting and has_run_anim:
                self.set_animation("run")
            else:
                self.set_animation("walk")

            if is_sprinting:
                _stop_move_loop("walk")
                _start_move_loop("run", self.run_sfx_name, self.run_sfx_volume)
            else:
                _stop_move_loop("run")
                _start_move_loop("walk", self.walk_sfx_name, self.walk_sfx_volume)
        elif not moving and self.current_animation in ("walk", "run"):
            self.set_animation("idle")
            _stop_move_loop("walk")
            _stop_move_loop("run")
        else:
            _stop_move_loop("walk")
            _stop_move_loop("run")

    def set_animation(self, animation_name):
        clean_name = self.normalize_name(animation_name)
        if clean_name in self.animations and len(self.animations[clean_name]) > 0:
            if self.current_animation != clean_name:
                self.current_animation = clean_name
                self.frame_index = 0
                self.frame_timer = 0.0

    def update(self, viewport_width=1280, viewport_height=720, obstacles=None):
        if self.hp <= 0:
            _stop_move_loop("walk")
            _stop_move_loop("run")
            self._update_death()
            return

        self.handle_input_and_collision(viewport_width, viewport_height, obstacles)

        current_frame_list = self.animations.get(self.current_animation, [])
        if not current_frame_list:
            return

        self.frame_timer += self.animation_speed
        if self.frame_timer >= 1.0:
            self.frame_timer = 0.0

            looping_states = ("idle", "walk", "run")
            if self.current_animation in looping_states:
                self.frame_index = (self.frame_index + 1) % len(current_frame_list)
            else:
                if self.frame_index < len(current_frame_list) - 1:
                    self.frame_index += 1

        current_image = current_frame_list[self.frame_index]
        self.rect = current_image.get_rect(midbottom=(int(self.x), int(self.y)))

    def draw(self, surface):
        current_frame_list = self.animations.get(self.current_animation, [])
        if current_frame_list:
            current_image = current_frame_list[self.frame_index]
            if not self.facing_right:
                current_image = pygame.transform.flip(current_image, True, False)

            self.rect = current_image.get_rect(midbottom=(int(self.x), int(self.y)))
            surface.blit(current_image, self.rect)

            if self.show_hitbox:
                pygame.draw.rect(surface, (255, 0, 0), self.get_hitbox(), 2)