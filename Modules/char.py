
import pygame


OUTLINE_COLOR_WHITE = (255, 255, 255, 255)
OUTLINE_COLOR_RED   = (220,  40,  40, 255)

OUTLINE_COLOR = OUTLINE_COLOR_WHITE

OUTLINE_THICKNESS = 2

DEFAULT_MASK_THRESHOLD = 127


def _outlines_enabled():

    try:
        from Modules.sound_manager import game_manager
        return getattr(game_manager, "outline_enabled", True)
    except Exception:
        return True


def add_outline(sprite, color=OUTLINE_COLOR_WHITE,
                thickness=OUTLINE_THICKNESS,
                threshold=DEFAULT_MASK_THRESHOLD):


    if not _outlines_enabled():
        return sprite

    pad = thickness
    width, height = sprite.get_size()
    new_width = width + pad * 2
    new_height = height + pad * 2

    outlined = pygame.Surface((new_width, new_height), pygame.SRCALPHA)

    mask = pygame.mask.from_surface(sprite, threshold)
    silhouette = mask.to_surface(setcolor=color, unsetcolor=(0, 0, 0, 0))

    for dx in range(-pad, pad + 1):
        for dy in range(-pad, pad + 1):
            if dx == 0 and dy == 0:
                continue
            outlined.blit(silhouette, (pad + dx, pad + dy))

    outlined.blit(sprite, (pad, pad))
    return outlined


def make_outline_silhouette(sprite, color=OUTLINE_COLOR_WHITE,
                            thickness=OUTLINE_THICKNESS,
                            threshold=DEFAULT_MASK_THRESHOLD):

    pad = thickness
    width, height = sprite.get_size()
    new_width = width + pad * 2
    new_height = height + pad * 2

    outlined = pygame.Surface((new_width, new_height), pygame.SRCALPHA)

    if not _outlines_enabled():
        return outlined

    mask = pygame.mask.from_surface(sprite, threshold)
    silhouette = mask.to_surface(setcolor=color, unsetcolor=(0, 0, 0, 0))

    for dx in range(-pad, pad + 1):
        for dy in range(-pad, pad + 1):
            if dx == 0 and dy == 0:
                continue
            outlined.blit(silhouette, (pad + dx, pad + dy))

    return outlined


def add_outline_to_list(sprites, color=OUTLINE_COLOR_WHITE,
                        thickness=OUTLINE_THICKNESS):

    return [add_outline(s, color, thickness) for s in sprites]