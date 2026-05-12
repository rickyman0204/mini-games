"""Lucky Wheel Game - spin for prizes"""
import math
import random
import pygame

from src.settings import (
    WINDOW_WIDTH, WINDOW_HEIGHT, COLORS,
)
from src.utils import (
    s, get_font, hex_to_rgb, get_mouse_pos, clamp, ease_out_cubic,
    draw_button, draw_text_with_shadow, draw_exit_button, draw_game_border,
    draw_breathing_hint, draw_result_overlay, draw_progress_bar, ease_out_quad
)
from src.particles import ParticleEmitter

# Wheel segment definition: (label, value, color, type)
SEGMENTS = [
    {'label': '\u8c22\u8c22\u60e0\u987e', 'value': 0, 'color': '#555555', 'accent': '#333333', 'type': 'nothing'},
    {'label': '50\u91d1\u5e01', 'value': 50, 'color': '#4CAF50', 'accent': '#2E7D32', 'type': 'money'},
    {'label': '\u8c22\u8c22\u60e0\u987e', 'value': 0, 'color': '#555555', 'accent': '#333333', 'type': 'nothing'},
    {'label': '100\u91d1\u5e01', 'value': 100, 'color': '#2196F3', 'accent': '#1565C0', 'type': 'money'},
    {'label': '50\u91d1\u5e01', 'value': 50, 'color': '#4CAF50', 'accent': '#2E7D32', 'type': 'money'},
    {'label': '200\u91d1\u5e01', 'value': 200, 'color': '#FF9800', 'accent': '#E65100', 'type': 'money'},
    {'label': '100~300\u91d1\u5e01', 'value': 0, 'color': '#9C27B0', 'accent': '#6A1B9A', 'type': 'free_money'},
    {'label': '150\u91d1\u5e01', 'value': 150, 'color': '#FF5722', 'accent': '#BF360C', 'type': 'money'},
    {'label': '100\u91d1\u5e01', 'value': 100, 'color': '#2196F3', 'accent': '#1565C0', 'type': 'money'},
    {'label': '50\u91d1\u5e01', 'value': 50, 'color': '#4CAF50', 'accent': '#2E7D32', 'type': 'money'},
]

# Spin animation
SPIN_DURATION = 4.0
SPIN_TOTAL_TURNS = 6  # Full rotations before slowing

# Visuals (scaled)
WHEEL_RADIUS = s(180)
WHEEL_CENTER_Y = s(300)


class WheelGame:
    """Lucky wheel: spin for prizes"""

    def __init__(self, wallet):
        self.wallet = wallet
        self.particles = ParticleEmitter()

        # Game state: 'idle', 'spinning', 'result', 'done'
        self.game_state = 'idle'

        # Wheel
        self.angle = 0.0  # Current rotation angle (radians)
        self.target_angle = 0.0
        self.spin_timer = 0.0
        self.spin_duration = SPIN_DURATION
        self.start_angle = 0.0

        # Result
        self.result_segment = None
        self.result_value = 0
        self.result_label = ''
        self.result_type = ''
        self.result_timer = 0.0
        self.won_free_scratch = False
        self.extra_spin = False

        # Buttons
        self.spin_btn_rect = pygame.Rect(0, 0, 0, 0)
        self.exit_btn_rect = pygame.Rect(0, 0, 0, 0)

        # Fonts (scaled by 1.6x)
        self.font_title = get_font(58, bold=True)
        self.font_big = get_font(70, bold=True)
        self.font_small = get_font(26)
        self.font_btn = get_font(38, bold=True)
        self.font_seg = get_font(29, bold=True)

        self._calc_layout()

    def _calc_layout(self):
        self.wheel_center_x = WINDOW_WIDTH // 2
        self.wheel_center_y = WHEEL_CENTER_Y

    def reset(self):
        self.game_state = 'idle'
        self.angle = 0.0
        self.target_angle = 0.0
        self.spin_timer = 0.0
        self.result_segment = None
        self.result_value = 0
        self.result_label = ''
        self.result_type = ''
        self.result_timer = 0.0
        self.won_free_scratch = False
        self.extra_spin = False
        self.particles.clear()

    def _determine_result(self):
        """Randomly pick a segment based on segment count"""
        idx = random.randint(0, len(SEGMENTS) - 1)
        return idx

    def handle_click(self, mouse_pos: tuple):
        if self.exit_btn_rect.collidepoint(mouse_pos):
            self.game_state = 'done'
            return

        if self.game_state == 'idle':
            if self.spin_btn_rect.collidepoint(mouse_pos):
                self._spin()
        elif self.game_state == 'result' and self.result_timer >= 0.5:
            if self.extra_spin:
                self._spin()
            else:
                self.game_state = 'done'

    def _spin(self):
        self.game_state = 'spinning'
        self.won_free_scratch = False
        self.won_free_game_id = None
        self.extra_spin = False
        self._tick_cooldown = 0.0

        # Determine result first
        seg_idx = self._determine_result()
        self.result_segment = SEGMENTS[seg_idx]
        self.result_value = self.result_segment['value']
        self.result_label = self.result_segment['label']
        self.result_type = self.result_segment['type']

        # Calculate target angle: pointer is at top (270 degrees = 3pi/2)
        # Segment i starts at angle i * segment_angle
        # We want the center of segment seg_idx to align with top pointer
        seg_angle = (2 * math.pi) / len(SEGMENTS)
        seg_center = seg_idx * seg_angle + seg_angle / 2
        # Pointer is at top = -pi/2 in our coordinate system
        target = -math.pi / 2 - seg_center
        # Add full rotations
        turns = SPIN_TOTAL_TURNS + random.uniform(0, 0.5)
        self.target_angle = target - turns * 2 * math.pi

        self.start_angle = self.angle
        self.spin_timer = 0.0

    def update(self, dt: float):
        self.particles.update(dt)

        if self.game_state == 'spinning':
            self.spin_timer += dt
            self._tick_cooldown -= dt

            # Tick sound as wheel passes segments (disabled - too frequent)
            pass

            progress = clamp(self.spin_timer / self.spin_duration, 0, 1)
            eased = ease_out_cubic(progress)

            self.angle = self.start_angle + (self.target_angle - self.start_angle) * eased

            if progress >= 1.0:
                self.game_state = 'result'
                self.result_timer = 0.0
                self.angle = self.target_angle

                # Apply result
                if self.result_type == 'money':
                    self.wallet.add(self.result_value)
                    self.particles.emit_confetti(
                        (self.wheel_center_x, self.wheel_center_y),
                        40, ['#FFD700', '#FFFFFF', self.result_segment['color']],
                        lifetime=2.0
                    )
                elif self.result_type == 'nothing':
                    pass
                elif self.result_type == 'free_money':
                    free_money = random.randint(100, 300)
                    self.result_label = f'{free_money}\u91d1\u5e01'
                    self.result_value = free_money
                    self.wallet.add(free_money)
                    self.particles.emit_confetti(
                        (self.wheel_center_x, self.wheel_center_y),
                        30, ['#9C27B0', '#FFD700', '#FFFFFF'],
                        lifetime=2.0
                    )
                elif self.result_type == 'respins':
                    self.extra_spin = True

    def draw(self, surface: pygame.Surface):
        surface.fill(hex_to_rgb(COLORS['bg_primary']))

        draw_game_border(surface)
        self._draw_title(surface)
        self._draw_wheel(surface)
        self._draw_pointer(surface)

        if self.game_state == 'idle':
            self._draw_spin_button(surface)

        if self.game_state == 'result':
            self._draw_result_overlay(surface)

        # Exit button (using utility function)
        mouse_pos = get_mouse_pos()
        self.exit_btn_rect = draw_exit_button(surface, mouse_pos, font_size=s(26))

        self.particles.draw(surface)

    def _draw_title(self, surface: pygame.Surface):
        draw_text_with_shadow(surface, '\u5e78\u8fd0\u8f6c\u76d8', self.font_title,
                             COLORS['gold'], (WINDOW_WIDTH // 2, s(24)))

    def _draw_wheel(self, surface: pygame.Surface):
        cx = self.wheel_center_x
        cy = self.wheel_center_y
        r = WHEEL_RADIUS
        seg_count = len(SEGMENTS)
        seg_angle = (2 * math.pi) / seg_count

        # Draw each segment as a polygon arc
        for i, seg in enumerate(SEGMENTS):
            start_a = self.angle + i * seg_angle
            end_a = start_a + seg_angle

            # Build polygon points
            points = [(cx, cy)]
            steps = 20
            for st in range(steps + 1):
                a = start_a + (end_a - start_a) * st / steps
                px = cx + r * math.cos(a)
                py = cy + r * math.sin(a)
                points.append((px, py))

            color = hex_to_rgb(seg['color'])
            pygame.draw.polygon(surface, color, points)

            # Border line
            line_a = start_a
            lx1 = cx + s(5) * math.cos(line_a)
            ly1 = cy + s(5) * math.sin(line_a)
            lx2 = cx + r * math.cos(line_a)
            ly2 = cy + r * math.sin(line_a)
            pygame.draw.line(surface, hex_to_rgb(COLORS['bg_primary']), (lx1, ly1), (lx2, ly2), s(2))

        # Outer ring
        pygame.draw.circle(surface, hex_to_rgb(COLORS['gold']), (cx, cy), r + s(4), s(4))
        pygame.draw.circle(surface, hex_to_rgb(COLORS['gold_dark']), (cx, cy), r, s(3))

        # Center hub
        hub_r = s(35)
        pygame.draw.circle(surface, hex_to_rgb(COLORS['bg_secondary']), (cx, cy), hub_r + s(3))
        pygame.draw.circle(surface, hex_to_rgb(COLORS['gold']), (cx, cy), hub_r)
        pygame.draw.circle(surface, hex_to_rgb(COLORS['gold_light']), (cx, cy), hub_r - s(4), s(2))

        # Segment labels (only if not spinning too fast)
        is_slow = self.game_state == 'result' or self.game_state == 'idle'
        if is_slow:
            for i, seg in enumerate(SEGMENTS):
                start_a = self.angle + i * seg_angle
                mid_a = start_a + seg_angle / 2
                label_r = r * 0.65
                lx = cx + label_r * math.cos(mid_a)
                ly = cy + label_r * math.sin(mid_a)

                label_surf = self.font_seg.render(seg['label'], True, (255, 255, 255))
                # Dark outline for readability
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    shadow = self.font_seg.render(seg['label'], True, (0, 0, 0))
                    surface.blit(shadow, (lx - shadow.get_width() // 2 + dx, ly - shadow.get_height() // 2 + dy))
                surface.blit(label_surf, (lx - label_surf.get_width() // 2, ly - label_surf.get_height() // 2))

        # Decorative dots around edge
        for i in range(seg_count * 3):
            dot_a = self.angle + i * (2 * math.pi) / (seg_count * 3)
            dot_r = r + s(12)
            dx = cx + dot_r * math.cos(dot_a)
            dy = cy + dot_r * math.sin(dot_a)
            dot_color = hex_to_rgb(COLORS['gold']) if i % 2 == 0 else hex_to_rgb(COLORS['gold_dark'])
            pygame.draw.circle(surface, dot_color, (int(dx), int(dy)), s(3))

    def _draw_pointer(self, surface: pygame.Surface):
        cx = self.wheel_center_x
        cy = self.wheel_center_y
        pointer_h = s(30)
        pointer_w = s(14)

        # Triangle pointing down
        pygame.draw.polygon(surface, hex_to_rgb('#FF4444'), [
            (cx, cy - WHEEL_RADIUS - s(4)),
            (cx - pointer_w, cy - WHEEL_RADIUS - pointer_h - s(4)),
            (cx + pointer_w, cy - WHEEL_RADIUS - pointer_h - s(4)),
        ])
        pygame.draw.polygon(surface, hex_to_rgb('#FF6666'), [
            (cx, cy - WHEEL_RADIUS - s(4)),
            (cx - pointer_w // 2, cy - WHEEL_RADIUS - pointer_h - s(4)),
            (cx + pointer_w // 2, cy - WHEEL_RADIUS - pointer_h - s(4)),
        ])

    def _draw_spin_button(self, surface: pygame.Surface):
        btn_w, btn_h = s(180), s(55)
        btn_x = WINDOW_WIDTH // 2
        btn_y = self.wheel_center_y + WHEEL_RADIUS + s(40)
        self.spin_btn_rect = pygame.Rect(btn_x - btn_w // 2, btn_y, btn_w, btn_h)

        mouse_pos = get_mouse_pos()
        is_hover = self.spin_btn_rect.collidepoint(mouse_pos)

        bg_color = hex_to_rgb(COLORS['gold']) if is_hover else hex_to_rgb(COLORS['gold_dark'])
        pygame.draw.rect(surface, bg_color, self.spin_btn_rect, border_radius=s(12))
        pygame.draw.rect(surface, hex_to_rgb(COLORS['gold_light']), self.spin_btn_rect, s(2), border_radius=s(12))

        btn_surf = self.font_btn.render('\u5f00\u59cb\u65cb\u8f6c', True, hex_to_rgb('#2D1515'))
        surface.blit(btn_surf, btn_surf.get_rect(center=(btn_x, btn_y + btn_h // 2)))

    def _draw_result_overlay(self, surface: pygame.Surface):
        if self.result_timer < 0.2:
            return

        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        progress = clamp((self.result_timer - 0.2) / 0.5, 0, 1)
        eased = ease_out_cubic(progress)
        overlay.fill((0, 0, 0, int(140 * eased)))
        surface.blit(overlay, (0, 0))

        if self.result_type == 'nothing':
            result_text = '\u8c22\u8c22\u60e0\u987e...'
            color = hex_to_rgb(COLORS['text_secondary'])
        elif self.result_type == 'money':
            result_text = f'\u606d\u559c\u83b7\u5f97 \xa5{self.result_value}\uff01'
            color = hex_to_rgb(COLORS['gold'])
        elif self.result_type == 'free_money':
            result_text = f'\u606d\u559c\u83b7\u5f97 \xa5{self.result_value}\uff01'
            color = hex_to_rgb('#9C27B0')
        elif self.result_type == 'respins':
            result_text = f'\u606d\u559c\u83b7\u5f97 \xa5{self.result_value}\uff01'
            color = hex_to_rgb('#FF5722')

        result_surf = self.font_big.render(result_text, True, color)
        surface.blit(result_surf, result_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - s(20))))

        if self.result_timer >= 0.5:
            if self.extra_spin:
                back_text = '\u70b9\u51fb\u6309\u94ae\u514d\u8d39\u518d\u8f6c'
            else:
                back_text = '\u70b9\u51fb\u4efb\u610f\u4f4d\u7f6e\u8fd4\u56de'
            draw_breathing_hint(surface, back_text, self.font_small,
                               COLORS['text_secondary'],
                               (WINDOW_WIDTH // 2, WINDOW_HEIGHT - s(50)),
                               self.result_timer * 2, speed=4)
