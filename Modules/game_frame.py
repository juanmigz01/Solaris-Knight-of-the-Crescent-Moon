import os
import sys
import math
import random
import pygame

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from Modules.button import Button

try:
    from Modules.sound_manager import game_manager
except Exception:
    game_manager = None


STAR_SURFACES = {}
for _sz in (1, 2, 3):
    _surf = pygame.Surface((_sz, _sz), pygame.SRCALPHA)
    _surf.fill((255, 255, 255, 255))
    STAR_SURFACES[_sz] = _surf


class GameFrame:

    def __init__(self, font_large=None, font_small=None):
        self.font_large = font_large
        self.font_small = font_small

        self.viewport_size = (1280, 720)
        self.viewport_pos = (320, 180)
        self.viewport = pygame.Surface(self.viewport_size)

        self.shake_offset = (0, 0)

        self.zoom_focus = None
        self._smooth_focus = None
        self.zoom_smooth = 0.20

        self.COLOR_BG        = (15, 15, 30)
        self.COLOR_PANEL     = (28, 26, 48)
        self.COLOR_SLOT_BG   = (22, 22, 40)
        self.COLOR_BORDER    = (212, 175, 55)
        self.COLOR_GOLD      = (255, 215, 0)
        self.COLOR_TEXT      = (240, 235, 210)

        self.COLOR_SLOT_MAIN = (100, 160, 255)
        self.COLOR_SLOT_OFF  = (240, 80, 80)

        self.quests = []

        self.header_rect = pygame.Rect(320, 20, 1280, 130)
        self.left_panel_rect = pygame.Rect(20, 180, 280, 720)
        self.right_panel_rect = pygame.Rect(1620, 180, 280, 720)

        COLOR_BTN_BG  = (35, 30, 60)
        COLOR_BTN_HOV = (60, 50, 95)

        self.pause_btn = Button(
            20, 60, 280, 60, text="PAUSE", font=self.font_small,
            bg_color=COLOR_BTN_BG, hover_color=COLOR_BTN_HOV,
            text_color=self.COLOR_GOLD, border_color=self.COLOR_BORDER,
            border_radius=8,
        )
        self.stats_btn = Button(
            20, 930, 280, 60, text="STATS", font=self.font_small,
            bg_color=COLOR_BTN_BG, hover_color=COLOR_BTN_HOV,
            text_color=self.COLOR_GOLD, border_color=self.COLOR_BORDER,
            border_radius=8,
        )

        slot_size = 46
        spacing = 8
        slot_count = 5
        total_equip_width = (slot_size * slot_count) + (spacing * (slot_count - 1))
        start_x = 1620 + (280 - total_equip_width) // 2
        slot_y = 230

        self.equip_slots = {
            "helmet":      pygame.Rect(start_x, slot_y, slot_size, slot_size),
            "chestplate":  pygame.Rect(start_x + (slot_size + spacing), slot_y, slot_size, slot_size),
            "weapon":      pygame.Rect(start_x + (slot_size + spacing) * 2, slot_y, slot_size, slot_size),
            "weapon_off":  pygame.Rect(start_x + (slot_size + spacing) * 3, slot_y, slot_size, slot_size),
            "accessory":   pygame.Rect(start_x + (slot_size + spacing) * 4, slot_y, slot_size, slot_size),
        }

        potion_size = 56
        potion_spacing = 14
        potion_count = 3
        total_potion_w = (potion_size * potion_count) + (potion_spacing * (potion_count - 1))
        potion_start_x = 1620 + (280 - total_potion_w) // 2
        potion_y = 326

        self.potion_slots = [
            pygame.Rect(potion_start_x + i * (potion_size + potion_spacing),
                        potion_y, potion_size, potion_size)
            for i in range(potion_count)
        ]

        tab_w = 96
        tab_h = 32
        tab_gap = 4
        total_tab_w = tab_w * 2 + tab_gap
        tabs_start_x = 1620 + (280 - total_tab_w) // 2
        tabs_y = 386

        self.tab_armor_rect  = pygame.Rect(tabs_start_x, tabs_y, tab_w, tab_h)
        self.tab_weapon_rect = pygame.Rect(tabs_start_x + tab_w + tab_gap,
                                           tabs_y, tab_w, tab_h)

        self.inventory_slots = []
        inv_cols = 3
        inv_rows = 5
        inv_slot_size = 56
        inv_spacing = 14
        grid_width = (inv_cols * inv_slot_size) + ((inv_cols - 1) * inv_spacing)
        grid_start_x = 1620 + (280 - grid_width) // 2
        grid_start_y = 470

        for row in range(inv_rows):
            for col in range(inv_cols):
                sx = grid_start_x + col * (inv_slot_size + inv_spacing)
                sy = grid_start_y + row * (inv_slot_size + inv_spacing)
                self.inventory_slots.append(pygame.Rect(sx, sy, inv_slot_size, inv_slot_size))

        screen_w, screen_h = 1920, 1080
        self._star_count = 80
        self._stars = [
            {
                "x": random.randint(0, screen_w),
                "y": random.randint(0, screen_h),
                "speed": random.uniform(0.15, 0.4),
                "size": random.randint(1, 3),
            }
            for _ in range(self._star_count)
        ]
        self._star_frame = 0
        self._screen_size = (screen_w, screen_h)

    def get_viewport(self):
        return self.viewport

    def _update_and_draw_stars(self, screen):
        self._star_frame += 1
        screen_w, screen_h = self._screen_size

        for star in self._stars:
            star["x"] -= star["speed"]
            if star["x"] < 0:
                star["x"] = screen_w
                star["y"] = random.randint(0, screen_h)

            alpha = int(120 + math.sin(self._star_frame * 0.04 + star["x"]) * 90)
            alpha = max(0, min(255, alpha))

            dot = STAR_SURFACES[star["size"]]
            dot.set_alpha(alpha)
            screen.blit(dot, (star["x"], star["y"]))

    def _draw_corner_brackets(self, screen, rect, arm_length=16, thickness=3):
        x, y, w, h = rect.x, rect.y, rect.width, rect.height
        gold = self.COLOR_GOLD

        pygame.draw.line(screen, gold, (x, y), (x + arm_length, y), thickness)
        pygame.draw.line(screen, gold, (x, y), (x, y + arm_length), thickness)
        pygame.draw.line(screen, gold, (x + w, y), (x + w - arm_length, y), thickness)
        pygame.draw.line(screen, gold, (x + w, y), (x + w, y + arm_length), thickness)
        pygame.draw.line(screen, gold, (x, y + h), (x + arm_length, y + h), thickness)
        pygame.draw.line(screen, gold, (x, y + h), (x, y + h - arm_length), thickness)
        pygame.draw.line(screen, gold, (x + w, y + h), (x + w - arm_length, y + h), thickness)
        pygame.draw.line(screen, gold, (x + w, y + h), (x + w, y + h - arm_length), thickness)

    def _draw_corner_rivets(self, screen, rect, offset=10, radius=3):
        x, y, w, h = rect.x, rect.y, rect.width, rect.height
        gold = self.COLOR_GOLD

        pygame.draw.circle(screen, gold, (x + offset, y + offset), radius)
        pygame.draw.circle(screen, gold, (x + w - offset, y + offset), radius)
        pygame.draw.circle(screen, gold, (x + offset, y + h - offset), radius)
        pygame.draw.circle(screen, gold, (x + w - offset, y + h - offset), radius)

    def _draw_panels(self, screen):
        panels = [self.header_rect, self.left_panel_rect, self.right_panel_rect]
        for rect in panels:
            pygame.draw.rect(screen, self.COLOR_PANEL, rect, border_radius=8)
            pygame.draw.rect(screen, self.COLOR_BORDER, rect, width=2, border_radius=8)
            self._draw_corner_brackets(screen, rect)
            self._draw_corner_rivets(screen, rect)

        mid_y = self.left_panel_rect.centery
        pygame.draw.line(
            screen, self.COLOR_BORDER,
            (self.left_panel_rect.left + 20, mid_y),
            (self.left_panel_rect.right - 20, mid_y),
            2,
        )

    def _draw_labels(self, screen):
        if not self.font_small:
            return

        title_text = getattr(self, "title_text", "Solaris: Knight of the Crescent Moon")
        title_surf = (
            self.font_large.render(title_text, True, self.COLOR_GOLD)
            if self.font_large else None
        )
        if title_surf:
            screen.blit(title_surf, title_surf.get_rect(center=self.header_rect.center))

        commands_lbl = self.font_small.render("COMMANDS", True, self.COLOR_GOLD)
        screen.blit(commands_lbl, commands_lbl.get_rect(center=(160, 210)))
        pygame.draw.line(screen, self.COLOR_BORDER, (100, 228), (220, 228), 2)

        quests_label_y = self.left_panel_rect.centery + 30
        quests_lbl = self.font_small.render("QUESTS", True, self.COLOR_GOLD)
        screen.blit(quests_lbl, quests_lbl.get_rect(center=(160, quests_label_y)))
        pygame.draw.line(
            screen, self.COLOR_BORDER,
            (100, quests_label_y + 18),
            (220, quests_label_y + 18),
            2,
        )

        equip_lbl = self.font_small.render("EQUIPMENT", True, self.COLOR_GOLD)
        screen.blit(equip_lbl, equip_lbl.get_rect(center=(1760, 200)))
        pygame.draw.line(screen, self.COLOR_BORDER, (1700, 216), (1820, 216), 2)

        potions_lbl = self.font_small.render("POTIONS", True, self.COLOR_GOLD)
        screen.blit(potions_lbl, potions_lbl.get_rect(center=(1760, 298)))
        pygame.draw.line(screen, self.COLOR_BORDER, (1700, 314), (1820, 314), 2)

        items_lbl = self.font_small.render("INVENTORY", True, self.COLOR_GOLD)
        screen.blit(items_lbl, items_lbl.get_rect(center=(1760, 440)))
        pygame.draw.line(screen, self.COLOR_BORDER, (1700, 456), (1820, 456), 2)

    def _draw_quests(self, screen):
        if not self.font_small:
            return

        panel_left = self.left_panel_rect.left
        panel_right = self.left_panel_rect.right
        content_left = panel_left + 16
        content_right = panel_right - 16

        bottom_half_top = self.left_panel_rect.centery + 55

        if not self.quests:
            empty_surf = self.font_small.render(
                "[ No active quests ]", True, (150, 150, 170)
            )
            screen.blit(
                empty_surf,
                empty_surf.get_rect(center=(160, bottom_half_top + 70)),
            )
            return

        line_height = 26
        y_limit = self.left_panel_rect.bottom - 40
        y = bottom_half_top + 10

        for i, quest_text in enumerate(self.quests):
            color = self.COLOR_TEXT if i == 0 else (180, 175, 165)
            bullet = "> " if i == 0 else "- "
            bullet_w = self.font_small.size(bullet)[0]

            if y + line_height > y_limit:
                return

            bullet_surf = self.font_small.render(bullet, True, color)
            screen.blit(bullet_surf, (content_left, y))

            text_x = content_left + bullet_w
            text_max_w = content_right - text_x

            words = quest_text.split(" ")
            current = ""

            for word in words:
                test = (current + " " + word).strip() if current else word
                if self.font_small.size(test)[0] <= text_max_w:
                    current = test
                else:
                    if y + line_height > y_limit:
                        return
                    surf = self.font_small.render(current, True, color)
                    screen.blit(surf, (text_x, y))
                    y += line_height
                    current = word

            if current:
                if y + line_height > y_limit:
                    return
                surf = self.font_small.render(current, True, color)
                screen.blit(surf, (text_x, y))
                y += line_height

    def _draw_slots(self, screen):
        for slot_name, rect in self.equip_slots.items():
            if slot_name == "weapon":
                border_color = self.COLOR_SLOT_MAIN
            elif slot_name == "weapon_off":
                border_color = self.COLOR_SLOT_OFF
            else:
                border_color = self.COLOR_BORDER

            pygame.draw.rect(screen, self.COLOR_SLOT_BG, rect, border_radius=6)
            pygame.draw.rect(screen, border_color, rect, width=2, border_radius=6)

        for rect in self.potion_slots:
            pygame.draw.rect(screen, self.COLOR_SLOT_BG, rect, border_radius=6)
            pygame.draw.rect(screen, self.COLOR_BORDER, rect, width=2, border_radius=6)

        for rect in self.inventory_slots:
            pygame.draw.rect(screen, self.COLOR_SLOT_BG, rect, border_radius=6)
            pygame.draw.rect(screen, self.COLOR_BORDER, rect, width=2, border_radius=6)

    def _draw_buttons(self, screen):
        action_triggered = None
        if self.pause_btn.draw(screen):
            action_triggered = "PAUSE"
        if self.stats_btn.draw(screen):
            action_triggered = "STATS"
        return action_triggered

    def _draw_viewport(self, screen):
        viewport_border = pygame.Rect(
            self.viewport_pos[0] - 3,
            self.viewport_pos[1] - 3,
            self.viewport_size[0] + 6,
            self.viewport_size[1] + 6,
        )
        pygame.draw.rect(screen, self.COLOR_BORDER, viewport_border, width=3, border_radius=4)

        apply_pos = (
            self.viewport_pos[0] + int(self.shake_offset[0]),
            self.viewport_pos[1] + int(self.shake_offset[1]),
        )

        zoom = 1.0
        if game_manager is not None:
            try:
                zoom = float(getattr(game_manager, "zoom_level", 1.0))
            except (TypeError, ValueError):
                zoom = 1.0
        if zoom < 1.0:
            zoom = 1.0

        if zoom <= 1.0:
            self._smooth_focus = None
            screen.blit(self.viewport, apply_pos)
            return

        vw, vh = self.viewport_size

        if self.zoom_focus is None:
            target_x, target_y = vw / 2.0, vh / 2.0
        else:
            target_x = float(self.zoom_focus[0])
            target_y = float(self.zoom_focus[1])

        if self._smooth_focus is None:
            self._smooth_focus = [target_x, target_y]
        else:
            self._smooth_focus[0] += (target_x - self._smooth_focus[0]) * self.zoom_smooth
            self._smooth_focus[1] += (target_y - self._smooth_focus[1]) * self.zoom_smooth

        focus_x, focus_y = self._smooth_focus

        crop_w = int(vw / zoom)
        crop_h = int(vh / zoom)

        crop_x = int(focus_x - crop_w // 2)
        crop_y = int(focus_y - crop_h // 2)

        crop_x = max(0, min(vw - crop_w, crop_x))
        crop_y = max(0, min(vh - crop_h, crop_y))

        crop_rect = pygame.Rect(crop_x, crop_y, crop_w, crop_h)
        cropped = self.viewport.subsurface(crop_rect)
        zoomed = pygame.transform.scale(cropped, self.viewport_size)
        screen.blit(zoomed, apply_pos)

    def draw(self, screen):
        screen.fill(self.COLOR_BG)

        self._update_and_draw_stars(screen)

        self._draw_panels(screen)
        self._draw_labels(screen)
        self._draw_quests(screen)
        self._draw_slots(screen)
        action_triggered = self._draw_buttons(screen)
        self._draw_viewport(screen)
        return action_triggered