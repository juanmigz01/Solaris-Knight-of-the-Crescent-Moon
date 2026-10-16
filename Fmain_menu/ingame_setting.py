import os
import sys
import pygame

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from Modules.button import Button, draw_corner_brackets
from Modules.sound_manager import game_manager


def run_ingame_settings(screen, bg_snapshot, slot_id=1, player=None,
                        wizard=None, orc=None, enemies=None, on_save=None):
    was_playing = pygame.mixer.music.get_busy()
    if was_playing:
        pygame.mixer.music.pause()

    clock = pygame.time.Clock()
    running = True
    action_result = None

    COLOR_PANEL        = (28, 26, 48)
    COLOR_BORDER       = (212, 175, 55)
    COLOR_GOLD         = (255, 215, 0)
    COLOR_TEXT_GRAY    = (150, 150, 170)
    COLOR_BTN_BG       = (35, 30, 60)
    COLOR_BTN_HOV      = (60, 50, 95)
    COLOR_TAB_INACT    = (22, 22, 40)
    COLOR_TAB_INACT_BD = (90, 75, 45)

    screen_w, screen_h = screen.get_size()
    center_x = screen_w // 2
    center_y = screen_h // 2

    dark_overlay = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
    dark_overlay.fill((10, 10, 20, 200))

    FONT_PATH = os.path.join(PROJECT_ROOT, "asset", "font", "TheGothicRite.otf")
    try:
        font_title = pygame.font.Font(FONT_PATH, 40)
        font_button = pygame.font.Font(FONT_PATH, 20)
        font_tab = pygame.font.Font(FONT_PATH, 22)
        font_section = pygame.font.Font(FONT_PATH, 16)
    except FileNotFoundError:
        font_title = pygame.font.SysFont("Georgia", 40, bold=True)
        font_button = pygame.font.SysFont("Georgia", 20, bold=True)
        font_tab = pygame.font.SysFont("Georgia", 22, bold=True)
        font_section = pygame.font.SysFont("Georgia", 16, bold=True)

    panel_w, panel_h = 720, 920
    container_rect = pygame.Rect(
        center_x - (panel_w // 2),
        center_y - (panel_h // 2),
        panel_w, panel_h,
    )

    tab_w, tab_h = 300, 50
    tab_gap = 20
    total_tabs_w = (tab_w * 2) + tab_gap
    tab_start_x = container_rect.left + (panel_w - total_tabs_w) // 2
    tab_y = container_rect.top + 110

    volume_tab_rect = pygame.Rect(tab_start_x, tab_y, tab_w, tab_h)
    misc_tab_rect   = pygame.Rect(tab_start_x + tab_w + tab_gap, tab_y, tab_w, tab_h)

    btn_w, btn_h = 480, 48
    btn_x = center_x - (btn_w // 2)

    def make_btn(x, y, w, h, text, **overrides):
        cfg = dict(
            bg_color=COLOR_BTN_BG, hover_color=COLOR_BTN_HOV,
            text_color=COLOR_GOLD, border_color=COLOR_BORDER,
            border_radius=8,
        )
        cfg.update(overrides)
        return Button(x, y, w, h, text=text, font=font_button, **cfg)

    content_top = container_rect.top + 210

    bgm_toggle_btn = make_btn(btn_x, content_top, btn_w, btn_h, "BACKGROUND MUSIC: ON")
    bgm_dec_btn    = make_btn(btn_x,          content_top + 70, 60,  btn_h, "-")
    bgm_vol_btn    = make_btn(btn_x + 70,     content_top + 70, 340, btn_h, "MUSIC VOL: 50%")
    bgm_inc_btn    = make_btn(btn_x + 420,    content_top + 70, 60,  btn_h, "+")

    sfx_toggle_btn = make_btn(btn_x, content_top + 160, btn_w, btn_h, "SOUND EFFECTS: ON")
    sfx_dec_btn    = make_btn(btn_x,          content_top + 230, 60,  btn_h, "-")
    sfx_vol_btn    = make_btn(btn_x + 70,     content_top + 230, 340, btn_h, "SFX VOL: 50%")
    sfx_inc_btn    = make_btn(btn_x + 420,    content_top + 230, 60,  btn_h, "+")

    radius_btn    = make_btn(btn_x, content_top + 10,  btn_w, btn_h, "RADIUS VISIBILITY: VISIBLE")
    outline_btn   = make_btn(btn_x, content_top + 90,  btn_w, btn_h, "CHARACTER OUTLINE: ON")
    zoom_btn      = make_btn(btn_x, content_top + 170, btn_w, btn_h, "ZOOM: 1.0x")
    hitbox_btn    = make_btn(btn_x, content_top + 250, btn_w, btn_h, "SHOW HITBOXES: OFF")
    zones_btn     = make_btn(btn_x, content_top + 330, btn_w, btn_h, "SHOW ZONE OUTLINES: OFF")
    particles_btn = make_btn(btn_x, content_top + 410, btn_w, btn_h, "MAPLE LEAVES: MEDIUM")

    misc_buttons = [radius_btn, outline_btn, zoom_btn, hitbox_btn, zones_btn, particles_btn]

    back_btn = make_btn(btn_x, container_rect.bottom - 120, btn_w, btn_h,
                        "BACK TO PAUSE MENU")
    bottom_buttons = [back_btn]

    title_surf = font_title.render("SETTINGS", True, COLOR_GOLD)
    title_rect = title_surf.get_rect(center=(center_x, container_rect.top + 55))

    hint_surf = font_button.render("[Press ESC to Return | TAB to Switch Tabs]",
                                   True, COLOR_TEXT_GRAY)
    hint_rect = hint_surf.get_rect(center=(center_x, container_rect.bottom - 25))

    panel_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
    panel_surf.fill((*COLOR_PANEL, 245))

    current_tab = "volume"

    def draw_tab(surface, rect, label, is_active):
        if is_active:
            bg = COLOR_BTN_BG; bd = COLOR_BORDER; tc = COLOR_GOLD; w = 3
        else:
            bg = COLOR_TAB_INACT; bd = COLOR_TAB_INACT_BD; tc = COLOR_TEXT_GRAY; w = 2

        pygame.draw.rect(surface, bg, rect, border_radius=8)
        pygame.draw.rect(surface, bd, rect, width=w, border_radius=8)

        t_surf = font_tab.render(label, True, tc)
        t_rect = t_surf.get_rect(center=rect.center)
        surface.blit(t_surf, t_rect)

        if is_active:
            pygame.draw.line(surface, COLOR_GOLD,
                             (rect.left + 15, rect.bottom - 6),
                             (rect.right - 15, rect.bottom - 6), 3)

    while running:
        clock.tick(60)
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_TAB:
                    current_tab = "misc" if current_tab == "volume" else "volume"

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if volume_tab_rect.collidepoint(mouse_pos):
                    current_tab = "volume"
                    continue
                if misc_tab_rect.collidepoint(mouse_pos):
                    current_tab = "misc"
                    continue

                if current_tab == "volume":
                    if bgm_toggle_btn.rect.collidepoint(mouse_pos):
                        game_manager.toggle_bgm()
                    elif bgm_dec_btn.rect.collidepoint(mouse_pos):
                        game_manager.change_music_volume(-0.1)
                    elif bgm_inc_btn.rect.collidepoint(mouse_pos):
                        game_manager.change_music_volume(0.1)
                    elif sfx_toggle_btn.rect.collidepoint(mouse_pos):
                        game_manager.toggle_sfx()
                    elif sfx_dec_btn.rect.collidepoint(mouse_pos):
                        game_manager.change_sfx_volume(-0.1)
                    elif sfx_inc_btn.rect.collidepoint(mouse_pos):
                        game_manager.change_sfx_volume(0.1)

                elif current_tab == "misc":
                    if radius_btn.rect.collidepoint(mouse_pos):
                        game_manager.toggle_radius_visibility()
                    elif outline_btn.rect.collidepoint(mouse_pos):
                        game_manager.toggle_outline_enabled()
                    elif zoom_btn.rect.collidepoint(mouse_pos):
                        game_manager.cycle_zoom()
                    elif hitbox_btn.rect.collidepoint(mouse_pos):
                        game_manager.toggle_hitboxes()
                    elif zones_btn.rect.collidepoint(mouse_pos):
                        game_manager.toggle_zones_visible()
                    elif particles_btn.rect.collidepoint(mouse_pos):
                        game_manager.cycle_particle_intensity()

                if back_btn.rect.collidepoint(mouse_pos):
                    while pygame.mouse.get_pressed()[0]:
                        pygame.event.pump()
                        clock.tick(60)
                    running = False

        bgm_toggle_btn.text = f"BACKGROUND MUSIC: {'ON' if game_manager.bgm_enabled else 'OFF'}"
        bgm_vol_btn.text = f"MUSIC VOL: {int(game_manager.music_volume * 100)}%"
        sfx_toggle_btn.text = f"SOUND EFFECTS: {'ON' if game_manager.sfx_enabled else 'OFF'}"
        sfx_vol_btn.text = f"SFX VOL: {int(game_manager.sfx_volume * 100)}%"

        radius_btn.text  = f"RADIUS VISIBILITY: {'VISIBLE' if game_manager.radius_visible else 'HIDDEN'}"
        outline_btn.text = f"CHARACTER OUTLINE: {'ON' if game_manager.outline_enabled else 'OFF'}"
        zoom_btn.text    = f"ZOOM: {game_manager.zoom_level:.2f}x"
        hitbox_btn.text  = f"SHOW HITBOXES: {'ON' if game_manager.hitbox_visible else 'OFF'}"
        zones_btn.text   = f"SHOW ZONE OUTLINES: {'ON' if game_manager.zones_visible else 'OFF'}"
        particles_btn.text = f"MAPLE LEAVES: {game_manager.particle_intensity.upper()}"

        screen.blit(bg_snapshot, (0, 0))
        screen.blit(dark_overlay, (0, 0))
        screen.blit(panel_surf, container_rect.topleft)
        pygame.draw.rect(screen, COLOR_BORDER, container_rect,
                         width=3, border_radius=12)
        draw_corner_brackets(screen, container_rect, COLOR_BORDER,
                             length=26, thickness=3, offset=8)

        screen.blit(title_surf, title_rect)
        pygame.draw.line(screen, COLOR_BORDER,
                         (container_rect.left + 70, container_rect.top + 90),
                         (container_rect.right - 70, container_rect.top + 90),
                         2)

        draw_tab(screen, volume_tab_rect, "VOLUME", current_tab == "volume")
        draw_tab(screen, misc_tab_rect,   "MISCELLANEOUS", current_tab == "misc")

        if current_tab == "volume":
            sec = font_section.render("MUSIC", True, COLOR_TEXT_GRAY)
            screen.blit(sec, (btn_x, content_top - 30))

            for b in [bgm_toggle_btn, bgm_dec_btn, bgm_vol_btn, bgm_inc_btn]:
                try: b.update(mouse_pos)
                except TypeError: b.update()
                try: b.draw(screen, mouse_pos)
                except TypeError: b.draw(screen)

            sec2 = font_section.render("SOUND EFFECTS", True, COLOR_TEXT_GRAY)
            screen.blit(sec2, (btn_x, content_top + 130))

            for b in [sfx_toggle_btn, sfx_dec_btn, sfx_vol_btn, sfx_inc_btn]:
                try: b.update(mouse_pos)
                except TypeError: b.update()
                try: b.draw(screen, mouse_pos)
                except TypeError: b.draw(screen)
        else:
            sec = font_section.render("DISPLAY & GAMEPLAY", True, COLOR_TEXT_GRAY)
            screen.blit(sec, (btn_x, content_top - 30))

            for b in misc_buttons:
                try: b.update(mouse_pos)
                except TypeError: b.update()
                try: b.draw(screen, mouse_pos)
                except TypeError: b.draw(screen)

        for b in bottom_buttons:
            try: b.update(mouse_pos)
            except TypeError: b.update()
            try: b.draw(screen, mouse_pos)
            except TypeError: b.draw(screen)

        screen.blit(hint_surf, hint_rect)
        pygame.display.flip()

    if was_playing and game_manager.bgm_enabled:
        pygame.mixer.music.unpause()

    return action_result