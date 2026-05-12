"""Wooden Fish Game - click to accumulate merit"""
import math
import os
import random
import pygame

from src.settings import (
    WINDOW_WIDTH, WINDOW_HEIGHT, COLORS,
    WOODEN_FISH_ENTRY_COST,
)
from src.utils import (
    s, get_font, hex_to_rgb, draw_button, draw_text_with_shadow,
    draw_exit_button, draw_game_border, draw_breathing_hint,
    draw_result_overlay, draw_progress_bar, ease_out_quad,
    clamp, hex_to_rgb as _h2r, get_mouse_pos,
)
from src.particles import ParticleEmitter
from src.audio import generate_tone, generate_chord


class WoodenFishGame:

    def __init__(self, wallet):
        self.wallet = wallet
        self.particles = ParticleEmitter()

        try:
            sound_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'my.mp3')
            self.click_sound = pygame.mixer.Sound(sound_path)
            self.click_sound.set_volume(0.7)
        except Exception:
            try:
                self.click_sound = generate_tone(800, 0.08, volume=0.6)
            except Exception:
                self.click_sound = None

        self.bonus_sound = None
        try:
            self.bonus_sound = generate_chord([880, 1108, 1318], 0.4, volume=0.4)
        except Exception:
            pass

        self.game_state = 'idle'

        self.accumulated = 0.0
        self.click_count = 0

        self.scale = 1.0
        self.glow_alpha = 0.0
        self.float_text = ''
        self.float_timer = 0.0
        self.float_y = 0.0

        self.result_timer = 0.0
        self.shake_intensity = 0.0
        self.water_offset = 0.0

        self.dance_timer = 0.0
        self.dance_duration = 0.6
        self.dance_angle = 0.0
        self.bonus_playing = False

        self.fish_rect = pygame.Rect(0, 0, 0, 0)
        self.exit_btn_rect = pygame.Rect(0, 0, 0, 0)

        self.font_title = get_font(58, bold=True)
        self.font_big = get_font(77, bold=True)
        self.font_info = get_font(32)
        self.font_small = get_font(26)
        self.font_btn = get_font(38, bold=True)
        self.font_counter = get_font(58, bold=True)

        self._calc_layout()

    def _calc_layout(self):
        self.fish_x = WINDOW_WIDTH // 2
        self.fish_y = WINDOW_HEIGHT // 2 + s(26)
        self.fish_w = s(120)
        self.fish_h = s(80)
        self.fish_rect = pygame.Rect(
            self.fish_x - self.fish_w // 2,
            self.fish_y - self.fish_h // 2,
            self.fish_w, self.fish_h,
        )

    def reset(self):
        self.game_state = 'idle'
        self.accumulated = 0.0
        self.click_count = 0
        self.scale = 1.0
        self.glow_alpha = 0.0
        self.float_text = ''
        self.float_timer = 0.0
        self.float_y = 0.0
        self.result_timer = 0.0
        self.shake_intensity = 0.0
        self.water_offset = 0.0
        self.particles.clear()
        self._bonus = False
        self.dance_timer = 0.0
        self.dance_angle = 0.0
        self.bonus_playing = False
        self._calc_layout()

    def handle_click(self, mouse_pos: tuple):
        if self.exit_btn_rect.collidepoint(mouse_pos):
            if self.game_state == 'playing':
                self._cash_out()
            else:
                self.game_state = 'done'
            return

        if self.game_state == 'idle':
            self._start_game()
        elif self.game_state == 'playing':
            if self.fish_rect.collidepoint(mouse_pos) and not self.bonus_playing:
                self._click_fish()
        elif self.game_state == 'result' and self.result_timer >= 0.5:
            self.game_state = 'done'

    def _start_game(self):
        self.game_state = 'playing'
        self.accumulated = 0.0
        self.click_count = 0
        self.wallet.subtract(WOODEN_FISH_ENTRY_COST)

    def _click_fish(self):
        is_bonus = random.random() < 0.05
        if is_bonus:
            earn = 5.0
            self.float_text = '+5 🙏'
            if self.bonus_sound:
                self.bonus_sound.play()
            self.particles.emit_confetti(
                (self.fish_x, self.fish_y),
                20, ['#FFD700', '#FFA500', '#FFFFFF'], lifetime=1.5
            )
            self.dance_timer = 0.0
            self.bonus_playing = True
        else:
            if self.bonus_playing:
                pass
            elif self.click_sound:
                self.click_sound.play()

            earn = random.choice([0.1, 0.2, 0.3])
            self.float_text = f'+{earn:.1f}'
            self.particles.emit_burst(
                (self.fish_x, self.fish_y),
                6, hex_to_rgb(COLORS['gold']),
                speed_range=(30, 80), lifetime=0.6, size=3
            )

        self.accumulated += earn
        self.click_count += 1

        self.scale = 1.15
        self.glow_alpha = 1.0
        self.float_timer = 0.0
        self.float_y = self.fish_y - s(40)

    def _cash_out(self):
        self.game_state = 'result'
        self.result_timer = 0.0
        self.shake_intensity = 5.0

        reward = math.ceil(self.accumulated)
        if self.accumulated >= 100:
            reward += 50
            self._bonus = True
        else:
            self._bonus = False
        self._reward_amount = reward
        self.wallet.add(reward)

        if reward > 0:
            self.particles.emit_confetti(
                (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2),
                40, ['#FFD700', '#FFFFFF', '#FFA500'], lifetime=2.0
            )

    def update(self, dt: float):
        self.particles.update(dt)
        self.water_offset += dt * 2
        self.shake_intensity *= (1 - dt * 6)

        if self.scale > 1.0:
            self.scale += (1.0 - self.scale) * dt * 12

        if self.glow_alpha > 0:
            self.glow_alpha = max(0, self.glow_alpha - dt * 0.5)

        if self.float_timer is not None:
            self.float_timer += dt
            self.float_y -= dt * 60

        if self.bonus_playing:
            self.dance_timer += dt
            self.dance_angle = math.sin(self.dance_timer * 20) * 25 * (1 - self.dance_timer / self.dance_duration)
            if self.dance_timer >= self.dance_duration:
                self.bonus_playing = False
                self.dance_angle = 0.0

        if self.game_state == 'result':
            self.result_timer += dt

    def draw(self, surface: pygame.Surface):
        surface.fill(hex_to_rgb(COLORS['bg_primary']))

        ox, oy = 0, 0
        if self.shake_intensity > 0.5:
            ox = random.uniform(-self.shake_intensity, self.shake_intensity)
            oy = random.uniform(-self.shake_intensity, self.shake_intensity)

        self._draw_border(surface)
        self._draw_title(surface)
        self._draw_wooden_fish(surface, ox, oy)
        self._draw_counter(surface)

        if self.game_state == 'idle':
            self._draw_start_hint(surface)

        if self.game_state == 'playing':
            self._draw_exit_hint(surface)

        if self.game_state == 'result':
            self._draw_result_overlay(surface)

        self._draw_exit_button(surface)
        self._draw_float_text(surface)
        self.particles.draw(surface)

    def _draw_border(self, surface: pygame.Surface):
        pygame.draw.rect(surface, hex_to_rgb(COLORS['red_primary']),
                         (s(4), s(4), WINDOW_WIDTH - s(8), WINDOW_HEIGHT - s(8)), 2)

    def _draw_title(self, surface: pygame.Surface):
        title_surf = self.font_title.render('敲木鱼', True, hex_to_rgb(COLORS['gold']))
        surface.blit(title_surf, title_surf.get_rect(center=(WINDOW_WIDTH // 2, s(24))))

    def _draw_wooden_fish(self, surface: pygame.Surface, ox: float, oy: float):
        cx = self.fish_x + ox
        cy = self.fish_y + oy

        if self.glow_alpha > 0:
            glow_surf = pygame.Surface((self.fish_w * 3, self.fish_h * 3), pygame.SRCALPHA)
            glow_r = self.fish_w * 1.5
            pygame.draw.circle(glow_surf, (255, 215, 0, int(60 * self.glow_alpha)),
                             (int(glow_r), int(glow_r)), int(glow_r))
            pygame.draw.circle(glow_surf, (255, 245, 180, int(80 * self.glow_alpha)),
                             (int(glow_r), int(glow_r)), int(glow_r * 0.6))
            surface.blit(glow_surf, (cx - int(glow_r), cy - int(glow_r)), special_flags=pygame.BLEND_RGBA_ADD)

        scale = self.scale
        fw = int(self.fish_w * scale)
        fh = int(self.fish_h * scale)

        fish_surf = pygame.Surface((fw, fh), pygame.SRCALPHA)

        pygame.draw.ellipse(fish_surf, hex_to_rgb('#8B5A2B'), (0, 0, fw, fh))
        pygame.draw.ellipse(fish_surf, hex_to_rgb('#A0692B'), (fw // 6, fh // 6, fw * 2 // 3, fh * 2 // 3))
        center_x = fw // 2
        pygame.draw.ellipse(fish_surf, hex_to_rgb('#5C3317'), (center_x - s(3), fh // 4, s(6), fh // 2))
        pygame.draw.ellipse(fish_surf, hex_to_rgb('#6B4226'), (0, 0, fw, fh), s(4))

        if self.bonus_playing:
            fish_surf = pygame.transform.rotate(fish_surf, self.dance_angle)
            rotated_rect = fish_surf.get_rect(center=(cx, cy))
            surface.blit(fish_surf, rotated_rect)
        else:
            surface.blit(fish_surf, (cx - fw // 2, cy - fh // 2))

    def _draw_counter(self, surface: pygame.Surface):
        if self.game_state != 'playing':
            return

        counter_surf = self.font_counter.render(
            f'¥{self.accumulated:.1f}', True, hex_to_rgb(COLORS['gold']))
        surface.blit(counter_surf, counter_surf.get_rect(center=(WINDOW_WIDTH // 2, s(84))))

        next_surf = self.font_small.render(
            '每次 +0.1/0.2/0.3 随机 · 5%概率+5', True,
            hex_to_rgb(COLORS['text_secondary']))
        surface.blit(next_surf, next_surf.get_rect(center=(WINDOW_WIDTH // 2, s(130))))

    def _draw_start_hint(self, surface: pygame.Surface):
        hint_surf = self.font_info.render('点击木鱼开始，每次翻倍', True, hex_to_rgb(COLORS['text_secondary']))
        surface.blit(hint_surf, hint_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - s(104))))

    def _draw_exit_hint(self, surface: pygame.Surface):
        hint_surf = self.font_small.render('点击「退出」按钮结束并兑现', True, hex_to_rgb(COLORS['text_secondary']))
        surface.blit(hint_surf, hint_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - s(52))))

    def _draw_exit_button(self, surface: pygame.Surface):
        btn_w, btn_h = s(90), s(32)
        btn_x, btn_y = s(15), s(10)
        self.exit_btn_rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)

        mouse_pos = get_mouse_pos()
        is_hover = self.exit_btn_rect.collidepoint(mouse_pos)

        bg_color = hex_to_rgb('#FF4444') if is_hover else hex_to_rgb(COLORS['red_primary'])
        pygame.draw.rect(surface, bg_color, self.exit_btn_rect, border_radius=s(6))
        pygame.draw.rect(surface, hex_to_rgb(COLORS['gold_dark']), self.exit_btn_rect, 2, border_radius=s(6))

        if self.game_state == 'playing':
            reward = math.ceil(self.accumulated)
            exit_text = f'退出 ¥{reward}' if reward > 0 else '退出'
        else:
            exit_text = '退出'
        exit_surf = self.font_small.render(exit_text, True, hex_to_rgb(COLORS['text_primary']))
        surface.blit(exit_surf, exit_surf.get_rect(center=(btn_x + btn_w // 2, btn_y + btn_h // 2)))

    def _draw_float_text(self, surface: pygame.Surface):
        if not self.float_text or self.float_timer >= 0.6:
            return

        alpha = int(255 * (1 - self.float_timer / 0.6))
        color = '#FFD700' if self.float_text == '+5 🙏' else COLORS['gold']
        float_surf = self.font_info.render(self.float_text, True, hex_to_rgb(color))
        float_surf.set_alpha(alpha)
        surface.blit(float_surf, float_surf.get_rect(center=(self.fish_x, self.float_y)))

    def _draw_result_overlay(self, surface: pygame.Surface):
        if self.result_timer < 0.2:
            return

        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        progress = clamp((self.result_timer - 0.2) / 0.5, 0, 1)
        eased = ease_out_quad(progress)
        overlay.fill((0, 0, 0, int(140 * eased)))
        surface.blit(overlay, (0, 0))

        if self._bonus:
            result_text = f'敲了 {self.click_count} 次 → ¥{self.accumulated:.1f} → +¥{self._reward_amount} (含50奖励!)'
        else:
            result_text = f'敲了 {self.click_count} 次 → ¥{self.accumulated:.1f} → +¥{self._reward_amount}'
        color = hex_to_rgb(COLORS['gold'])

        result_surf = self.font_big.render(result_text, True, color)
        surface.blit(result_surf, result_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - s(20))))

        if self.result_timer >= 0.5:
            draw_breathing_hint(surface, '点击任意位置返回', self.font_small,
                               COLORS['text_secondary'],
                               (WINDOW_WIDTH // 2, WINDOW_HEIGHT - s(50)),
                               self.water_offset, speed=4)
