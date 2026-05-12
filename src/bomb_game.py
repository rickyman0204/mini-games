"""Bomb Defusal game - cut the right wire to win"""
import random
import math
import pygame
from pygame.math import Vector2

from src.settings import (
    COLORS, WINDOW_WIDTH, WINDOW_HEIGHT, BOMB_WIRES,
    BOMB_REWARD, BOMB_CUT_ANIM_DURATION, BOMB_REVEAL_DURATION
)
from src.utils import ease_out_quad, ease_out_back, hex_to_rgb


class Wire:
    """A wire in the bomb game"""

    _label_font = None

    @classmethod
    def _get_label_font(cls):
        if cls._label_font is None:
            cls._label_font = pygame.font.SysFont('microsoftyahei', 14, bold=True)
        return cls._label_font

    def __init__(self, color: str, index: int, x: int):
        self.color = color
        self.index = index
        self.x = x
        self.is_safe = False  # Will be set randomly per game
        self.is_cut = False
        self.cut_progress = 0.0  # 0-1 animation progress
        self.start_y = 200
        self.end_y = 400
        self.cut_y = 320  # Where the wire is cut
        self.color_hex = self._get_color_hex()

    def _get_color_hex(self) -> str:
        """Get hex color for wire type"""
        colors = {
            'green': '#33FF33',
            'yellow': '#FFCC00',
            'blue': '#3366FF',
        }
        return colors.get(self.color, '#FFFFFF')

    def handle_click(self, mouse_pos: tuple) -> bool:
        """Check if click is on this wire. Returns True if clicked."""
        if self.is_cut:
            return False

        # Wire area is a vertical strip
        wire_rect = pygame.Rect(self.x - 30, self.start_y - 20, 60, self.end_y - self.start_y + 40)
        if wire_rect.collidepoint(mouse_pos):
            return True
        return False

    def cut(self):
        """Start cutting animation"""
        self.is_cut = True
        self.cut_progress = 0.0

    def update(self, dt: float):
        """Update wire state"""
        if self.is_cut and self.cut_progress < 1.0:
            self.cut_progress = min(1.0, self.cut_progress + dt / BOMB_CUT_ANIM_DURATION)

    def draw(self, surface: pygame.Surface):
        """Draw the wire"""
        color = hex_to_rgb(self.color_hex)

        if self.is_cut:
            # Draw top part (connected to bomb)
            top_end_y = self.cut_y + self.cut_progress * 50
            pygame.draw.line(surface, color, (self.x, self.start_y), (self.x, top_end_y), 8)

            # Draw bottom part (falling)
            if self.cut_progress > 0.3:
                fall_offset = (self.cut_progress - 0.3) * 80
                pygame.draw.line(surface, color,
                               (self.x, self.cut_y + 50),
                               (self.x + 10, self.cut_y + 80 + fall_offset), 6)

            # Draw cut sparks
            if self.cut_progress < 0.5:
                spark_count = 5
                for i in range(spark_count):
                    angle = random.uniform(0, math.pi * 2)
                    distance = random.uniform(5, 20) * self.cut_progress
                    spark_x = self.x + math.cos(angle) * distance
                    spark_y = self.cut_y + math.sin(angle) * distance
                    spark_size = int(3 * (1 - self.cut_progress * 2))
                    if spark_size > 0:
                        pygame.draw.circle(surface, (255, 255, 200),
                                         (int(spark_x), int(spark_y)), spark_size)
        else:
            # Draw full wire with curve
            points = []
            steps = 20
            for i in range(steps + 1):
                t = i / steps
                y = self.start_y + (self.end_y - self.start_y) * t
                x = self.x + math.sin(t * math.pi * 2) * 8
                points.append((int(x), int(y)))

            # Draw wire
            for i in range(len(points) - 1):
                pygame.draw.line(surface, color, points[i], points[i + 1], 8)

            # Draw connector at top
            pygame.draw.circle(surface, (150, 150, 150), (self.x, self.start_y), 6)

            # Color label
            color_name = {'green': '绿', 'yellow': '黄', 'blue': '蓝'}[self.color]
            label = Wire._get_label_font().render(color_name, True, (255, 255, 255))
            label_rect = label.get_rect(center=(self.x, self.start_y - 30))
            surface.blit(label, label_rect)


class BombGame:
    """The bomb defusal game component"""

    def __init__(self, wallet):
        self.wallet = wallet
        self.wires: list[Wire] = []
        self.safe_wire_index = -1
        self.game_state = 'waiting'  # 'waiting' -> 'cutting' -> 'reveal' -> 'done'
        self.result_text = ''
        self.result_color = COLORS['gold']
        self.result_timer = 0.0
        self.timer_show = False
        self.sparkle_particles = []

        self._timer_font = pygame.font.SysFont('monospace', 22, bold=True)
        self._bomb_font = pygame.font.SysFont('microsoftyahei', 20, bold=True)
        self._result_font = pygame.font.SysFont('microsoftyahei', 32, bold=True)

    def reset(self):
        """Start a new bomb round"""
        self.game_state = 'waiting'
        self.result_text = ''
        self.result_timer = 0.0
        self.timer_show = False

        # Randomly pick safe wire
        self.safe_wire_index = random.randint(0, 2)

        # Create wires
        wire_spacing = 100
        start_x = WINDOW_WIDTH // 2 - wire_spacing
        self.wires = []
        for i, wire_color in enumerate(BOMB_WIRES):
            x = start_x + i * wire_spacing
            wire = Wire(wire_color, i, x)
            wire.is_safe = (i == self.safe_wire_index)
            self.wires.append(wire)

    def handle_click(self, mouse_pos: tuple) -> bool:
        """Handle wire click. Returns True if a wire was clicked."""
        if self.game_state != 'waiting':
            return False

        for wire in self.wires:
            if wire.handle_click(mouse_pos):
                self._cut_wire(wire)
                return True
        return False

    def _cut_wire(self, wire: Wire):
        """Cut a wire"""
        self.game_state = 'cutting'
        wire.cut()

    def update(self, dt: float):
        """Update game state"""
        for wire in self.wires:
            wire.update(dt)

        if self.game_state == 'cutting':
            # Check if cut animation is mostly done
            cut_wire = next((w for w in self.wires if w.is_cut and w.cut_progress >= 1.0), None)
            if cut_wire:
                self.game_state = 'reveal'
                self.result_timer = 0.0

                if cut_wire.is_safe:
                    self.result_text = f'成功！+¥{BOMB_REWARD}!'
                    self.result_color = COLORS['gold']
                    self.wallet.add(BOMB_REWARD)
                    # Add celebration sparkles
                    for _ in range(20):
                        self.sparkle_particles.append({
                            'x': cut_wire.x + random.uniform(-30, 30),
                            'y': cut_wire.cut_y + random.uniform(-30, 30),
                            'vx': random.uniform(-100, 100),
                            'vy': random.uniform(-150, -50),
                            'life': random.uniform(0.5, 1.5),
                            'max_life': random.uniform(0.5, 1.5),
                            'color': hex_to_rgb(COLORS['gold']),
                        })
                else:
                    self.result_text = '错误！炸弹还在！'
                    self.result_color = COLORS['red_primary']
                    # Add warning red sparkles
                    for _ in range(15):
                        self.sparkle_particles.append({
                            'x': cut_wire.x + random.uniform(-30, 30),
                            'y': cut_wire.cut_y + random.uniform(-30, 30),
                            'vx': random.uniform(-50, 50),
                            'vy': random.uniform(-50, 50),
                            'life': random.uniform(0.3, 0.8),
                            'max_life': random.uniform(0.3, 0.8),
                            'color': (255, 50, 50),
                        })

        if self.game_state == 'reveal':
            self.result_timer += dt
            if self.result_timer >= BOMB_REVEAL_DURATION:
                self.game_state = 'done'

        if self.game_state == 'done':
            self.timer_show = True
            self.result_timer += dt

        # Update sparkle particles
        new_particles = []
        for p in self.sparkle_particles:
            p['life'] -= dt
            if p['life'] > 0:
                p['x'] += p['vx'] * dt
                p['y'] += p['vy'] * dt
                p['vy'] += 100 * dt  # gravity
                new_particles.append(p)
        self.sparkle_particles = new_particles

    def draw(self, surface: pygame.Surface):
        """Draw the bomb game"""
        self._draw_bomb(surface)
        self._draw_wires(surface)
        self._draw_result(surface)
        self._draw_sparkles(surface)

    def _draw_bomb(self, surface: pygame.Surface):
        """Draw the bomb body at top"""
        cx = WINDOW_WIDTH // 2
        bomb_y = 150

        shadow_rect = pygame.Rect(cx - 82, bomb_y - 28, 164, 64)
        s_surf = pygame.Surface((shadow_rect.width, shadow_rect.height), pygame.SRCALPHA)
        s_surf.fill((0, 0, 0, 60))
        surface.blit(s_surf, shadow_rect)

        bomb_rect = pygame.Rect(cx - 80, bomb_y - 30, 160, 60)
        bomb_s = pygame.Surface((bomb_rect.width, bomb_rect.height), pygame.SRCALPHA)
        bomb_s.fill((60, 60, 70, 200))
        surface.blit(bomb_s, bomb_rect)
        pygame.draw.rect(surface, (120, 120, 130), bomb_rect, 3, border_radius=12)

        body_hl = pygame.Rect(cx - 70, bomb_y - 25, 60, 20)
        hl_s = pygame.Surface((body_hl.width, body_hl.height), pygame.SRCALPHA)
        hl_s.fill((255, 255, 255, 25))
        surface.blit(hl_s, body_hl)

        if self.timer_show:
            seconds_left = max(0, 10 - self.result_timer)
            timer_text = self._timer_font.render(f'{int(seconds_left):02d}', True, (255, 50, 50))
            timer_rect = timer_text.get_rect(center=(cx, bomb_y))
            surface.blit(timer_text, timer_rect)
        else:
            label = self._bomb_font.render('炸弹', True, (255, 100, 100))
            label_rect = label.get_rect(center=(cx, bomb_y))
            surface.blit(label, label_rect)

        for wire in self.wires:
            pygame.draw.line(surface, (0, 0, 0, 60),
                           (wire.x + 1, wire.start_y + 1),
                           (wire.x + 1, bomb_y + 32), 9)
            pygame.draw.line(surface, hex_to_rgb(wire.color_hex),
                           (wire.x, wire.start_y),
                           (wire.x, bomb_y + 30), 8)

    def _draw_wires(self, surface: pygame.Surface):
        """Draw wires"""
        for wire in self.wires:
            wire.draw(surface)

    def _draw_result(self, surface: pygame.Surface):
        """Draw result text with shadow"""
        if self.game_state in ('reveal', 'done') and self.result_text:
            shadow = self._result_font.render(self.result_text, True, (0, 0, 0))
            shadow.set_alpha(100)
            s_r = shadow.get_rect(center=(WINDOW_WIDTH // 2 + 2, 452))
            surface.blit(shadow, s_r)

            text_surf = self._result_font.render(self.result_text, True, hex_to_rgb(self.result_color))
            rect = text_surf.get_rect(center=(WINDOW_WIDTH // 2, 450))
            surface.blit(text_surf, rect)

    def _draw_sparkles(self, surface: pygame.Surface):
        """Draw sparkle particles"""
        for p in self.sparkle_particles:
            life_ratio = p['life'] / p['max_life']
            size = int(3 * life_ratio)
            alpha = int(255 * life_ratio)
            if size > 0:
                spark_surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
                spark_surf.set_alpha(alpha)
                pygame.draw.circle(spark_surf, p['color'], (size, size), size)
                surface.blit(spark_surf, (int(p['x']) - size, int(p['y']) - size))
