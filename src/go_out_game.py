"""Should I Go Out? - Weather prediction and choice game"""
import math
import random
import pygame

from src.settings import (
    WINDOW_WIDTH, WINDOW_HEIGHT, COLORS,
    GO_OUT_ENTRY_COST, GO_OUT_PREDICT_COST,
)
from src.utils import (
    s, get_font, hex_to_rgb, draw_button, draw_text_with_shadow,
    draw_exit_button, draw_game_border, draw_breathing_hint,
    draw_result_overlay, draw_progress_bar, ease_out_quad,
    clamp, ease_out_cubic, get_mouse_pos,
)
from src.particles import ParticleEmitter

PREDICT_ACCURACY = 0.80

REWARDS = {
    ('sunny', 'go_out'): 200,
    ('sunny', 'stay_home'): 50,
    ('cloudy', 'go_out'): 50,
    ('cloudy', 'stay_home'): 150,
}


class GoOutGame:

    def __init__(self, wallet):
        self.wallet = wallet
        self.particles = ParticleEmitter()

        self.game_state = 'idle'

        self.scenario = None
        self.actual_weather = None
        self.prediction = None
        self.has_predicted = False

        self.player_choice = None
        self.reward = 0

        self.result_timer = 0.0

        self.stay_btn_rect = pygame.Rect(0, 0, 0, 0)
        self.go_btn_rect = pygame.Rect(0, 0, 0, 0)
        self.predict_btn_rect = pygame.Rect(0, 0, 0, 0)
        self.exit_btn_rect = pygame.Rect(0, 0, 0, 0)

        self.font_title = get_font(58, bold=True)
        self.font_big = get_font(70, bold=True)
        self.font_info = get_font(32)
        self.font_small = get_font(26)
        self.font_btn = get_font(38, bold=True)
        self.font_hint = get_font(29)
        self.font_tiny = get_font(24)

        self._calc_layout()

    def _calc_layout(self):
        self.btn_y = s(370)
        self.btn_w = s(150)
        self.btn_h = s(50)
        self.stay_btn_rect = pygame.Rect(
            WINDOW_WIDTH // 2 - self.btn_w - s(10), self.btn_y, self.btn_w, self.btn_h)
        self.go_btn_rect = pygame.Rect(
            WINDOW_WIDTH // 2 + s(10), self.btn_y, self.btn_w, self.btn_h)
        self.predict_btn_rect = pygame.Rect(
            WINDOW_WIDTH // 2 - s(80), self.btn_y + s(60), s(160), s(40))
        self.exit_btn_rect = pygame.Rect(s(15), s(10), s(70), s(32))

    def reset(self):
        self.game_state = 'idle'
        self.actual_weather = None
        self.prediction = None
        self.has_predicted = False
        self.player_choice = None
        self.reward = 0
        self.result_timer = 0.0
        self.particles.clear()
        self._calc_layout()

    def _generate_weather(self):
        self.scenario = random.choice(['sunny_heavy', 'cloudy_heavy'])
        if self.scenario == 'sunny_heavy':
            self.actual_weather = 'sunny' if random.random() < 0.75 else 'cloudy'
        else:
            self.actual_weather = 'sunny' if random.random() < 0.25 else 'cloudy'

    def _generate_prediction(self):
        if random.random() < PREDICT_ACCURACY:
            self.prediction = self.actual_weather
        else:
            self.prediction = 'cloudy' if self.actual_weather == 'sunny' else 'sunny'

    def handle_click(self, mouse_pos: tuple):
        if self.exit_btn_rect.collidepoint(mouse_pos):
            self.game_state = 'done'
            return

        if self.game_state == 'idle':
            self._start_game()
            return

        elif self.game_state in ('choosing', 'predicting'):
            if self.predict_btn_rect.collidepoint(mouse_pos):
                self._predict()
                return
            if self.stay_btn_rect.collidepoint(mouse_pos):
                self.player_choice = 'stay_home'
                self._resolve()
                return
            if self.go_btn_rect.collidepoint(mouse_pos):
                self.player_choice = 'go_out'
                self._resolve()
                return

        elif self.game_state == 'result' and self.result_timer >= 0.5:
            self.game_state = 'done'

    def _start_game(self):
        self._generate_weather()
        self.game_state = 'choosing'

    def _predict(self):
        if self.has_predicted:
            return
        self.has_predicted = True
        self.wallet.subtract(GO_OUT_PREDICT_COST)
        self._generate_prediction()
        self.game_state = 'predicting'

    def _resolve(self):
        self.reward = REWARDS.get((self.actual_weather, self.player_choice), 0)
        self.wallet.add(self.reward)
        self.game_state = 'result'
        self.result_timer = 0.0

        if self.reward >= 150:
            self.particles.emit_confetti(
                (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2),
                40, ['#FFD700', '#FFFFFF', '#FFA500'],
                lifetime=2.0
            )

    def update(self, dt: float):
        self.particles.update(dt)

        if self.game_state == 'result':
            self.result_timer += dt

    def draw(self, surface: pygame.Surface):
        surface.fill(hex_to_rgb(COLORS['bg_primary']))

        self._draw_border(surface)
        self._draw_title(surface)

        if self.game_state == 'idle':
            self._draw_start_hint(surface)
        elif self.game_state in ('choosing', 'predicting'):
            self._draw_weather_unknown(surface)
        elif self.game_state == 'result':
            self._draw_result(surface)

        self._draw_exit_button(surface)
        self.particles.draw(surface)

    def _draw_border(self, surface: pygame.Surface):
        pygame.draw.rect(surface, hex_to_rgb(COLORS['red_primary']),
                         (s(4), s(4), WINDOW_WIDTH - s(8), WINDOW_HEIGHT - s(8)), 2)

    def _draw_title(self, surface: pygame.Surface):
        title_surf = self.font_title.render('是否要出门', True, hex_to_rgb(COLORS['gold']))
        surface.blit(title_surf, title_surf.get_rect(center=(WINDOW_WIDTH // 2, s(24))))

    def _draw_start_hint(self, surface: pygame.Surface):
        hint_surf = self.font_hint.render('点击屏幕开始', True, hex_to_rgb(COLORS['text_secondary']))
        surface.blit(hint_surf, hint_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2)))

    def _draw_weather_unknown(self, surface: pygame.Surface):
        cx = WINDOW_WIDTH // 2

        card_w, card_h = s(200), s(200)
        card_surf = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
        pygame.draw.rect(card_surf, hex_to_rgb(COLORS['card_bg']), (0, 0, card_w, card_h), border_radius=s(16))
        pygame.draw.rect(card_surf, hex_to_rgb(COLORS['gold_dark']), (0, 0, card_w, card_h), 2, border_radius=s(16))

        q_surf = self.font_big.render('?', True, hex_to_rgb(COLORS['text_muted']))
        card_surf.blit(q_surf, q_surf.get_rect(center=(card_w // 2, card_h // 2)))

        surface.blit(card_surf, (cx - card_w // 2, s(60)))

        hint_surf = self.font_small.render('今天天气如何？', True, hex_to_rgb(COLORS['text_secondary']))
        surface.blit(hint_surf, hint_surf.get_rect(center=(cx, s(275))))

        font = self.font_tiny
        reward_table = [
            ('☀️ 晴天 + 出去玩', '¥200', COLORS['gold']),
            ('☁️ 阴天 + 出去玩', '¥50', COLORS['text_secondary']),
            ('☀️ 晴天 + 呆在家', '¥50', COLORS['text_secondary']),
            ('☁️ 阴天 + 呆在家', '¥150', COLORS['success']),
        ]
        table_y = s(290)
        for label, val, color in reward_table:
            label_surf = font.render(label, True, hex_to_rgb(color))
            surface.blit(label_surf, (cx - s(80), table_y))
            val_surf = font.render(val, True, hex_to_rgb(color))
            surface.blit(val_surf, (cx + s(70) - val_surf.get_width(), table_y))
            table_y += s(38)

        self._draw_choice_button(surface, self.stay_btn_rect, '🏠 呆在家', 'info')
        self._draw_choice_button(surface, self.go_btn_rect, '🎉 出去玩', 'success')

        if not self.has_predicted:
            self._draw_predict_button(surface)
        else:
            self._draw_prediction_result(surface)

    def _draw_choice_button(self, surface: pygame.Rect, rect: pygame.Rect, text: str, color_key: str):
        mouse_pos = get_mouse_pos()
        is_hover = rect.collidepoint(mouse_pos)

        bg = hex_to_rgb(COLORS[color_key]) if is_hover else hex_to_rgb(COLORS['card_bg'])
        pygame.draw.rect(surface, bg, rect, border_radius=s(12))
        pygame.draw.rect(surface, hex_to_rgb(COLORS['gold_dark']), rect, 2, border_radius=s(12))

        btn_surf = self.font_btn.render(text, True, hex_to_rgb(COLORS['text_primary']))
        surface.blit(btn_surf, btn_surf.get_rect(center=(rect.centerx, rect.centery)))

    def _draw_predict_button(self, surface: pygame.Surface):
        rect = self.predict_btn_rect
        mouse_pos = get_mouse_pos()
        is_hover = rect.collidepoint(mouse_pos)

        bg = hex_to_rgb(COLORS['warning']) if is_hover else hex_to_rgb(COLORS['card_bg'])
        pygame.draw.rect(surface, bg, rect, border_radius=s(10))
        pygame.draw.rect(surface, hex_to_rgb(COLORS['gold_dark']), rect, 2, border_radius=s(10))

        btn_surf = self.font_small.render(f'🔮 预测 (¥{GO_OUT_PREDICT_COST})', True, hex_to_rgb(COLORS['text_primary']))
        surface.blit(btn_surf, btn_surf.get_rect(center=(rect.centerx, rect.centery)))

    def _draw_prediction_result(self, surface: pygame.Surface):
        cx = WINDOW_WIDTH // 2

        win_w, win_h = s(240), s(160)
        win_x = cx - win_w // 2
        win_y = s(60)

        frame_pad = s(16)
        frame_surf = pygame.Surface((win_w + frame_pad, win_h + frame_pad), pygame.SRCALPHA)
        pygame.draw.rect(frame_surf, hex_to_rgb(COLORS['wood']), (0, 0, win_w + frame_pad, win_h + frame_pad), border_radius=s(8))
        pygame.draw.rect(frame_surf, hex_to_rgb(COLORS['wood_dark']), (0, 0, win_w + frame_pad, win_h + frame_pad), 2, border_radius=s(8))
        surface.blit(frame_surf, (win_x - frame_pad // 2, win_y - frame_pad // 2))

        sky_x, sky_y = win_x, win_y
        if self.prediction == 'sunny':
            pygame.draw.rect(surface, hex_to_rgb(COLORS['sky']), (sky_x, sky_y, win_w, win_h))
            sun_cx, sun_cy = win_x + win_w - s(40), win_y + s(40)
            sun_r = s(30)
            for r in range(sun_r, 0, -s(4)):
                alpha = int(255 * (1 - r / sun_r))
                glow = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
                pygame.draw.circle(glow, (255, 224, 102, alpha), (r, r), r)
                surface.blit(glow, (sun_cx - r, sun_cy - r))
            pygame.draw.circle(surface, (255, 224, 102), (sun_cx, sun_cy), s(22))
            pygame.draw.circle(surface, (255, 243, 176), (sun_cx - s(4), sun_cy - s(4)), s(12))
            pygame.draw.circle(surface, (255, 255, 255), (win_x + s(50), win_y + s(80)), s(18))
            pygame.draw.circle(surface, (255, 255, 255), (win_x + s(70), win_y + s(75)), s(22))
            pygame.draw.circle(surface, (255, 255, 255), (win_x + s(90), win_y + s(80)), s(18))
        else:
            pygame.draw.rect(surface, (120, 120, 130), (sky_x, sky_y, win_w, win_h))
            cloud_positions = [
                (win_x + s(40), win_y + s(50), s(30)),
                (win_x + s(80), win_y + s(40), s(35)),
                (win_x + s(130), win_y + s(55), s(28)),
                (win_x + s(60), win_y + s(80), s(25)),
                (win_x + s(110), win_y + s(90), s(30)),
                (win_x + s(160), win_y + s(70), s(25)),
                (win_x + s(30), win_y + s(110), s(20)),
                (win_x + s(90), win_y + s(120), s(22)),
                (win_x + s(150), win_y + s(110), s(20)),
            ]
            for px, py, pr in cloud_positions:
                pygame.draw.circle(surface, (90, 90, 100), (px, py), pr)
            for _ in range(15):
                rx = win_x + random.randint(s(5), win_w - s(5))
                ry = win_y + random.randint(s(20), win_h - s(5))
                pygame.draw.line(surface, (100, 150, 200), (rx, ry), (rx - s(3), ry + s(8)), 1)

        bar_w = s(6)
        pygame.draw.rect(surface, hex_to_rgb(COLORS['wood_dark']),
                         (sky_x + win_w // 2 - bar_w // 2, sky_y, bar_w, win_h))
        pygame.draw.rect(surface, hex_to_rgb(COLORS['wood_dark']),
                         (sky_x, sky_y + win_h // 2 - bar_w // 2, win_w, bar_w))

        pred_text = '☀️ 预测: 可能是晴天' if self.prediction == 'sunny' else '☁️ 预测: 可能是阴天'
        pred_surf = self.font_hint.render(pred_text, True, hex_to_rgb(COLORS['warning']))
        surface.blit(pred_surf, pred_surf.get_rect(center=(cx, win_y + win_h + s(30))))

    def _draw_result(self, surface: pygame.Surface):
        cx = WINDOW_WIDTH // 2

        weather_icon = '☀️' if self.actual_weather == 'sunny' else '☁️'
        weather_name = '晴天' if self.actual_weather == 'sunny' else '阴天'
        choice_name = '呆在家里' if self.player_choice == 'stay_home' else '出去玩'

        weather_surf = self.font_big.render(f'{weather_icon} 实际天气: {weather_name}', True, hex_to_rgb(COLORS['gold']))
        surface.blit(weather_surf, weather_surf.get_rect(center=(cx, WINDOW_HEIGHT // 2 - s(60))))

        choice_surf = self.font_info.render(f'你选择了: {choice_name}', True, hex_to_rgb(COLORS['text_primary']))
        surface.blit(choice_surf, choice_surf.get_rect(center=(cx, WINDOW_HEIGHT // 2)))

        if self.reward >= 100:
            reward_color = hex_to_rgb(COLORS['gold'])
        elif self.reward >= 50:
            reward_color = hex_to_rgb(COLORS['success'])
        else:
            reward_color = hex_to_rgb(COLORS['text_secondary'])

        reward_surf = self.font_big.render(f'+¥{self.reward}', True, reward_color)
        surface.blit(reward_surf, reward_surf.get_rect(center=(cx, WINDOW_HEIGHT // 2 + s(50))))

        if self.has_predicted:
            pred_correct = (self.prediction == self.actual_weather)
            pred_text = f'🔮 预测{"正确" if pred_correct else "错误"}!'
            pred_surf = self.font_hint.render(pred_text, True,
                                              hex_to_rgb(COLORS['success'] if pred_correct else COLORS['red_primary']))
            surface.blit(pred_surf, pred_surf.get_rect(center=(cx, WINDOW_HEIGHT // 2 + s(90))))

        if self.result_timer >= 0.5:
            draw_breathing_hint(surface, '点击任意位置返回', self.font_small,
                               COLORS['text_secondary'],
                               (cx, WINDOW_HEIGHT - s(50)),
                               self.result_timer, speed=4)

    def _draw_exit_button(self, surface: pygame.Surface):
        btn_w, btn_h = s(70), s(32)
        btn_x, btn_y = s(15), s(10)
        self.exit_btn_rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)

        mouse_pos = get_mouse_pos()
        is_hover = self.exit_btn_rect.collidepoint(mouse_pos)

        bg_color = hex_to_rgb('#FF4444') if is_hover else hex_to_rgb(COLORS['red_primary'])
        pygame.draw.rect(surface, bg_color, self.exit_btn_rect, border_radius=s(6))
        pygame.draw.rect(surface, hex_to_rgb(COLORS['gold_dark']), self.exit_btn_rect, 2, border_radius=s(6))

        exit_surf = self.font_small.render('退出', True, hex_to_rgb(COLORS['text_primary']))
        surface.blit(exit_surf, exit_surf.get_rect(center=(btn_x + btn_w // 2, btn_y + btn_h // 2)))
