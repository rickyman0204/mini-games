"""Dice Game - roll 3 dice, win based on sum with combo multipliers"""
import math
import random
import pygame

from src.settings import (
    WINDOW_WIDTH, WINDOW_HEIGHT, COLORS, DICE_ENTRY_COST,
    DICE_ROLL_ANIM_DURATION, DICE_RESULT_DURATION
)
from src.utils import get_mouse_pos, clamp, ease_out_quad, hex_to_rgb
from src.particles import ParticleEmitter


class DiceGame:
    """Roll 3 dice, payouts based on sum with straight/triple multipliers"""

    def __init__(self, wallet):
        self.wallet = wallet
        self.particles = ParticleEmitter()

        # Game state: 'idle', 'rolling', 'result', 'done'
        self.game_state = 'idle'

        # Dice values
        self.dice_values = [1, 1, 1]
        self.dice_rolling = [False, False, False]
        self.dice_roll_timer = [0, 0, 0]

        # Result
        self.total_sum = 0
        self.payout = 0
        self.combo_type = ''       # 'straight', 'triple', 'pair', 'none'
        self.combo_mult = 1.0

        # Animation
        self.result_timer = 0.0
        self.shake_intensity = 0.0
        self.water_offset = 0.0
        self.particle_emitted = False

        # Dice visuals
        self.dice_size = 90
        self.dice_gap = 30
        self.dice_y = 0
        self.dice_x = []

        # Fonts
        self.font_title = pygame.font.SysFont('microsoftyahei', 36, bold=True)
        self.font_big = pygame.font.SysFont('microsoftyahei', 48, bold=True)
        self.font_info = pygame.font.SysFont('microsoftyahei', 20)
        self.font_small = pygame.font.SysFont('microsoftyahei', 16)
        self.font_dice = pygame.font.SysFont('microsoftyahei', 40, bold=True)
        self.font_btn = pygame.font.SysFont('microsoftyahei', 24, bold=True)

        # Roll button
        self.roll_btn_rect = pygame.Rect(0, 0, 0, 0)
        self.exit_btn_rect = pygame.Rect(0, 0, 0, 0)

    def reset(self):
        self.game_state = 'idle'
        self.dice_values = [1, 1, 1]
        self.dice_rolling = [False, False, False]
        self.dice_roll_timer = [0, 0, 0]
        self.total_sum = 0
        self.payout = 0
        self.combo_type = ''
        self.combo_mult = 1.0
        self.result_timer = 0.0
        self.shake_intensity = 0.0
        self.water_offset = 0.0
        self.particle_emitted = False
        self.particles.clear()
        self._calc_layout()

    def _calc_layout(self):
        total_w = self.dice_size * 3 + self.dice_gap * 2
        start_x = (WINDOW_WIDTH - total_w) // 2
        self.dice_x = [
            start_x,
            start_x + self.dice_size + self.dice_gap,
            start_x + (self.dice_size + self.dice_gap) * 2,
        ]
        self.dice_y = 150

    def handle_click(self, mouse_pos: tuple):
        if self.exit_btn_rect.collidepoint(mouse_pos):
            self.game_state = 'done'
            return

        if self.game_state == 'idle':
            if self.roll_btn_rect.collidepoint(mouse_pos):
                self._roll_dice()
        elif self.game_state == 'result' and self.result_timer >= 1.0:
            self.game_state = 'done'

    def _roll_dice(self):
        self.game_state = 'rolling'
        self.dice_values = [random.randint(1, 6) for _ in range(3)]
        self.dice_rolling = [True, True, True]
        self.dice_roll_timer = [0, 0, 0]
        self.shake_intensity = 8.0
        self.particle_emitted = False

    def _check_combo(self):
        d = sorted(self.dice_values)

        # Triple (三个一样)
        if d[0] == d[1] == d[2]:
            self.combo_type = 'triple'
            self.combo_mult = 2.5
            return

        # Straight (顺子 - 3 consecutive)
        if d[0] + 1 == d[1] and d[1] + 1 == d[2]:
            self.combo_type = 'straight'
            self.combo_mult = 3.0
            return

        # Pair (对子)
        if d[0] == d[1] or d[1] == d[2]:
            self.combo_type = 'pair'
            self.combo_mult = 1.5
            return

        self.combo_type = 'none'
        self.combo_mult = 1.0

    def _calculate_payout(self):
        self.total_sum = sum(self.dice_values)
        self._check_combo()
        self.payout = self.total_sum * 2
        self.wallet.add(self.payout)

    def update(self, dt: float):
        self.particles.update(dt)
        self.water_offset += dt * 2
        self.shake_intensity *= (1 - dt * 6)

        if self.game_state == 'rolling':
            for i in range(3):
                if self.dice_rolling[i]:
                    self.dice_roll_timer[i] += dt
                    # Stagger: dice stop one by one
                    stop_time = 0.4 + i * 0.3
                    if self.dice_roll_timer[i] >= stop_time:
                        self.dice_rolling[i] = False
                        self.shake_intensity = 5.0

            if all(not r for r in self.dice_rolling):
                self._calculate_payout()
                self.game_state = 'result'
                self.result_timer = 0.0

                if self.combo_mult >= 2.5:
                    self.particles.emit_confetti(
                        (WINDOW_WIDTH // 2, self.dice_y + self.dice_size // 2),
                        60, ['#FFD700', '#FF9800', '#FFFFFF'], lifetime=2.5
                    )
                elif self.combo_mult > 1.0:
                    self.particles.emit_burst(
                        (WINDOW_WIDTH // 2, self.dice_y + self.dice_size // 2),
                        30, hex_to_rgb('#FFD700'),
                        speed_range=(100, 250), lifetime=1.5, size=4
                    )

        elif self.game_state == 'result':
            self.result_timer += dt

    def draw(self, surface: pygame.Surface):
        surface.fill(hex_to_rgb(COLORS['bg_primary']))
        self._draw_border(surface)
        self._calc_layout()

        # Title
        title_surf = self.font_title.render('骰子游戏', True, hex_to_rgb(COLORS['gold']))
        surface.blit(title_surf, title_surf.get_rect(center=(WINDOW_WIDTH // 2, 18)))

        # Rule info
        info_surf = self.font_small.render(
            '奖励 = 三颗骰子的点数之和 × 2',
            True, hex_to_rgb(COLORS['text_secondary']))
        surface.blit(info_surf, info_surf.get_rect(center=(WINDOW_WIDTH // 2, 46)))

        # Shake offset
        ox, oy = 0, 0
        if self.shake_intensity > 0.5:
            ox = random.uniform(-self.shake_intensity, self.shake_intensity)
            oy = random.uniform(-self.shake_intensity, self.shake_intensity)

        # Dice
        for i in range(3):
            self._draw_dice(surface, i, ox, oy)

        # Sum display
        if self.game_state in ('result',):
            combo_color = {
                'straight': hex_to_rgb('#00FF00'),
                'triple': hex_to_rgb('#FF6B6B'),
                'pair': hex_to_rgb('#FFA500'),
                'none': hex_to_rgb(COLORS['text_secondary']),
            }[self.combo_type]

            combo_names = {
                'straight': '顺子!',
                'triple': '豹子!',
                'pair': '对子!',
                'none': '',
            }
            cname = combo_names[self.combo_type]

            sum_text = f'和 = {self.total_sum}  →  奖金 ¥{self.payout}'
            sum_surf = self.font_info.render(sum_text, True, hex_to_rgb(COLORS['gold']))
            surface.blit(sum_surf, sum_surf.get_rect(center=(WINDOW_WIDTH // 2, self.dice_y + self.dice_size + 20)))

        if self.game_state == 'idle':
            self._draw_roll_button(surface)

        # Exit button
        self._draw_exit_button(surface)

        # Result overlay
        if self.game_state == 'result':
            self._draw_result_overlay(surface)

        self.particles.draw(surface)

    def _draw_border(self, surface: pygame.Surface):
        pygame.draw.rect(surface, hex_to_rgb(COLORS['red_primary']),
                         (4, 4, WINDOW_WIDTH - 8, WINDOW_HEIGHT - 8), 2)

    def _draw_dice(self, surface: pygame.Surface, index: int, ox: float, oy: float):
        x = self.dice_x[index] + ox
        y = self.dice_y + oy
        size = self.dice_size

        shad = pygame.Rect(x + 3, y + 3, size, size)
        sh_s = pygame.Surface((size, size), pygame.SRCALPHA)
        sh_s.fill((0, 0, 0, 70))
        surface.blit(sh_s, shad)

        bg_color = hex_to_rgb(COLORS['card_bg'])
        is_special = self.combo_type in ('straight', 'triple') and self.game_state == 'result'
        border_color = hex_to_rgb('#FF6B6B') if is_special else hex_to_rgb(COLORS['gold_dark'])

        pygame.draw.rect(surface, bg_color, (x, y, size, size), border_radius=12)
        pygame.draw.rect(surface, border_color, (x, y, size, size), 3, border_radius=12)

        val = self.dice_values[index]
        dot_radius = 7
        dot_color = (255, 255, 255)
        cx, cy = x + size // 2, y + size // 2
        offset = size // 4

        dot_positions = {
            1: [(cx, cy)],
            2: [(cx - offset, cy - offset), (cx + offset, cy + offset)],
            3: [(cx - offset, cy - offset), (cx, cy), (cx + offset, cy + offset)],
            4: [(cx - offset, cy - offset), (cx + offset, cy - offset),
                (cx - offset, cy + offset), (cx + offset, cy + offset)],
            5: [(cx - offset, cy - offset), (cx + offset, cy - offset),
                (cx, cy),
                (cx - offset, cy + offset), (cx + offset, cy + offset)],
            6: [(cx - offset, cy - offset), (cx + offset, cy - offset),
                (cx - offset, cy), (cx + offset, cy),
                (cx - offset, cy + offset), (cx + offset, cy + offset)],
        }

        for dx, dy in dot_positions.get(val, []):
            pygame.draw.circle(surface, (0, 0, 0, 60), (int(dx) + 1, int(dy) + 1), dot_radius)
            pygame.draw.circle(surface, dot_color, (int(dx), int(dy)), dot_radius)

        if self.dice_rolling[index]:
            alpha = int(100 + 100 * math.sin(self.water_offset * 10 + index))
            spin_surf = pygame.Surface((size, size), pygame.SRCALPHA)
            pygame.draw.rect(spin_surf, (*hex_to_rgb('#FFF3B0'), alpha // 3),
                           (0, 0, size, size), border_radius=12)
            surface.blit(spin_surf, (x, y))

    def _draw_roll_button(self, surface: pygame.Surface):
        btn_w, btn_h = 160, 50
        btn_x = WINDOW_WIDTH // 2
        btn_y = self.dice_y + self.dice_size + 80
        self.roll_btn_rect = pygame.Rect(btn_x - btn_w // 2, btn_y, btn_w, btn_h)

        mouse_pos = get_mouse_pos()
        is_hover = self.roll_btn_rect.collidepoint(mouse_pos)
        can_afford = self.wallet.can_afford(DICE_ENTRY_COST)

        if not can_afford:
            bg_color = tuple(int(c * 0.4) for c in hex_to_rgb(COLORS['red_primary']))
        elif is_hover:
            bg_color = hex_to_rgb(COLORS['red_primary'])
        else:
            bg_color = tuple(int(c * 0.7) for c in hex_to_rgb(COLORS['red_primary']))

        pygame.draw.rect(surface, bg_color, self.roll_btn_rect, border_radius=10)
        pygame.draw.rect(surface, hex_to_rgb(COLORS['gold']), self.roll_btn_rect, 2, border_radius=10)

        roll_surf = self.font_btn.render(f'摇骰子 ¥{DICE_ENTRY_COST}', True, hex_to_rgb(COLORS['text_primary']))
        surface.blit(roll_surf, roll_surf.get_rect(center=(btn_x, btn_y + btn_h // 2)))

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
        if self.result_timer < 0.5:
            return

        progress = clamp((self.result_timer - 0.5) / 0.6, 0, 1)
        eased = ease_out_quad(progress)

        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, int(160 * eased)))
        surface.blit(overlay, (0, 0))

        combo_colors = {
            'straight': hex_to_rgb('#00FF00'),
            'triple': hex_to_rgb('#FF6B6B'),
            'pair': hex_to_rgb('#FFA500'),
            'none': hex_to_rgb(COLORS['gold']),
        }
        text_color = combo_colors.get(self.combo_type, hex_to_rgb(COLORS['gold']))

        result_surf = self.font_big.render(f'+¥{self.payout}', True, text_color)
        surface.blit(result_surf, result_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 20)))

        if self.result_timer >= 1.0:
            back_surf = self.font_small.render('点击任意位置返回', True, hex_to_rgb(COLORS['text_secondary']))
            back_surf.set_alpha(int(150 + 100 * math.sin(self.water_offset * 4)))
            surface.blit(back_surf, back_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 50)))
