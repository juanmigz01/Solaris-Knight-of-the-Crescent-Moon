import os
import random
import pygame

class CastleFloor:
    def __init__(self, viewport_width=1280, viewport_height=720):
        self.width = viewport_width

        self.height = viewport_height

        self.floor_images = []

        self.current_floor = None

        self.load_floors()

        self.select_random_floor()

    def load_floors(self):
        image_paths = [
            os.path.join("asset", "deco_img", "tiles", "castle_1.png"),
            os.path.join("asset", "deco_img", "tiles", "castle_2.png")
        ]

        for path in image_paths:
            if os.path.exists(path):
                raw_image = pygame.image.load(path).convert_alpha()

                scaled_image = pygame.transform.scale(raw_image, (self.width, self.height))

                self.floor_images.append(scaled_image)
            else:
                fallback_surf = pygame.Surface((self.width, self.height))
                fallback_surf.fill((45, 40, 55))
                self.floor_images.append(fallback_surf)

    def select_random_floor(self):
        if len(self.floor_images) > 0:
            self.current_floor = random.choice(self.floor_images)

    def draw(self, viewport_surface):
        if self.current_floor is not None:
            viewport_surface.blit(self.current_floor, (0, 0))