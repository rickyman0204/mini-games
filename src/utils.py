"""Utility functions for games"""
import random
import math
import pygame
from src.settings import PRIZES, TREE_DROPS, WINDOW_WIDTH, WINDOW_HEIGHT


# Global mouse transform (set by main.py for screen scaling)
_mouse_scale = 1.0
_mouse_offset_x = 0.0
_mouse_offset_y = 0.0

# Font cache
_font_cache = {}


def set_mouse_transform(scale: float, offset_x: float, offset_y: float):
    """Set transform for mouse position conversion"""
    global _mouse_scale, _mouse_offset_x, _mouse_offset_y
    _mouse_scale = scale
    _mouse_offset_x = offset_x
    _mouse_offset_y = offset_y


def get_mouse_pos() -> tuple:
    """Get mouse position converted to base surface coords"""
    mx, my = pygame.mouse.get_pos()
    return ((mx - _mouse_offset_x) / _mouse_scale, (my - _mouse_offset_y) / _mouse_scale)


def s(value: float) -> int:
    """Scale value for 1280x900 base resolution (scale factor 1.6x)"""
    return int(value * 1.6)


def get_font(size: int, bold: bool = False) -> pygame.font.Font:
    """Cached system font with fallback chain"""
    key = (size, bold)
    if key not in _font_cache:
        for name in ['microsoftyahei', 'simhei', 'arial', 'dejavusans']:
            try:
                _font_cache[key] = pygame.font.SysFont(name, size, bold=bold)
                break
            except Exception:
                continue
        if key not in _font_cache:
            _font_cache[key] = pygame.font.Font(None, size)
    return _font_cache[key]


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp a value between min and max"""
    return max(min_val, min(value, max_val))


def lerp(start: float, end: float, t: float) -> float:
    """Linear interpolation between start and end"""
    return start + (end - start) * t


def lerp_color(color1: str, color2: str, t: float) -> tuple:
    """Interpolate between two hex colors"""
    r1, g1, b1 = int(color1[1:3], 16), int(color1[3:5], 16), int(color1[5:7], 16)
    r2, g2, b2 = int(color2[1:3], 16), int(color2[3:5], 16), int(color2[5:7], 16)
    r = int(lerp(r1, r2, t))
    g = int(lerp(g1, g2, t))
    b = int(lerp(b1, b2, t))
    return (r, g, b)


def ease_out_quad(t: float) -> float:
    """Decelerating ease-out for natural animations"""
    return t * (2 - t)


def ease_out_back(t: float) -> float:
    """Bounce effect for prize reveal pop-in"""
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * pow(t - 1, 3) + c1 * pow(t - 1, 2)


def ease_in_out_quad(t: float) -> float:
    """Accelerate then decelerate"""
    return t * t if t < 0.5 else 1 - (1 - t) * (1 - t)


def ease_out_cubic(t: float) -> float:
    """Smooth deceleration"""
    return 1 - pow(1 - t, 3)


def random_prize() -> str:
    """Return a random prize key based on probability weights"""
    roll = random.random()
    cumulative = 0.0
    for prize_key, prize_data in PRIZES.items():
        cumulative += prize_data['probability']
        if roll <= cumulative:
            return prize_key
    return list(PRIZES.keys())[-1]


def random_tree_drop() -> str:
    """Return a random tree drop key based on probability weights"""
    roll = random.random()
    cumulative = 0.0
    for drop_key, drop_data in TREE_DROPS.items():
        cumulative += drop_data['probability']
        if roll <= cumulative:
            return drop_key
    return list(TREE_DROPS.keys())[-1]


def generate_prizes(count: int = 3) -> list:
    """Generate a list of random prizes for the scratch cards"""
    return [random_prize() for _ in range(count)]


def has_pair(prizes: list) -> bool:
    """Check if there are at least 2 identical prizes"""
    return len(prizes) != len(set(prizes))


def hex_to_rgb(hex_color: str) -> tuple:
    """Convert hex color string to RGB tuple, or pass through if already tuple"""
    if isinstance(hex_color, tuple):
        return hex_color
    return (int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16))


def format_money(amount: int) -> str:
    """Format money amount with currency symbol"""
    return f'¥{amount}'


def draw_text_with_shadow(surface: pygame.Surface, text: str, font: pygame.font.Font,
                          color: tuple | str, pos: tuple, shadow_color: tuple = None,
                          shadow_offset: int = 2):
    """Draw text with drop shadow"""
    if shadow_color is None:
        shadow_color = (0, 0, 0)
    shadow_surf = font.render(text, True, hex_to_rgb(shadow_color))
    surface.blit(shadow_surf, shadow_surf.get_rect(center=(pos[0] + shadow_offset, pos[1] + shadow_offset)))
    text_surf = font.render(text, True, hex_to_rgb(color))
    surface.blit(text_surf, text_surf.get_rect(center=pos))


def draw_text_with_glow(surface: pygame.Surface, text: str, font: pygame.font.Font,
                        color: tuple | str, pos: tuple, glow_color: tuple = None,
                        glow_radius: int = 4):
    """Draw text with soft glow effect"""
    if glow_color is None:
        glow_color = hex_to_rgb(color)
    # Glow layers
    for i in range(glow_radius, 0, -1):
        alpha = int(40 * (1 - i / glow_radius))
        glow_surf = pygame.Surface(font.size(text), pygame.SRCALPHA)
        text_render = font.render(text, True, (*glow_color, alpha))
        glow_surf.blit(text_render, (0, 0))
        surface.blit(glow_surf, glow_surf.get_rect(center=(pos[0] - i, pos[1] - i)))
    text_surf = font.render(text, True, hex_to_rgb(color))
    surface.blit(text_surf, text_surf.get_rect(center=pos))


def draw_rounded_panel(surface: pygame.Surface, rect: pygame.Rect,
                       fill_color: tuple | str, border_color: tuple | str = None,
                       border_width: int = 2, radius: int = None):
    """Draw polished rounded panel with shadow"""
    if radius is None:
        radius = s(8)
    # Shadow
    shadow_rect = rect.move(s(2), s(2))
    shadow_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    pygame.draw.rect(shadow_surf, (0, 0, 0, 40), (0, 0, rect.width, rect.height),
                     border_radius=radius)
    surface.blit(shadow_surf, shadow_rect)
    # Fill
    pygame.draw.rect(surface, hex_to_rgb(fill_color), rect, border_radius=radius)
    # Border
    if border_color:
        pygame.draw.rect(surface, hex_to_rgb(border_color), rect, border_width, border_radius=radius)


def draw_button(surface: pygame.Surface, rect: pygame.Rect, text: str,
                font: pygame.font.Font, text_color: tuple | str,
                bg_color: tuple | str, border_color: tuple | str = None,
                is_hover: bool = False):
    """Draw polished button with hover effect"""
    # Background
    if is_hover:
        hover_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        hover_surf.fill((255, 255, 255, 20))
        surface.blit(hover_surf, rect)
    pygame.draw.rect(surface, hex_to_rgb(bg_color), rect, border_radius=s(12))
    # Border
    if border_color:
        pygame.draw.rect(surface, hex_to_rgb(border_color), rect, s(2), border_radius=s(12))
    # Text
    text_surf = font.render(text, True, hex_to_rgb(text_color))
    surface.blit(text_surf, text_surf.get_rect(center=rect.center))


def draw_exit_button(surface: pygame.Surface, mouse_pos: tuple, font_size: int = s(26)):
    """Draw standard red exit button, returns its rect"""
    btn_w, btn_h = s(80), s(36)
    btn_x, btn_y = s(15), s(10)
    btn_rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)

    is_hover = btn_rect.collidepoint(mouse_pos)
    bg_color = '#FF4444' if is_hover else '#CC3333'
    pygame.draw.rect(surface, hex_to_rgb(bg_color), btn_rect, border_radius=s(6))
    pygame.draw.rect(surface, hex_to_rgb('#FFE066'), btn_rect, 2, border_radius=s(6))

    font = get_font(font_size)
    text_surf = font.render('退出', True, hex_to_rgb('#FFF8DC'))
    surface.blit(text_surf, text_surf.get_rect(center=btn_rect.center))
    return btn_rect


def draw_game_border(surface: pygame.Surface):
    """Draw standard gold/red game border"""
    pygame.draw.rect(surface, hex_to_rgb('#FF5E5E'),
                     (s(4), s(4), WINDOW_WIDTH - s(8), WINDOW_HEIGHT - s(8)), 2)


def draw_result_overlay(surface: pygame.Surface, alpha: float, result_text: str,
                        result_font: pygame.font.Font, result_color: tuple | str,
                        sub_text: str = None, sub_font: pygame.font.Font = None,
                        sub_color: tuple | str = None):
    """Full-screen dark overlay with centered glowing text"""
    overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, int(alpha * 255)))
    surface.blit(overlay, (0, 0))

    cx, cy = WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2
    draw_text_with_shadow(surface, result_text, result_font,
                          result_color, (cx, cy))

    if sub_text and sub_font:
        sub_surf = sub_font.render(sub_text, True, hex_to_rgb(sub_color or result_color))
        surface.blit(sub_surf, sub_surf.get_rect(center=(cx, cy + s(50))))


def draw_breathing_hint(surface: pygame.Surface, text: str, font: pygame.font.Font,
                        color: tuple | str, pos: tuple, time_val: float, speed: float = 3):
    """Draw text with sinusoidal alpha animation"""
    alpha = int(128 + 127 * math.sin(time_val * speed))
    text_surf = font.render(text, True, hex_to_rgb(color))
    text_surf.set_alpha(alpha)
    surface.blit(text_surf, text_surf.get_rect(center=pos))


def draw_progress_bar(surface: pygame.Surface, rect: pygame.Rect, progress: float,
                      bg_color: tuple | str = '#333', fill_color: tuple | str = '#2ECC71',
                      border_color: tuple | str = None, border_width: int = 2,
                      radius: int = None):
    """Draw smooth progress bar with highlight"""
    if radius is None:
        radius = s(4)
    progress = clamp(progress, 0, 1)
    # Background
    pygame.draw.rect(surface, hex_to_rgb(bg_color), rect, border_radius=radius)
    # Fill
    fill_rect = pygame.Rect(rect.x, rect.y, int(rect.width * progress), rect.height)
    if fill_rect.width > 0:
        pygame.draw.rect(surface, hex_to_rgb(fill_color), fill_rect, border_radius=radius)
        # Highlight line
        pygame.draw.rect(surface, (255, 255, 255, 40),
                        (fill_rect.x, fill_rect.y, fill_rect.width, fill_rect.height // 2),
                        border_radius=radius)
    # Border
    if border_color:
        pygame.draw.rect(surface, hex_to_rgb(border_color), rect, border_width, border_radius=radius)
