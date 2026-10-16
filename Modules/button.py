import pygame


def draw_corner_brackets(surface, rect, color, length=24, thickness=3, offset=6):
    pygame.draw.line(surface, color, (rect.left - offset, rect.top - offset), (rect.left - offset + length, rect.top - offset), thickness)
    pygame.draw.line(surface, color, (rect.left - offset, rect.top - offset), (rect.left - offset, rect.top - offset + length), thickness)

    pygame.draw.line(surface, color, (rect.right + offset, rect.top - offset), (rect.right + offset - length, rect.top - offset), thickness)
    pygame.draw.line(surface, color, (rect.right + offset, rect.top - offset), (rect.right + offset, rect.top - offset + length), thickness)

    pygame.draw.line(surface, color, (rect.left - offset, rect.bottom + offset), (rect.left - offset + length, rect.bottom + offset), thickness)
    pygame.draw.line(surface, color, (rect.left - offset, rect.bottom + offset), (rect.left - offset, rect.bottom + offset - length), thickness)

    pygame.draw.line(surface, color, (rect.right + offset, rect.bottom + offset), (rect.right + offset - length, rect.bottom + offset), thickness)
    pygame.draw.line(surface, color, (rect.right + offset, rect.bottom + offset), (rect.right + offset, rect.bottom + offset - length), thickness)


def _play_click_sfx():
    try:
        from Modules.sound_manager import game_manager
        game_manager.play_sfx("click.mp3", volume=0.40)
    except Exception:
        pass


class Button:

    def __init__(self, x, y, width, height, text="", font=None,
                 bg_color=(35, 30, 60),
                 hover_color=(60, 50, 95),
                 text_color=(255, 215, 0),
                 border_color=(212, 175, 55),
                 border_radius=8):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.font = font if font is not None else pygame.font.SysFont("Georgia", 20)
        self.bg_color = bg_color
        self.hover_color = hover_color
        self.text_color = text_color
        self.border_color = border_color
        self.border_radius = border_radius
        self.is_hovered = False
        self._was_mouse_down = False

    def update(self, mouse_pos=None):
        if mouse_pos is None:
            mouse_pos = pygame.mouse.get_pos()
        self.is_hovered = self.rect.collidepoint(mouse_pos)

    def draw(self, surface, mouse_pos=None):
        self.update(mouse_pos)

        current_bg = self.hover_color if self.is_hovered else self.bg_color

        pygame.draw.rect(surface, current_bg, self.rect,
                         border_radius=self.border_radius)

        if self.rect.height > 8 and self.rect.width > 16:
            hl_w = self.rect.width - 10
            hl_h = 2
            hl = pygame.Surface((hl_w, hl_h), pygame.SRCALPHA)
            hl.fill((255, 235, 180, 30))
            surface.blit(hl, (self.rect.x + 5, self.rect.y + 3))

        if self.border_color:
            pygame.draw.rect(surface, self.border_color, self.rect,
                             width=2, border_radius=self.border_radius)

        if self.text:
            text_surf = self.font.render(self.text, True, self.text_color)
            text_rect = text_surf.get_rect(center=self.rect.center)
            surface.blit(text_surf, text_rect)

        mouse_down = pygame.mouse.get_pressed()[0]
        if self.is_hovered and mouse_down and not self._was_mouse_down:
            _play_click_sfx()
        self._was_mouse_down = mouse_down

        if self.is_hovered and mouse_down:
            return True
        return False