"""Random Math Equation Game - stop the changing equation, win based on result"""
import math
import random
import pygame

from src.settings import (
    WINDOW_WIDTH, WINDOW_HEIGHT, COLORS,
    MATH_ENTRY_COST, MATH_RESULT_DURATION
)
from src.utils import get_mouse_pos, clamp, ease_out_quad, hex_to_rgb
from src.particles import ParticleEmitter


class MathGame:
    """Random math equation game - stop the equation to see your result"""

    def __init__(self, wallet):
        self.wallet = wallet
        self.particles = ParticleEmitter()

        # Game state: 'idle', 'running', 'result', 'done'
        self.game_state = 'idle'

        # Equation
        self.num_a = 1
        self.num_b = 1
        self.operator = '+'
        self.result = 0

        # Running state
        self.change_timer = 0.0
        self.change_interval = 0.15

        # Result
        self.result_timer = 0.0
        self.shake_intensity = 0.0
        self.water_offset = 0.0
        self.particle_emitted = False

        # Buttons
        self.stop_btn_rect = pygame.Rect(0, 0, 0, 0)
        self.exit_btn_rect = pygame.Rect(0, 0, 0, 0)

        # Fonts
        self.font_title = pygame.font.SysFont('microsoftyahei', 36, bold=True)
        self.font_big = pygame.font.SysFont('microsoftyahei', 64, bold=True)
        self.font_info = pygame.font.SysFont('microsoftyahei', 20)
        self.font_small = pygame.font.SysFont('microsoftyahei', 16)
        self.font_eq = pygame.font.SysFont('microsoftyahei', 48, bold=True)
        self.font_btn = pygame.font.SysFont('microsoftyahei', 24, bold=True)

    def reset(self):
        self.game_state = 'idle'
        self.num_a = random.randint(1, 9)
        self.num_b = random.randint(1, 9)
        self.operator = random.choice(['+', '-', '*', '/'])
        self.result = 0
        self.change_timer = 0.0
        self.result_timer = 0.0
        self.shake_intensity = 0.0
        self.water_offset = 0.0
        self.particle_emitted = False
        self.particles.clear()

    def handle_click(self, mouse_pos: tuple):
        if self.exit_btn_rect.collidepoint(mouse_pos):
            self.game_state = 'done'
            return

        if self.game_state == 'idle':
            if self.stop_btn_rect.collidepoint(mouse_pos):
                self._start_running()
        elif self.game_state == 'running':
            if self.stop_btn_rect.collidepoint(mouse_pos):
                self._stop_equation()
        elif self.game_state == 'result' and self.result_timer >= 1.0:
            self.game_state = 'done'

    def _start_running(self):
        self.game_state = 'running'
        self.change_timer = 0.0
        self._randomize_equation()

    def _stop_equation(self):
        self.game_state = 'result'
        self.result_timer = 0.0
        self.shake_intensity = 8.0

        # Calculate result (rounded up)
        if self.operator == '+':
            self.result = math.ceil(self.num_a + self.num_b)
        elif self.operator == '-':
            self.result = math.ceil(self.num_a - self.num_b)
        elif self.operator == '*':
            self.result = math.ceil(self.num_a * self.num_b)
        elif self.operator == '/':
            if self.num_b == 0:
                self.num_b = 1
            self.result = math.ceil(self.num_a / self.num_b)

        # Reward based on result
        reward = max(0, self.result * 3)
        self._reward_amount = reward
        self.wallet.add(reward)

        if reward > 0:
            self.particles.emit_burst(
                (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 50),
                40, hex_to_rgb('#FFD700'),
                speed_range=(100, 250), lifetime=2.0, size=4
            )

    def _randomize_equation(self):
        self.num_a = random.randint(1, 9)
        self.num_b = random.randint(1, 9)
        self.operator = random.choice(['+', '-', '*', '/'])
        # Avoid division by zero
        if self.operator == '/' and self.num_b == 0:
            self.num_b = 1

    def update(self, dt: float):
        self.particles.update(dt)
        self.water_offset += dt * 2
        self.shake_intensity *= (1 - dt * 6)

        if self.game_state == 'running':
            self.change_timer += dt
            if self.change_timer >= self.change_interval:
                self.change_timer = 0.0
                self._randomize_equation()

        elif self.game_state == 'result':
            self.result_timer += dt

    def draw(self, surface: pygame.Surface):
        surface.fill(hex_to_rgb(COLORS['bg_primary']))
        self._draw_border(surface)

        # Title
        shadow = self.font_title.render('随机算式', True, (25, 20, 10))
        surface.blit(shadow, shadow.get_rect(center=(WINDOW_WIDTH // 2 + 2, 20)))
        title_surf = self.font_title.render('随机算式', True, hex_to_rgb(COLORS['gold']))
        surface.blit(title_surf, title_surf.get_rect(center=(WINDOW_WIDTH // 2, 18)))

        # Rule info
        info_surf = self.font_small.render(
            '算式快速变化，点击按钮停止，奖金=结果×3(向上取整)',
            True, hex_to_rgb(COLORS['text_secondary']))
        surface.blit(info_surf, info_surf.get_rect(center=(WINDOW_WIDTH // 2, 46)))

        # Shake offset
        ox, oy = 0, 0
        if self.shake_intensity > 0.5:
            ox = random.uniform(-self.shake_intensity, self.shake_intensity)
            oy = random.uniform(-self.shake_intensity, self.shake_intensity)

        # Equation display
        self._draw_equation(surface, ox, oy)

        # Stop button
        self._draw_stop_button(surface)

        # Exit button
        self._draw_exit_button(surface)

        # Result overlay
        if self.game_state == 'result':
            self._draw_result_overlay(surface)

        self.particles.draw(surface)

    def _draw_border(self, surface: pygame.Surface):
        pygame.draw.rect(surface, hex_to_rgb(COLORS['red_primary']),
                         (4, 4, WINDOW_WIDTH - 8, WINDOW_HEIGHT - 8), 2)

    def _draw_equation(self, surface: pygame.Surface, ox: float, oy: float):
        eq_x = WINDOW_WIDTH // 2 + ox
        eq_y = WINDOW_HEIGHT // 2 - 60 + oy

        # Background box
        box_w, box_h = 350, 100
        bg_color = hex_to_rgb(COLORS['card_bg'])
        border_color = hex_to_rgb(COLORS['gold']) if self.game_state == 'result' else hex_to_rgb(COLORS['gold_dark'])

        pygame.draw.rect(surface, bg_color,
                         (eq_x - box_w // 2, eq_y - box_h // 2, box_w, box_h),
                         border_radius=15)
        pygame.draw.rect(surface, border_color,
                         (eq_x - box_w // 2, eq_y - box_h // 2, box_w, box_h),
                         3, border_radius=15)

        # Equation text
        op_symbols = {'+': '+', '-': '-', '*': '×', '/': '÷'}
        eq_text = f'{self.num_a} {op_symbols.get(self.operator, self.operator)} {self.num_b}'
        eq_surf = self.font_big.render(eq_text, True, hex_to_rgb(COLORS['gold']))
        surface.blit(eq_surf, eq_surf.get_rect(center=(eq_x, eq_y)))

    def _draw_stop_button(self, surface: pygame.Surface):
        btn_w, btn_h = 200, 55
        btn_x = WINDOW_WIDTH // 2
        btn_y = WINDOW_HEIGHT // 2 + 80
        self.stop_btn_rect = pygame.Rect(btn_x - btn_w // 2, btn_y, btn_w, btn_h)

        mouse_pos = get_mouse_pos()
        is_hover = self.stop_btn_rect.collidepoint(mouse_pos)

        if self.game_state == 'running':
            bg_color = hex_to_rgb(COLORS['red_primary']) if is_hover else tuple(int(c * 0.8) for c in hex_to_rgb(COLORS['red_primary']))
        elif self.game_state == 'idle':
            bg_color = hex_to_rgb(COLORS['success']) if is_hover else tuple(int(c * 0.8) for c in hex_to_rgb(COLORS['success']))
        else:
            bg_color = tuple(int(c * 0.4) for c in hex_to_rgb(COLORS['red_primary']))

        pygame.draw.rect(surface, bg_color, self.stop_btn_rect, border_radius=12)
        pygame.draw.rect(surface, hex_to_rgb(COLORS['gold']), self.stop_btn_rect, 2, border_radius=12)

        if self.game_state == 'running':
            btn_text = '停止！'
        elif self.game_state == 'idle':
            btn_text = '开始算式'
        else:
            btn_text = '已结束'

        btn_surf = self.font_btn.render(btn_text, True, hex_to_rgb(COLORS['text_primary']))
        surface.blit(btn_surf, btn_surf.get_rect(center=(btn_x, btn_y + btn_h // 2)))

    def _draw_exit_button(self, surface: pygame.Surface):
        btn_w, btn_h = 70, 32
        btn_x, btn_y = 15, 10
        self.exit_btn_rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)

        mouse_pos = get_mouse_pos()
        is_hover = self.exit_btn_rect.collidepoint(mouse_pos)

        bg_color = hex_to_rgb('#FF4444') if is_hover else hex_to_rgb(COLORS['red_primary'])
        pygame.draw.rect(surface, bg_color, self.exit_btn_rect, border_radius=6)
        pygame.draw.rect(surface, hex_to_rgb(COLORS['gold_dark']), self.exit_btn_rect, 2, border_radius=6)

        exit_surf = self.font_small.render('退出', True, hex_to_rgb(COLORS['text_primary']))
        surface.blit(exit_surf, exit_surf.get_rect(center=(btn_x + btn_w // 2, btn_y + btn_h // 2)))

    def _draw_result_overlay(self, surface: pygame.Surface):
        if self.result_timer < 0.3:
            return

        progress = clamp((self.result_timer - 0.3) / 0.6, 0, 1)
        eased = ease_out_quad(progress)

        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, int(160 * eased)))
        surface.blit(overlay, (0, 0))

        # Result
        if self._reward_amount > 0:
            result_text = f'结果: {self.result}  →  +¥{self._reward_amount}'
            color = hex_to_rgb(COLORS['gold'])
        else:
            result_text = f'结果: {self.result}'
            color = hex_to_rgb(COLORS['text_secondary'])

        result_surf = self.font_big.render(result_text, True, color)
        surface.blit(result_surf, result_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 20)))

        if self.result_timer >= 1.0:
            back_surf = self.font_small.render('点击任意位置返回', True, hex_to_rgb(COLORS['text_secondary']))
            back_surf.set_alpha(int(150 + 100 * math.sin(self.water_offset * 4)))
            surface.blit(back_surf, back_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 50)))
