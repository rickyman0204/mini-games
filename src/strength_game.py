"""Strength Competition - mash spacebar for power"""
import random
import pygame

from src.settings import (
    WINDOW_WIDTH, WINDOW_HEIGHT, COLORS,
)
from src.utils import (
    s, get_font, hex_to_rgb, get_mouse_pos,
    draw_text_with_shadow, draw_exit_button, draw_game_border,
    draw_breathing_hint, ease_out_cubic, draw_progress_bar
)

POWER_TABLE = [
    {'pts': 1, 'prob': 0.35, 'label': '+1'},
    {'pts': 2, 'prob': 0.30, 'label': '+2'},
    {'pts': 3, 'prob': 0.15, 'label': '+3'},
    {'pts': 4, 'prob': 0.10, 'label': '+4'},
    {'pts': 5, 'prob': 0.05, 'label': '+5'},
    {'pts': 10, 'prob': 0.05, 'label': '+10'},
]

MAX_POWER = 100
TARGET_MIN = 80
TARGET_MAX = 150
CASH_MIN = 300
CASH_MAX = 500


class StrengthGame:

    def __init__(self, wallet):
        self.wallet = wallet

        self.game_state = 'idle'

        self.power = 0
        self.result_money = 0

        self.duration = 0.0
        self.time_left = 0.0
        self.timer_min = 8.0
        self.timer_max = 10.0

        self.target_power = MAX_POWER

        self.last_press_pts = 0
        self.press_feedback = 0.0
        self.press_feedback_label = ''
        self.press_particles = []

        self.start_btn_rect = pygame.Rect(0, 0, 0, 0)
        self.exit_btn_rect = pygame.Rect(0, 0, 0, 0)

        self.bob_timer = 0.0
        self.result_timer = 0.0

        self.font_title = get_font(58, bold=True)
        self.font_big = get_font(70, bold=True)
        self.font_small = get_font(26)
        self.font_btn = get_font(38, bold=True)
        self.font_power = get_font(48, bold=True)

    def reset(self):
        self.game_state = 'idle'
        self.power = 0
        self.result_money = 0
        self.duration = random.uniform(self.timer_min, self.timer_max)
        self.time_left = self.duration
        self.target_power = random.randint(TARGET_MIN, TARGET_MAX)
        self.last_press_pts = 0
        self.press_feedback = 0.0
        self.press_feedback_label = ''
        self.press_particles = []
        self.bob_timer = 0.0
        self.result_timer = 0.0

    def handle_click(self, mouse_pos: tuple):
        if self.exit_btn_rect.collidepoint(mouse_pos):
            self.game_state = 'done'
            return

        if self.game_state == 'idle' and self.start_btn_rect.collidepoint(mouse_pos):
            self.game_state = 'playing'

        if self.game_state == 'result' and self.result_timer >= 0.5:
            self.game_state = 'done'

    def handle_keydown(self, key):
        if self.game_state != 'playing':
            return False

        if key == pygame.K_SPACE:
            self._mash()
            return True
        return False

    def _mash(self):
        roll = random.random()
        cumulative = 0.0
        pts = 1
        entry = POWER_TABLE[1]
        for e in POWER_TABLE:
            cumulative += e['prob']
            if roll <= cumulative:
                pts = e['pts']
                entry = e
                break

        self.power = max(0, self.power + pts)
        self.last_press_pts = pts
        self.press_feedback = 0.4

        self.press_particles.append({
            'x': WINDOW_WIDTH // 2 + random.uniform(-s(80), s(80)),
            'y': WINDOW_HEIGHT // 2 - s(40),
            'vy': -120,
            'life': 0.8,
            'max_life': 0.8,
            'label': entry['label'],
            'color': self._get_pts_color(pts),
        })

        if self.power >= self.target_power:
            self._end_round(success=True)

    def _get_pts_color(self, pts: int) -> tuple:
        colors = {1: (180, 180, 180), 2: (100, 200, 100), 3: (100, 150, 255),
                  4: (255, 180, 50), 5: (255, 220, 80), 10: (255, 80, 80)}
        return colors.get(pts, (255, 255, 255))

    def _end_round(self, success: bool = False):
        self.game_state = 'result'
        self.result_timer = 0.0
        if success:
            self.result_money = random.randint(CASH_MIN, CASH_MAX)
        else:
            self.result_money = 0
        self.wallet.add(self.result_money)

    def update(self, dt: float):
        self.bob_timer += dt

        if self.game_state == 'playing':
            self.time_left -= dt
            if self.time_left <= 0:
                self.time_left = 0
                self._end_round(success=False)

        if self.press_feedback > 0:
            self.press_feedback -= dt

        new_particles = []
        for p in self.press_particles:
            p['life'] -= dt
            p['y'] += p['vy'] * dt
            if p['life'] > 0:
                new_particles.append(p)
        self.press_particles = new_particles

        if self.game_state == 'result':
            self.result_timer += dt

    def draw(self, surface: pygame.Surface):
        surface.fill(hex_to_rgb(COLORS['bg_primary']))
        draw_game_border(surface)
        self._draw_title(surface)
        self._draw_power_bar(surface)
        self._draw_timer(surface)
        self._draw_particles(surface)

        if self.game_state == 'idle':
            self._draw_start_button(surface)
        elif self.game_state == 'playing':
            self._draw_mash_hint(surface)
        elif self.game_state == 'result':
            self._draw_result(surface)

        mouse_pos = get_mouse_pos()
        self.exit_btn_rect = draw_exit_button(surface, mouse_pos, font_size=s(26))

    def _draw_title(self, surface: pygame.Surface):
        draw_text_with_shadow(surface, '力量比拼', self.font_title,
                              COLORS['gold'], (WINDOW_WIDTH // 2, s(24)))

    def _draw_power_bar(self, surface: pygame.Surface):
        cx = WINDOW_WIDTH // 2
        bar_y = s(120)
        bar_w = s(500)
        bar_h = s(30)
        bar_x = cx - bar_w // 2

        pygame.draw.rect(surface, hex_to_rgb('#2A2A2A'), (bar_x, bar_y, bar_w, bar_h),
                         border_radius=s(8))

        progress = self.power / self.target_power
        if progress > 0:
            fill_w = int(bar_w * min(progress, 1.0))
            if progress < 0.5:
                color = (50, 150, 255)
            elif progress < 0.8:
                color = (255, 200, 50)
            else:
                color = (255, 80, 80)
            pygame.draw.rect(surface, color, (bar_x, bar_y, fill_w, bar_h),
                             border_radius=s(8))

        pygame.draw.rect(surface, hex_to_rgb(COLORS['gold']), (bar_x, bar_y, bar_w, bar_h),
                         s(2), border_radius=s(8))

        power_str = f'{self.power}/{self.target_power}'
        draw_text_with_shadow(surface, power_str, self.font_power,
                              hex_to_rgb(COLORS['gold_light']), (cx, bar_y + bar_h + s(40)))

        if self.press_feedback > 0:
            alpha = int(255 * (self.press_feedback / 0.4))
            flash_color = self._get_pts_color(self.last_press_pts)
            label = self._get_label_for_pts(self.last_press_pts)
            font = get_font(60, bold=True)
            surf = font.render(label, True, flash_color)
            surf.set_alpha(alpha)
            surface.blit(surf, surf.get_rect(center=(cx, bar_y + bar_h + s(100))))

    def _get_label_for_pts(self, pts: int) -> str:
        for entry in POWER_TABLE:
            if entry['pts'] == pts:
                return entry['label']
        return '+0'

    def _draw_timer(self, surface: pygame.Surface):
        if self.game_state == 'playing':
            cx = WINDOW_WIDTH // 2
            timer_y = s(280)
            timer_font = get_font(52, bold=True)
            time_str = f'{self.time_left:.1f}s'
            draw_text_with_shadow(surface, time_str, timer_font,
                                  (255, 255, 255), (cx, timer_y))

            bar_w = s(300)
            bar_h = s(8)
            bar_x = cx - bar_w // 2
            bar_y = timer_y + s(40)
            progress = self.time_left / self.duration
            pygame.draw.rect(surface, (80, 80, 80), (bar_x, bar_y, bar_w, bar_h),
                             border_radius=s(4))
            fill_w = int(bar_w * progress)
            color = (255, 255, 100) if progress > 0.3 else (255, 80, 80)
            pygame.draw.rect(surface, color, (bar_x, bar_y, fill_w, bar_h),
                             border_radius=s(4))

    def _draw_particles(self, surface: pygame.Surface):
        for p in self.press_particles:
            life_ratio = p['life'] / p['max_life']
            alpha = int(255 * life_ratio)
            font = get_font(36, bold=True)
            surf = font.render(p['label'], True, p['color'])
            surf.set_alpha(alpha)
            surface.blit(surf, surf.get_rect(center=(int(p['x']), int(p['y']))))

    def _draw_start_button(self, surface: pygame.Surface):
        btn_w, btn_h = s(200), s(60)
        btn_x = WINDOW_WIDTH // 2
        btn_y = WINDOW_HEIGHT // 2 + s(40)
        self.start_btn_rect = pygame.Rect(btn_x - btn_w // 2, btn_y, btn_w, btn_h)

        mouse_pos = get_mouse_pos()
        is_hover = self.start_btn_rect.collidepoint(mouse_pos)

        bg_color = hex_to_rgb(COLORS['gold']) if is_hover else hex_to_rgb(COLORS['gold_dark'])
        pygame.draw.rect(surface, bg_color, self.start_btn_rect, border_radius=s(12))
        pygame.draw.rect(surface, hex_to_rgb(COLORS['gold_light']), self.start_btn_rect,
                         s(2), border_radius=s(12))

        btn_surf = self.font_btn.render('开始', True, hex_to_rgb('#2D1515'))
        surface.blit(btn_surf, btn_surf.get_rect(center=(btn_x, btn_y + btn_h // 2)))

    def _draw_mash_hint(self, surface: pygame.Surface):
        font = get_font(36, bold=True)
        draw_text_with_shadow(surface, '疯狂按空格键！', font,
                              hex_to_rgb(COLORS['gold_light']),
                              (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + s(120)))

    def _draw_result(self, surface: pygame.Surface):
        if self.result_timer < 0.2:
            return

        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        progress = min(1.0, (self.result_timer - 0.2) / 0.5)
        eased = progress * (2 - progress)
        overlay.fill((0, 0, 0, int(140 * eased)))
        surface.blit(overlay, (0, 0))

        cx = WINDOW_WIDTH // 2
        cy = WINDOW_HEIGHT // 2 - s(20)

        result_text = f'恭喜获得 ¥{self.result_money}!' if self.result_money > 0 else '挑战失败！未达目标'
        result_color = hex_to_rgb(COLORS['gold']) if self.result_money > 0 else hex_to_rgb(COLORS['red_primary'])
        draw_text_with_shadow(surface, result_text, self.font_big,
                              result_color, (cx, cy))

        sub_text = f'力量值: {self.power}/{self.target_power}'
        sub_font = get_font(28)
        sub_surf = sub_font.render(sub_text, True, hex_to_rgb(COLORS['text_secondary']))
        surface.blit(sub_surf, sub_surf.get_rect(center=(cx, cy + s(50))))

        if self.result_money > 0:
            reward_text = f'随机奖励: ¥{CASH_MIN}~¥{CASH_MAX}'
            reward_surf = sub_font.render(reward_text, True, hex_to_rgb(COLORS['gold_light']))
            surface.blit(reward_surf, reward_surf.get_rect(center=(cx, cy + s(90))))

        if self.result_timer >= 0.5:
            draw_breathing_hint(surface, '点击任意位置返回', sub_font,
                               COLORS['text_secondary'],
                               (WINDOW_WIDTH // 2, WINDOW_HEIGHT - s(50)),
                               self.result_timer, speed=4)
