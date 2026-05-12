"""Coin Toss Game - free to play, toss for big wins"""
import math
import random
import pygame

from src.settings import (
    WINDOW_WIDTH, WINDOW_HEIGHT, COLORS,
)
from src.utils import get_mouse_pos, clamp, ease_out_quad, hex_to_rgb
from src.particles import ParticleEmitter

# Probabilities
EDGE_CHANCE = 0.01   # 1% land on edge

# Rewards
EDGE_REWARD = 500
HEADS_REWARD = 15
TAILS_PENALTY = -10


class CoinTossGame:
    """Free coin toss: edge=+500, heads=+15, tails=-1"""

    def __init__(self, wallet):
        self.wallet = wallet
        self.particles = ParticleEmitter()

        # Game state: 'idle', 'tossing', 'result', 'done'
        self.game_state = 'idle'

        # Coin
        self.coin_y = 0
        self.coin_radius = 50
        self.spin_angle = 0.0
        self.spin_speed = 0
        self.coin_scale_y = 1.0

        # Toss animation
        self.toss_timer = 0.0
        self.toss_duration = 1.8
        self.coin_peak_y = 180
        self.coin_start_y = 0

        # Result
        self.result = ''       # 'edge', 'heads', 'tails'
        self.reward = 0
        self.result_timer = 0.0
        self.result_alpha = 0.0
        self.shake_intensity = 0.0
        self.water_offset = 0.0

        # Buttons
        self.toss_btn_rect = pygame.Rect(0, 0, 0, 0)
        self.exit_btn_rect = pygame.Rect(0, 0, 0, 0)

        # Fonts
        self.font_title = pygame.font.SysFont('microsoftyahei', 36, bold=True)
        self.font_big = pygame.font.SysFont('microsoftyahei', 48, bold=True)
        self.font_info = pygame.font.SysFont('microsoftyahei', 20)
        self.font_small = pygame.font.SysFont('microsoftyahei', 16)
        self.font_btn = pygame.font.SysFont('microsoftyahei', 24, bold=True)
        self.font_coin = pygame.font.SysFont('microsoftyahei', 36, bold=True)

        self.coin_start_y = WINDOW_HEIGHT // 2 - 40

    def reset(self):
        self.game_state = 'idle'
        self.spin_angle = 0.0
        self.spin_speed = 0
        self.coin_scale_y = 1.0
        self.toss_timer = 0.0
        self.result = ''
        self.reward = 0
        self.result_timer = 0.0
        self.result_alpha = 0.0
        self.shake_intensity = 0.0
        self.water_offset = 0.0
        self.particles.clear()

    def handle_click(self, mouse_pos: tuple):
        if self.exit_btn_rect.collidepoint(mouse_pos):
            self.game_state = 'done'
            return

        if self.game_state == 'idle':
            if self.toss_btn_rect.collidepoint(mouse_pos):
                self._toss_coin()
        elif self.game_state == 'result' and self.result_timer >= 1.5:
            self.game_state = 'done'

    def _toss_coin(self):
        self.game_state = 'tossing'
        self.toss_timer = 0.0
        self.spin_speed = 15 + random.uniform(0, 5)
        self.coin_scale_y = 1.0

        # Determine result
        r = random.random()
        if r < EDGE_CHANCE:
            self.result = 'edge'
            self.reward = EDGE_REWARD
        elif r < EDGE_CHANCE + 0.5:
            self.result = 'heads'
            self.reward = HEADS_REWARD
        else:
            self.result = 'tails'
            self.reward = TAILS_PENALTY

        self.wallet.add(self.reward)

    def update(self, dt: float):
        self.particles.update(dt)
        self.water_offset += dt * 2
        self.shake_intensity *= (1 - dt * 6)

        if self.game_state == 'tossing':
            self.toss_timer += dt
            self.spin_angle += self.spin_speed * dt * 10

            # Coin flies up then falls
            progress = self.toss_timer / self.toss_duration
            if progress < 1.0:
                # Parabolic arc
                self.coin_y = self.coin_start_y - math.sin(progress * math.pi) * 200
                # Flip illusion: scale Y oscillates
                self.coin_scale_y = abs(math.cos(self.spin_angle)) * 0.3 + 0.7
            else:
                # Landed
                self.coin_y = self.coin_start_y
                self.coin_scale_y = 1.0
                self.game_state = 'result'
                self.result_timer = 0.0
                self.shake_intensity = 6.0

                if self.result == 'edge':
                    self.particles.emit_confetti(
                        (WINDOW_WIDTH // 2, self.coin_start_y),
                        60, ['#FFD700', '#FFA500', '#FFFFFF'], lifetime=2.5
                    )
                elif self.result == 'tails':
                    self.particles.emit_burst(
                        (WINDOW_WIDTH // 2, self.coin_start_y),
                        10, hex_to_rgb('#888888'),
                        speed_range=(30, 80), lifetime=0.8, size=2
                    )

        elif self.game_state == 'result':
            self.result_timer += dt
            self.result_alpha = clamp(self.result_timer * 3, 0, 1)

    def draw(self, surface: pygame.Surface):
        surface.fill(hex_to_rgb('#1a1a2e'))

        # Shake offset
        ox, oy = 0, 0
        if self.shake_intensity > 0.5:
            ox = random.uniform(-self.shake_intensity, self.shake_intensity)
            oy = random.uniform(-self.shake_intensity, self.shake_intensity)

        self._draw_border(surface)
        self._draw_title(surface)
        self._draw_info(surface)
        self._draw_coin(surface, ox, oy)

        if self.game_state == 'idle':
            self._draw_toss_button(surface)

        if self.game_state == 'result':
            self._draw_result(surface)

        # Exit button
        self._draw_exit_button(surface)

        self.particles.draw(surface)

    def _draw_border(self, surface: pygame.Surface):
        pygame.draw.rect(surface, hex_to_rgb(COLORS['red_primary']),
                         (4, 4, WINDOW_WIDTH - 8, WINDOW_HEIGHT - 8), 2)

    def _draw_title(self, surface: pygame.Surface):
        title_surf = self.font_title.render('掷硬币', True, hex_to_rgb(COLORS['gold']))
        surface.blit(title_surf, title_surf.get_rect(center=(WINDOW_WIDTH // 2, 18)))

    def _draw_info(self, surface: pygame.Surface):
        info_surf = self.font_small.render(
            '1% 立起=+500 | 正面=+15 | 反面=-10 | 免费无限玩',
            True, hex_to_rgb(COLORS['text_secondary']))
        surface.blit(info_surf, info_surf.get_rect(center=(WINDOW_WIDTH // 2, 46)))

    def _draw_coin(self, surface: pygame.Surface, ox: float, oy: float):
        cx = WINDOW_WIDTH // 2 + ox
        cy = self.coin_start_y + oy
        r = self.coin_radius
        scale_y = self.coin_scale_y

        if self.game_state == 'result':
            # Draw the actual result face
            if self.result == 'edge':
                self._draw_edge_coin(surface, cx, cy, r)
            elif self.result == 'heads':
                self._draw_heads_coin(surface, cx, cy, r)
            else:
                self._draw_tails_coin(surface, cx, cy, r)
        else:
            # Spinning coin
            coin_surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)

            # Coin body (gold)
            pygame.draw.circle(coin_surf, hex_to_rgb('#FFD700'), (r, r), r)
            pygame.draw.circle(coin_surf, hex_to_rgb('#B8860B'), (r, r), r, 3)

            # Inner circle
            pygame.draw.circle(coin_surf, hex_to_rgb('#FFEC8B'), (r, r), r - 8)

            # Text
            text_surf = self.font_coin.render('?', True, hex_to_rgb('#8B6914'))
            coin_surf.blit(text_surf, text_surf.get_rect(center=(r, r)))

            # Apply vertical scale for flip effect
            if scale_y < 1.0:
                h = int(coin_surf.get_height() * scale_y)
                if h < 4:
                    # Thin line
                    pygame.draw.line(surface, hex_to_rgb('#FFD700'),
                                   (cx - r, cy), (cx + r, cy), 3)
                else:
                    coin_surf = pygame.transform.scale(coin_surf, (r * 2, h))
                    surface.blit(coin_surf, (cx - r, cy - h // 2))
            else:
                surface.blit(coin_surf, (cx - r, cy - r))

    def _draw_heads_coin(self, surface: pygame.Surface, cx: float, cy: float, r: float):
        # 正面 - gold coin with 正
        coin_surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(coin_surf, hex_to_rgb('#FFD700'), (r, r), r)
        pygame.draw.circle(coin_surf, hex_to_rgb('#B8860B'), (r, r), r, 3)
        pygame.draw.circle(coin_surf, hex_to_rgb('#FFEC8B'), (r, r), r - 8)

        text_surf = self.font_coin.render('正', True, hex_to_rgb('#B8860B'))
        coin_surf.blit(text_surf, text_surf.get_rect(center=(r, r)))

        surface.blit(coin_surf, (cx - r, cy - r))

        # Glow
        glow_surf = pygame.Surface((r * 3, r * 3), pygame.SRCALPHA)
        for i in range(r * 3 // 2, 0, -5):
            alpha = int(30 * (1 - i / (r * 3 // 2)))
            pygame.draw.circle(glow_surf, (255, 215, 0, alpha), (r * 3 // 2, r * 3 // 2), i)
        surface.blit(glow_surf, (cx - r * 3 // 2, cy - r * 3 // 2), special_flags=pygame.BLEND_RGBA_ADD)

    def _draw_tails_coin(self, surface: pygame.Surface, cx: float, cy: float, r: float):
        # 反面 - silver coin with 反
        coin_surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(coin_surf, hex_to_rgb('#C0C0C0'), (r, r), r)
        pygame.draw.circle(coin_surf, hex_to_rgb('#808080'), (r, r), r, 3)
        pygame.draw.circle(coin_surf, hex_to_rgb('#D8D8D8'), (r, r), r - 8)

        text_surf = self.font_coin.render('反', True, hex_to_rgb('#606060'))
        coin_surf.blit(text_surf, text_surf.get_rect(center=(r, r)))

        surface.blit(coin_surf, (cx - r, cy - r))

    def _draw_edge_coin(self, surface: pygame.Surface, cx: float, cy: float, r: float):
        # 立起 - thin vertical line with sparkle
        edge_w = 6

        # Vertical bar
        pygame.draw.rect(surface, hex_to_rgb('#FFD700'),
                         (cx - edge_w // 2, cy - r, edge_w, r * 2), border_radius=3)
        pygame.draw.rect(surface, hex_to_rgb('#B8860B'),
                         (cx - edge_w // 2, cy - r, edge_w, r * 2), 1, border_radius=3)

        # Radiating lines (sparkle effect)
        for angle in range(0, 360, 30):
            rad = math.radians(angle)
            x1 = cx + math.cos(rad) * (r + 5)
            y1 = cy + math.sin(rad) * (r + 5)
            x2 = cx + math.cos(rad) * (r + 15)
            y2 = cy + math.sin(rad) * (r + 15)
            alpha = int(100 + 155 * math.sin(self.water_offset * 5 + angle))
            line_surf = pygame.Surface((int(abs(x2 - x1)) + 2, int(abs(y2 - y1)) + 2), pygame.SRCALPHA)
            pygame.draw.line(line_surf, (255, 215, 0, alpha), (0, 0), (abs(x2 - x1), abs(y2 - y1)), 2)
            surface.blit(line_surf, (min(x1, x2), min(y1, y2)))

    def _draw_result(self, surface: pygame.Surface):
        if self.result_timer < 0.2:
            return

        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        progress = clamp((self.result_timer - 0.2) / 0.5, 0, 1)
        eased = ease_out_quad(progress)
        overlay.fill((0, 0, 0, int(140 * eased)))
        surface.blit(overlay, (0, 0))

        if self.result == 'edge':
            result_text = '硬币立起来了！+¥500！'
            color = hex_to_rgb(COLORS['gold'])
        elif self.result == 'heads':
            result_text = '正面！+¥15'
            color = hex_to_rgb(COLORS['success'])
        else:
            result_text = '反面... -¥10'
            color = hex_to_rgb(COLORS['red_primary'])

        result_surf = self.font_big.render(result_text, True, color)
        surface.blit(result_surf, result_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 20)))

        if self.result_timer >= 1.5:
            back_surf = self.font_small.render('点击任意位置继续', True, hex_to_rgb(COLORS['text_secondary']))
            back_surf.set_alpha(int(150 + 100 * math.sin(self.water_offset * 4)))
            surface.blit(back_surf, back_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 50)))

    def _draw_toss_button(self, surface: pygame.Surface):
        btn_w, btn_h = 180, 55
        btn_x = WINDOW_WIDTH // 2
        btn_y = self.coin_start_y + self.coin_radius + 50
        self.toss_btn_rect = pygame.Rect(btn_x - btn_w // 2, btn_y, btn_w, btn_h)

        mouse_pos = get_mouse_pos()
        is_hover = self.toss_btn_rect.collidepoint(mouse_pos)

        bg_color = hex_to_rgb(COLORS['gold']) if is_hover else hex_to_rgb(COLORS['gold_dark'])
        pygame.draw.rect(surface, bg_color, self.toss_btn_rect, border_radius=12)
        pygame.draw.rect(surface, hex_to_rgb(COLORS['gold_light']), self.toss_btn_rect, 2, border_radius=12)

        btn_surf = self.font_btn.render('投掷硬币', True, hex_to_rgb('#2D1515'))
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
