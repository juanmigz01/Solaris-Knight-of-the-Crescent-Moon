import os
import sys
import json
import pygame

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


CHEST_IMG  = os.path.join("asset", "deco_img", "gold_chest.png")
CHEST_JSON = os.path.join("asset", "deco_img", "gold_chest.json")

CHEST_SCALE = 2.0

CLOSED_FRAMES  = [0]
OPENING_FRAMES = [0, 6, 10, 11, 12, 13, 19, 20]
OPENED_FRAMES  = [20]

OPEN_FRAME_TIME = 0.10


class Chest:


    def __init__(self, x=0, y=0, loot=None, label="Chest"):
        self.x = float(x)
        self.y = float(y)
        self.label = label

        self.state = "CLOSED"
        self.frame_index = 0
        self.frame_timer = 0.0

        self.loot = list(loot) if loot else []

        self.animations = {}
        self.image = pygame.Surface((48, 40))
        self.image.fill((200, 160, 40))
        self.rect = self.image.get_rect(midbottom=(int(self.x), int(self.y)))

        self.load_spritesheet_and_json(CHEST_IMG, CHEST_JSON)
        self._set_state("CLOSED")

    def load_spritesheet_and_json(self, image_path, json_path):
        full_img = os.path.join(PROJECT_ROOT, image_path)
        full_json = os.path.join(PROJECT_ROOT, json_path)

        if not os.path.exists(full_img) or not os.path.exists(full_json):
            print(f"[Chest] Missing asset files: {full_img} / {full_json}")
            return

        sprite_sheet = pygame.image.load(full_img).convert_alpha()

        with open(full_json, "r") as f:
            data = json.load(f)

        raw_frames = []
        for frame_entry in data["frames"].values():
            fr = frame_entry["frame"]
            fx, fy, fw, fh = fr["x"], fr["y"], fr["w"], fr["h"]
            sub = sprite_sheet.subsurface(pygame.Rect(fx, fy, fw, fh))
            scaled = pygame.transform.scale(
                sub, (int(fw * CHEST_SCALE), int(fh * CHEST_SCALE))
            )
            raw_frames.append(scaled)

        def pick(indices):
            out = []
            for i in indices:
                if 0 <= i < len(raw_frames):
                    out.append(raw_frames[i])
            return out

        self.animations["closed"]  = pick(CLOSED_FRAMES)
        self.animations["opening"] = pick(OPENING_FRAMES)
        self.animations["opened"]  = pick(OPENED_FRAMES)

        if not self.animations["closed"] and raw_frames:
            self.animations["closed"]  = [raw_frames[0]]
        if not self.animations["opening"] and raw_frames:
            self.animations["opening"] = [raw_frames[0]]
        if not self.animations["opened"] and raw_frames:
            self.animations["opened"]  = [raw_frames[-1]]

        if self.animations["closed"]:
            self.image = self.animations["closed"][0]
            self.rect = self.image.get_rect(midbottom=(int(self.x), int(self.y)))

    def _set_state(self, new_state):
        self.state = new_state
        self.frame_index = 0
        self.frame_timer = 0.0

        frames = self.animations.get(new_state.lower(), [])
        if frames:
            self.image = frames[0]
            self.rect = self.image.get_rect(midbottom=(int(self.x), int(self.y)))

    def open(self):

        if self.state != "CLOSED":
            return False
        self._set_state("OPENING")
        return True

    def is_opened(self):
        return self.state == "OPENED"

    def get_hitbox(self):

        w = max(20, self.rect.width - 20)
        h = 16
        hb = pygame.Rect(0, 0, w, h)
        hb.midbottom = (self.rect.centerx, self.rect.bottom - 4)
        return hb

    def can_interact(self, player):

        if self.state != "CLOSED":
            return False

        player_rect = getattr(player, "hitbox", getattr(player, "rect", None))
        if player_rect is None:
            return False

        dx = player_rect.centerx - self.rect.centerx
        dy = player_rect.centery - self.rect.centery
        return (dx * dx + dy * dy) ** 0.5 <= 70

    def update(self, dt=0.016):
        if self.state != "OPENING":
            return

        frames = self.animations.get("opening", [])
        if not frames:
            self._set_state("OPENED")
            return

        self.frame_timer += dt
        if self.frame_timer >= OPEN_FRAME_TIME:
            self.frame_timer = 0.0
            self.frame_index += 1

            if self.frame_index >= len(frames):
                self._set_state("OPENED")
                return

            self.image = frames[self.frame_index]

    def draw(self, surface):
        self.rect = self.image.get_rect(midbottom=(int(self.x), int(self.y)))
        surface.blit(self.image, self.rect)