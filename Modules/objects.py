import os
import pygame

from Modules.char import (
    add_outline,
    make_outline_silhouette,
    DEFAULT_MASK_THRESHOLD,
)


OBJECT_CONFIG = {
    "rock_1": {
        "path": "asset/deco_img/rock_1.png",
        "scale": 1.0,
        "hitbox": (0.40, 0.45, 0.30, 0.30),
    },
    "rock_2": {
        "path": "asset/deco_img/rock_2.png",
        "scale": 1.0,
        "hitbox": (0.40, 0.45, 0.35, 0.35),
    },
    "maple": {
        "path": "asset/deco_img/maple.png",
        "scale": 1.0,
        "hitbox": (0.45, 0.55, 0.16, 0.15),
        "layer_hitbox": (0.15, 0.0, 0.70, 0.55),
    },
    "maplebush": {
        "path": "asset/deco_img/maplebush.png",
        "scale": 1.0,
        "hitbox": (0.33, 0.40, 0.40, 0.40),
    },
    "oak": {
        "path": "asset/deco_img/oak.png",
        "scale": 1.0,
        "hitbox": (0.45, 0.55, 0.10, 0.15),
        "layer_hitbox": (0.15, 0.0, 0.70, 0.55),
    },
    "oakbush": {
        "path": "asset/deco_img/oakbush.png",
        "scale": 1.0,
        "hitbox": (0.33, 0.40, 0.40, 0.40),
    },
    "house_1": {
        "path": "asset/deco_img/house_1.png",
        "scale": 0.65,
        "hitbox": (0.23, 0.58, 0.55, 0.10),
        "layer_hitbox": (0.10, 0.0, 0.80, 0.58),
    },
    "house_2": {
        "path": "asset/deco_img/house_2.png",
        "scale": 0.65,
        "hitbox": (0.20, 0.58, 0.62, 0.30),
        "layer_hitbox": (0.10, 0.0, 0.80, 0.58),
    },
    "castle": {
        "path": "asset/deco_img/Castle.png",
        "scale": 0.35,
        "hitbox": (0.13, 0.50, 0.74, 0.32),
        "layer_hitbox": (0.05, 0.0, 0.90, 0.50),
    },
}


class DecoObject:


    def __init__(self, obj_type, x=0, y=0, scale=None, center=None,
                 outline_color=None, outline_thickness=2,
                 outline_variants_colors=None,
                 outline_mask_threshold=DEFAULT_MASK_THRESHOLD):
        self.obj_type = obj_type.lower()
        self.x = x
        self.y = y

        self.config = OBJECT_CONFIG.get(self.obj_type, {})
        self.scale = scale if scale is not None else self.config.get("scale", 1.0)
        self.center_pos = center

        self.outline_color = outline_color
        self.outline_thickness = outline_thickness
        self.outline_variants_colors = outline_variants_colors
        self.outline_mask_threshold = outline_mask_threshold

        self._base_sprite = None
        self._variants = None
        self._variant_index = 0

        self.show_hitbox = False
        self.image = None
        self.rect = None

        self.hitbox = pygame.Rect(0, 0, 0, 0)
        self.layer_hitbox = None

        self.load_object()

    def load_object(self):
        file_path = self.config.get("path", "")

        if os.path.exists(file_path):
            raw_image = pygame.image.load(file_path).convert_alpha()
            if self.scale != 1.0:
                new_w = int(raw_image.get_width() * self.scale)
                new_h = int(raw_image.get_height() * self.scale)
                base = pygame.transform.scale(raw_image, (new_w, new_h))
            else:
                base = raw_image
        else:
            base = pygame.Surface((64, 64))
            base.fill((150, 150, 150))

        self._base_sprite = base

        if self.outline_variants_colors:
            try:
                self._variants = [
                    make_outline_silhouette(
                        base, color=c,
                        thickness=self.outline_thickness,
                        threshold=self.outline_mask_threshold,
                    )
                    for c in self.outline_variants_colors
                ]
                self.image = self._compose_full(self._variants[0])
                self._variant_index = 0
            except Exception as e:
                print(f"[objects] variant outline failed for {self.obj_type}: {e}")
                self._variants = None
                self.image = base

        elif self.outline_color is not None:
            try:
                self.image = add_outline(
                    base, color=self.outline_color,
                    thickness=self.outline_thickness,
                    threshold=self.outline_mask_threshold,
                )
            except Exception as e:
                print(f"[objects] outline failed for {self.obj_type}: {e}")
                self.image = base

        else:
            self.image = base

        if self.center_pos:
            self.rect = self.image.get_rect(center=self.center_pos)
            self.x = self.rect.x
            self.y = self.rect.y
        else:
            self.rect = self.image.get_rect(topleft=(self.x, self.y))

        off_x_pct, off_y_pct, w_pct, h_pct = self.config.get(
            "hitbox", (0.0, 0.0, 1.0, 1.0))
        hb_x = self.x + int(self.rect.width * off_x_pct)
        hb_y = self.y + int(self.rect.height * off_y_pct)
        hb_w = int(self.rect.width * w_pct)
        hb_h = int(self.rect.height * h_pct)
        self.hitbox = pygame.Rect(hb_x, hb_y, hb_w, hb_h)

        if "layer_hitbox" in self.config:
            l_x, l_y, l_w, l_h = self.config["layer_hitbox"]
            layer_x = self.x + int(self.rect.width * l_x)
            layer_y = self.y + int(self.rect.height * l_y)
            layer_w = int(self.rect.width * l_w)
            layer_h = int(self.rect.height * l_h)
            self.layer_hitbox = pygame.Rect(layer_x, layer_y, layer_w, layer_h)

    def _compose_full(self, outline_surface):

        composed = outline_surface.copy()
        composed.blit(self._base_sprite,
                      (self.outline_thickness, self.outline_thickness))
        return composed

    def has_variants(self):
        return bool(self._variants)

    def set_variant(self, index):

        if not self._variants:
            return
        index = int(index) % len(self._variants)
        if index == self._variant_index:
            return
        self._variant_index = index
        self.image = self._compose_full(self._variants[index])

    def draw(self, surface, blend_a=None, blend_b=None, blend_t=0.0):

        if not self._variants or blend_a is None:
            surface.blit(self.image, self.rect)
        else:
            n = len(self._variants)
            outline_a = self._variants[blend_a % n]
            surface.blit(outline_a, self.rect)

            if blend_b is not None and blend_t > 0.001:
                outline_b = self._variants[blend_b % n]
                prev_alpha = outline_b.get_alpha()
                outline_b.set_alpha(int(255 * min(1.0, blend_t)))
                surface.blit(outline_b, self.rect)
                outline_b.set_alpha(prev_alpha)

            pad = self.outline_thickness
            surface.blit(self._base_sprite,
                         (self.rect.x + pad, self.rect.y + pad))

        if self.show_hitbox:
            pygame.draw.rect(surface, (255, 0, 0), self.hitbox, 2)
            if self.layer_hitbox:
                pygame.draw.rect(surface, (0, 0, 255), self.layer_hitbox, 2)