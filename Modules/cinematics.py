
import pygame

from Modules.sound_manager import game_manager


CAM_LERP = 0.22

VIEWPORT_SCREEN_RECT = pygame.Rect(320, 180, 1280, 720)
VIEWPORT_OFFSET = (320, 180)


def get_cam_y(player_y, zoom, world_height, viewport_h=720):

    if zoom > 1.0:
        blend = min(1.0, (zoom - 1.0) / 0.3)
        cam_y = (player_y - viewport_h * 0.5) * blend
        cam_y = max(0.0, min(float(world_height - viewport_h), cam_y))
    else:
        cam_y = 0.0
    return cam_y


def smooth_camera_y(current, target, factor=CAM_LERP):

    if current is None:
        return float(target)
    return float(current) + (float(target) - float(current)) * factor


def _ease_in_out_cubic(t):
    if t < 0.5:
        return 4 * t * t * t
    else:
        f = (2 * t) - 2
        return 0.5 * f * f * f + 1


def play_zoom_intro(screen, frame, player, world_surface, world_height,
                    duration_sec=2.4, start_zoom=2.4,
                    hold_peak_sec=0.35, particles=None):

    clock = pygame.time.Clock()
    viewport = frame.get_viewport()

    restore_zoom = float(getattr(game_manager, "zoom_level", 1.0) or 1.0)

    saved_smooth = frame._smooth_focus
    frame._smooth_focus = [float(player.x), float(player.y)]

    base_world = world_surface.copy() if particles is not None else None

    total_frames = max(1, int(60 * duration_sec))
    hold_frames = max(1, int(60 * hold_peak_sec))

    for i in range(total_frames):
        dt = clock.tick(60) / 1000.0
        dt = min(dt, 0.05)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                game_manager.zoom_level = restore_zoom
                frame._smooth_focus = saved_smooth
                return

        if i < hold_frames:
            current_zoom = start_zoom
        else:
            raw_progress = (i - hold_frames) / float(max(1, total_frames - hold_frames))
            eased = _ease_in_out_cubic(raw_progress)
            current_zoom = start_zoom + (1.0 - start_zoom) * eased

        game_manager.zoom_level = current_zoom

        cam_y = get_cam_y(player.y, current_zoom, world_height)
        cam_y_int = int(cam_y)

        frame._smooth_focus = [float(player.x), float(player.y - cam_y)]
        frame.zoom_focus = (int(player.x), int(player.y - cam_y))

        if particles is not None:
            world_surface.blit(base_world, (0, 0))
            particles.update(dt)
            view_rect = pygame.Rect(0, cam_y_int, 1280, 720)
            particles.draw(world_surface, view_rect=view_rect)

        viewport.blit(world_surface, (0, 0),
                      pygame.Rect(0, cam_y_int, 1280, 720))

        frame.draw(screen)
        pygame.display.flip()

    game_manager.zoom_level = restore_zoom
    frame._smooth_focus = None
    frame.zoom_focus = (int(player.x), int(player.y))