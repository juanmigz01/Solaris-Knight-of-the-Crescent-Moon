
import os
import sys
import pygame

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from player.player import Player
from Modules.save_manager import save_full_game_state
from Modules.sound_manager import game_manager
from Modules.transition import run_transition
from gameplay.map_router import run_gameplay_with_map_switching


COLOR_VOID = (0, 0, 0)
COLOR_BLACK = (10, 10, 15)
COLOR_GOLD = (212, 175, 55)
COLOR_BRIGHT_GOLD = (255, 215, 0)
COLOR_WHITE = (240, 235, 210)
COLOR_GRAY = (150, 150, 170)
COLOR_AQUA = (140, 220, 255)


def draw_letterbox(surface, screen_h, bar_height=90):
    bar = pygame.Surface((surface.get_width(), bar_height))
    bar.fill(COLOR_VOID)
    surface.blit(bar, (0, 0))
    surface.blit(bar, (0, screen_h - bar_height))


def play_flash_transition(screen, duration_sec=1.0):
    clock = pygame.time.Clock()
    screen_size = screen.get_size()

    thunder_sound = None
    thunder_path = os.path.join(PROJECT_ROOT, "asset", "sfx", "thunder.mp3")

    if game_manager.sfx_enabled and os.path.exists(thunder_path):
        try:
            thunder_sound = pygame.mixer.Sound(thunder_path)
            thunder_sound.set_volume(game_manager.sfx_volume)
            thunder_sound.play()
        except Exception as e:
            print(f"[Prologue] Failed to play thunder SFX: {e}")

    total_frames = max(1, int(60 * duration_sec))
    for i in range(total_frames):
        clock.tick(60)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                break

        flash_surface = pygame.Surface(screen_size, pygame.SRCALPHA)
        alpha = int(255 * (1.0 - (i / float(total_frames))))
        flash_surface.fill((255, 255, 255, alpha))
        screen.blit(flash_surface, (0, 0))
        pygame.display.flip()

    if thunder_sound:
        thunder_sound.fadeout(300)


def play_fade_to_black(screen, duration_sec=1.5):
    clock = pygame.time.Clock()
    screen_size = screen.get_size()
    total_frames = max(1, int(60 * duration_sec))

    for i in range(total_frames):
        clock.tick(60)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                break

        fade_surface = pygame.Surface(screen_size)
        fade_surface.fill(COLOR_VOID)
        alpha = int(255 * (i / float(total_frames)))
        fade_surface.set_alpha(alpha)
        screen.blit(fade_surface, (0, 0))
        pygame.display.flip()


def render_wrapped_text(surface, text, font, color, rect, line_gap=8):
    words = text.split(' ')
    lines = []
    current_line = ""

    for word in words:
        if "\n" in word:
            parts = word.split("\n")
            for j, part in enumerate(parts):
                if j > 0:
                    lines.append(current_line)
                    current_line = ""
                if part:
                    current_line += part + " "
        else:
            test_line = current_line + word + " "
            if font.size(test_line)[0] < rect.width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word + " "
    lines.append(current_line)

    y_offset = rect.y
    for line in lines:
        stripped = line.strip()
        if stripped:
            line_surface = font.render(stripped, True, color)
            surface.blit(line_surface, (rect.x, y_offset))
        y_offset += font.get_linesize() + line_gap


def show_chapter_card(screen, clock, title, subtitle, font_title, font_sub,
                      duration_sec=3.0):
    screen_w, screen_h = screen.get_size()
    total_frames = max(1, int(60 * duration_sec))

    for i in range(total_frames):
        clock.tick(60)
        progress = i / float(total_frames)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif ((event.type == pygame.KEYDOWN and event.key in
                   (pygame.K_SPACE, pygame.K_RETURN))
                  or (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1)):
                return True

        if progress < 0.25:
            alpha = int(255 * (progress / 0.25))
        elif progress > 0.75:
            alpha = int(255 * ((1.0 - progress) / 0.25))
        else:
            alpha = 255

        screen.fill(COLOR_VOID)

        title_surf = font_title.render(title, True, COLOR_BRIGHT_GOLD)
        title_surf.set_alpha(alpha)
        title_rect = title_surf.get_rect(center=(screen_w // 2, screen_h // 2 - 40))
        screen.blit(title_surf, title_rect)

        if subtitle:
            sub_surf = font_sub.render(subtitle, True, COLOR_WHITE)
            sub_surf.set_alpha(alpha)
            sub_rect = sub_surf.get_rect(center=(screen_w // 2, screen_h // 2 + 40))
            screen.blit(sub_surf, sub_rect)

        if alpha > 120:
            line_alpha = min(255, alpha)
            line_surf = pygame.Surface((300, 2), pygame.SRCALPHA)
            line_surf.fill((COLOR_GOLD[0], COLOR_GOLD[1], COLOR_GOLD[2], line_alpha))
            screen.blit(line_surf, line_surf.get_rect(center=(screen_w // 2, screen_h // 2)))

        pygame.display.flip()

    return True


def show_story_beat(screen, clock, header_text, text,
                    font_header, font_body,
                    color=COLOR_WHITE, auto_advance_seconds=None,
                    char_delay=0.045):
    screen_w, screen_h = screen.get_size()

    beat_active = True
    typing_timer = 0.0
    visible_char_count = 0
    total_chars = len(text)
    is_fully_revealed = False

    auto_advance_timer = 0.0
    cursor_timer = 0.0

    background = pygame.Surface((screen_w, screen_h))
    background.fill(COLOR_BLACK)

    while beat_active:
        dt = clock.tick(60) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif ((event.type == pygame.KEYDOWN and event.key in
                   (pygame.K_SPACE, pygame.K_RETURN))
                  or (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1)):
                if not is_fully_revealed:
                    visible_char_count = total_chars
                    is_fully_revealed = True
                else:
                    beat_active = False

        if not is_fully_revealed:
            typing_timer += dt
            cursor_timer += dt
            visible_char_count = int(typing_timer / char_delay)
            if visible_char_count >= total_chars:
                visible_char_count = total_chars
                is_fully_revealed = True
        else:
            if auto_advance_seconds is not None:
                auto_advance_timer += dt
                if auto_advance_timer >= auto_advance_seconds:
                    beat_active = False

        screen.blit(background, (0, 0))

        current_text = text[:visible_char_count]
        if not is_fully_revealed:
            cursor_char = "_" if (int(cursor_timer * 3) % 2 == 0) else ""
            display_text = current_text + cursor_char
        else:
            display_text = text

        if header_text:
            header_surf = font_header.render(header_text, True, COLOR_GOLD)
            screen.blit(header_surf, (340, 300))
            pygame.draw.line(screen, COLOR_GOLD,
                             (340, 300 + header_surf.get_height() + 8),
                             (340 + 560, 300 + header_surf.get_height() + 8),
                             2)

        text_box_rect = pygame.Rect(340, 380, 1240, 380)
        render_wrapped_text(screen, display_text, font_body, color, text_box_rect)

        if is_fully_revealed:
            hint_surf = font_body.render("[ SPACE / ENTER to continue ]", True, COLOR_GRAY)
            screen.blit(hint_surf, hint_surf.get_rect(center=(screen_w // 2, screen_h - 150)))

        draw_letterbox(screen, screen_h, bar_height=90)
        pygame.display.flip()

    return True


def run_prologue(screen, slot_number):
    game_manager.play_music("violin.mp3", fade_ms=1500)

    clock = pygame.time.Clock()
    screen_w, screen_h = screen.get_size()
    player = Player(x=13 * 64, y=6 * 64, name="Solaris")

    font_path = os.path.join(PROJECT_ROOT, "asset", "font", "TheGothicRite.otf")
    if os.path.exists(font_path):
        font_chapter = pygame.font.Font(font_path, 72)
        font_sub = pygame.font.Font(font_path, 30)
        font_header = pygame.font.Font(font_path, 44)
        font_body = pygame.font.Font(font_path, 30)
        font_input = pygame.font.Font(font_path, 42)
    else:
        font_chapter = pygame.font.SysFont("Georgia", 72, bold=True)
        font_sub = pygame.font.SysFont("Georgia", 30)
        font_header = pygame.font.SysFont("Georgia", 44, bold=True)
        font_body = pygame.font.SysFont("Georgia", 30)
        font_input = pygame.font.SysFont("Georgia", 42)

    screen.fill(COLOR_VOID)
    pygame.display.flip()

    if not show_chapter_card(screen, clock, "PROLOGUE",
                              "The Night the Moon Went Dark",
                              font_chapter, font_sub, duration_sec=3.2):
        game_manager.stop_music(fade_ms=1000)
        return "QUIT_TO_MENU"

    story_beats = [
        ("THE KINGDOM OF AURELIA",
         "For generations, the Kingdom of Aurelia stood as a land of peace and beauty. "
         "Golden towers rose above the mist, and gardens spilled with flowers long into "
         "the warm nights."),

        ("THE GIRL IN THE GARDEN",
         "Lunaire was the only daughter of the royal family. Despite being surrounded by "
         "servants and tutors, she was often alone. Everyone treated her like a precious "
         "princess rather than a person."),

        ("THE BOY WHO DIDN'T BOW",
         "They met when they were seven. Solaris wandered into the gardens during one of "
         "his father's visits. He found Lunaire reading beneath a great tree. He didn't bow. "
         "He didn't call her 'Your Highness.' He simply asked: 'Why are you sitting here "
         "all by yourself?'"),

        ("A PROMISE KEPT",
         "From that day they were inseparable. They snuck through the gardens, stole sweets "
         "from the kitchens, and explored places they weren't supposed to. Solaris played "
         "the heroic knight. Lunaire played the princess he had to rescue."),

        ("THE LAST GOODBYE",
         "Years passed. Before Solaris left for his final training, Lunaire pressed a small "
         "silver pendant into his hand - a crescent moon, cast in silver. 'So you'll always "
         "know where to return,' she told him.\n\n"
         "He looked back and smiled. 'And I'll always come back.'"),

        ("THE SHADOW",
         "Peace held - until it didn't. Gorgona, the Vain Empress, was an ancient serpent "
         "sorceress consumed by one obsession: beauty that would never fade. When she "
         "learned of Lunaire's grace, that obsession found its target."),

        ("THE LONGEST NIGHT",
         "In a single midnight raid, Gorgona slipped past the castle's defenses and took "
         "the princess - meaning to drain her beauty to preserve her own. By morning, "
         "Lunaire was gone."),

        ("THE OATH RENEWED",
         "King Sethos remained in his throne room - safe, but frantic, hollowed by worry "
         "for his daughter. Solaris - now a fully trained knight - stepped forward. He "
         "touched the crescent pendant at his chest and remembered the promise he'd made "
         "as a boy.\n\nI'll always come back.\n\nNow it was time to keep it."),
    ]

    for header, body in story_beats:
        if not show_story_beat(screen, clock, header, body,
                                font_header, font_body, color=COLOR_WHITE):
            game_manager.stop_music(fade_ms=1000)
            return "QUIT_TO_MENU"

    screen.fill(COLOR_VOID)
    line1 = font_header.render(f"Lunaire: '{player.name}...'", True, COLOR_AQUA)
    screen.blit(line1, line1.get_rect(center=(screen_w // 2, screen_h // 2)))
    pygame.display.flip()
    pygame.time.wait(2200)

    screen.fill(COLOR_VOID)
    line2 = font_header.render("Lunaire: 'Please...'", True, COLOR_AQUA)
    screen.blit(line2, line2.get_rect(center=(screen_w // 2, screen_h // 2)))
    pygame.display.flip()
    pygame.time.wait(1500)

    play_flash_transition(screen, duration_sec=1.0)

    typed_name = ""
    input_active = True
    input_box_rect = pygame.Rect(screen_w // 2 - 250, screen_h // 2 - 35, 500, 70)

    while input_active:
        clock.tick(60)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                game_manager.stop_music(fade_ms=1000)
                return "QUIT_TO_MENU"
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    chosen_name = typed_name.strip() if typed_name.strip() != "" else "Solaris"
                    player.set_name(chosen_name)
                    input_active = False
                elif event.key == pygame.K_BACKSPACE:
                    typed_name = typed_name[:-1]
                else:
                    if len(typed_name) < 16 and event.unicode.isprintable():
                        typed_name += event.unicode

        screen.fill(COLOR_VOID)

        prompt_surf = font_sub.render("Who will answer the call?",
                                       True, COLOR_GOLD)
        screen.blit(prompt_surf,
                    prompt_surf.get_rect(center=(screen_w // 2, screen_h // 2 - 130)))

        pygame.draw.rect(screen, (25, 30, 40), input_box_rect, border_radius=6)
        pygame.draw.rect(screen, COLOR_GOLD, input_box_rect, 2, border_radius=6)

        display_str = typed_name if typed_name else "Solaris"
        display_color = COLOR_WHITE if typed_name else COLOR_GRAY
        text_surface = font_input.render(display_str, True, display_color)
        screen.blit(text_surface, (input_box_rect.x + 20, input_box_rect.y + 12))

        hint_surf = font_sub.render("Type your hero's name and press ENTER",
                                     True, COLOR_GRAY)
        screen.blit(hint_surf,
                    hint_surf.get_rect(center=(screen_w // 2, screen_h // 2 + 90)))

        pygame.display.flip()


    screen.fill(COLOR_VOID)
    line1 = font_header.render(f"{player.name}: '...Lunaire.'", True, COLOR_BRIGHT_GOLD)
    screen.blit(line1, line1.get_rect(center=(screen_w // 2, screen_h // 2 - 20)))
    pygame.display.flip()
    pygame.time.wait(2200)

    screen.fill(COLOR_VOID)
    line2 = font_header.render(f"{player.name}: 'I promised I'd come back.'",
                                True, COLOR_BRIGHT_GOLD)
    screen.blit(line2, line2.get_rect(center=(screen_w // 2, screen_h // 2 - 20)))
    pygame.display.flip()
    pygame.time.wait(2600)

    game_manager.stop_music(fade_ms=1500)
    play_fade_to_black(screen, duration_sec=1.5)

    run_transition(screen, message="Entering the Kingdom of Aurelia...", duration_sec=1.5)

    save_full_game_state(slot_number, player=player, position_valid=False)

    return run_gameplay_with_map_switching(
        screen, slot_id=slot_number, player=player, cinematic_intro=True
    )