"""Number Lottery - pick 3 numbers and match the draw"""
import math
import random
import pygame

from src.settings import (
    WINDOW_WIDTH, WINDOW_HEIGHT, COLORS,
    LOTTERY_ENTRY_COST, LOTTERY_NUMBERS, LOTTERY_PRIZES,
    LOTTERY_RESULT_DURATION
)
from src.utils import clamp, ease_out_quad, hex_to_rgb
from src.particles import ParticleEmitter


# Animation timings
SLOT_SPIN_DURATION = 1.0
SLOT_LOCK_TIME = 0.1
DONE_SHOW_PAUSE = 0.5
REVEAL_NEXT_PAUSE = 0.8


class NumberLottery:
    """Pick 3 numbers, match position by position to win"""

    def __init__(self, wallet):
        self.wallet = wallet
        self.particles = ParticleEmitter()

        self.game_state = 'idle'

        self.player_picks = [None, None, None]
        self.draw_results = [None, None, None]
        self.total_won = 0
        self.match_count = 0

        self.current_reveal = -1
        self.reveal_timer = 0.0
        self.slot_flash = [0, 0, 0]
        self.matched_draw = [False, False, False]
        self.matched_pick = [False, False, False]

        self.result_timer = 0.0
        self.shake_intensity = 0.0
        self.water_offset = 0.0
        self.particle_emitted = False

        self.slot_size = 80
        self.slot_gap = 40
        self.draw_y = 0
        self.pick_y = 0
        self.slot_x = []

        self.font_title = pygame.font.SysFont('microsoftyahei', 30, bold=True)
        self.font_big = pygame.font.SysFont('microsoftyahei', 44, bold=True)
        self.font_info = pygame.font.SysFont('microsoftyahei', 16)
        self.font_small = pygame.font.SysFont('microsoftyahei', 13)
        self.font_slot = pygame.font.SysFont('microsoftyahei', 40, bold=True)
        self.font_btn = pygame.font.SysFont('microsoftyahei', 24, bold=True)
        self.font_label = pygame.font.SysFont('microsoftyahei', 18, bold=True)

    def reset(self):
        self.game_state = 'idle'
        self.player_picks = [None, None, None]
        self.draw_results = [None, None, None]
        self.total_won = 0
        self.match_count = 0
        self.current_reveal = -1
        self.reveal_timer = 0.0
        self.slot_flash = [0, 0, 0]
        self.matched_draw = [False, False, False]
        self.matched_pick = [False, False, False]
        self.result_timer = 0.0
        self.shake_intensity = 0.0
        self.water_offset = 0.0
        self.particle_emitted = False
        self.particles.clear()

    def _calc_layout(self):
        total_width = self.slot_size * 3 + self.slot_gap * 2
        start_x = (WINDOW_WIDTH - total_width) // 2
        self.slot_x = [
            start_x,
            start_x + self.slot_size + self.slot_gap,
            start_x + (self.slot_size + self.slot_gap) * 2,
        ]
        self.draw_y = 110
        self.pick_y = 240

    def handle_click(self, mouse_pos: tuple):
        if self.game_state == 'idle':
            self._handle_pick(mouse_pos)
        elif self.game_state == 'result' and self.result_timer >= 1.0:
            self.game_state = 'done'

    def _handle_pick(self, mouse_pos: tuple):
        mx, my = mouse_pos
        self._calc_layout()

        # Pick buttons (below each pick slot)
        for i in range(3):
            for num in LOTTERY_NUMBERS:
                btn_x = self.slot_x[i] + self.slot_size // 2
                btn_y = self.pick_y + self.slot_size + 30 + (num - 1) * 42
                btn_w, btn_h = 46, 34

                if (btn_x - btn_w // 2 <= mx <= btn_x + btn_w // 2 and
                        btn_y - btn_h // 2 <= my <= btn_y + btn_h // 2):
                    self.player_picks[i] = num
                    return

        # Start button
        if all(p is not None for p in self.player_picks):
            btn_y = self.pick_y + self.slot_size + 30 + 2 * 42 + 30
            if (WINDOW_WIDTH // 2 - 65 <= mx <= WINDOW_WIDTH // 2 + 65 and
                    btn_y - 16 <= my <= btn_y + 16):
                self._start_draw()

    def _start_draw(self):
        self.game_state = 'spinning'
        self.draw_results = [
            random.choice(LOTTERY_NUMBERS),
            random.choice(LOTTERY_NUMBERS),
            random.choice(LOTTERY_NUMBERS),
        ]
        self.current_reveal = 0
        self.reveal_timer = 0.0
        self.shake_intensity = 0.0
        self.slot_flash = [0, 0, 0]
        self.matched_draw = [False, False, False]
        self.matched_pick = [False, False, False]

    def update(self, dt: float):
        self.particles.update(dt)
        self.water_offset += dt * 2
        self.shake_intensity *= (1 - dt * 6)

        if self.game_state == 'spinning':
            self.reveal_timer += dt

            if self.reveal_timer < SLOT_SPIN_DURATION:
                self.slot_flash[self.current_reveal] = random.choice(LOTTERY_NUMBERS)
            elif self.slot_flash[self.current_reveal] != self.draw_results[self.current_reveal]:
                self.slot_flash[self.current_reveal] = self.draw_results[self.current_reveal]
                self.shake_intensity = 8.0

            if self.reveal_timer >= SLOT_SPIN_DURATION + SLOT_LOCK_TIME:
                self.game_state = 'revealing'
                self.reveal_timer = 0.0

        elif self.game_state == 'revealing':
            self.reveal_timer += dt

            if self.reveal_timer >= DONE_SHOW_PAUSE + REVEAL_NEXT_PAUSE:
                self.current_reveal += 1
                if self.current_reveal < 3:
                    self.game_state = 'spinning'
                    self.reveal_timer = 0.0
                else:
                    self._calculate_result()
                    self.game_state = 'result'
                    self.result_timer = 0.0

        elif self.game_state == 'result':
            self.result_timer += dt
            if not self.particle_emitted and self.total_won > 0:
                self.particle_emitted = True
                if self.match_count == 3:
                    self.particles.emit_confetti(
                        (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2),
                        100, ['#FFD700', '#FF9800', '#FFFFFF'], lifetime=3.0
                    )
                elif self.match_count >= 1:
                    self.particles.emit_burst(
                        (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2), 50,
                        hex_to_rgb('#FFD700'),
                        speed_range=(100, 300), lifetime=2.0, size=5
                    )

            if self.result_timer >= LOTTERY_RESULT_DURATION:
                self.game_state = 'done'

    def _calculate_result(self):
        self.matched_draw = [False, False, False]
        self.matched_pick = [False, False, False]

        for i in range(3):
            if self.player_picks[i] == self.draw_results[i]:
                self.match_count += 1
                self.matched_draw[i] = True
                self.matched_pick[i] = True

        prize_map = {1: 100, 2: 500, 3: 1000}
        self.total_won = prize_map.get(self.match_count, 0)

        if self.total_won > 0:
            self.wallet.add(self.total_won)

    def draw(self, surface: pygame.Surface):
        surface.fill(hex_to_rgb(COLORS['bg_primary']))
        self._draw_border(surface)

        # Title
        shadow = self.font_title.render('数字彩票', True, (25, 20, 10))
        surface.blit(shadow, shadow.get_rect(center=(WINDOW_WIDTH // 2 + 2, 20)))
        title_surf = self.font_title.render('数字彩票', True, hex_to_rgb(COLORS['gold']))
        surface.blit(title_surf, title_surf.get_rect(center=(WINDOW_WIDTH // 2, 16)))

        # Prize info
        info_text = '对1个=¥100  对2个=¥500  对3个=¥1000'
        info_surf = self.font_small.render(info_text, True, hex_to_rgb(COLORS['text_secondary']))
        surface.blit(info_surf, info_surf.get_rect(center=(WINDOW_WIDTH // 2, 44)))

        self._calc_layout()

        # Connection lines
        for i in range(3):
            line_x = self.slot_x[i] + self.slot_size // 2
            line_top = self.draw_y + self.slot_size
            line_bottom = self.pick_y

            if self.game_state == 'result' and self.matched_pick[i]:
                line_color = hex_to_rgb('#00FF00')
                line_width = 4
            else:
                line_color = hex_to_rgb(COLORS['gold_dark'])
                line_width = 2

            segments = 8
            gap = (line_bottom - line_top) // (segments * 2)
            if gap > 0:
                for s in range(segments):
                    y_start = line_top + s * gap * 2
                    y_end = min(y_start + gap, line_bottom)
                    pygame.draw.line(surface, line_color, (line_x, y_start), (line_x, y_end), line_width)

        # Draw slots (top row)
        for i in range(3):
            self._draw_draw_slot(surface, i)

        # VS label
        vs_y = (self.draw_y + self.pick_y) // 2
        vs_surf = self.font_small.render('对比', True, hex_to_rgb(COLORS['text_secondary']))
        surface.blit(vs_surf, vs_surf.get_rect(center=(WINDOW_WIDTH // 2, vs_y)))

        # Pick slots (bottom row)
        for i in range(3):
            self._draw_pick_slot(surface, i)

        if self.game_state == 'idle':
            self._draw_pick_buttons(surface)
            self._draw_start_button(surface)
        elif self.game_state in ('spinning', 'revealing'):
            self._draw_spinning(surface)
        elif self.game_state == 'result':
            self._draw_result(surface)

        self.particles.draw(surface)

    def _draw_border(self, surface: pygame.Surface):
        pygame.draw.rect(surface, hex_to_rgb(COLORS['red_primary']),
                         (4, 4, WINDOW_WIDTH - 8, WINDOW_HEIGHT - 8), 2)

    def _draw_slot_bg(self, surface: pygame.Surface, x: int, y: int, color='gold_dark'):
        bg = hex_to_rgb(COLORS['card_bg'])
        border = hex_to_rgb(COLORS[color])
        pygame.draw.rect(surface, bg, (x, y, self.slot_size, self.slot_size), border_radius=10)
        pygame.draw.rect(surface, border, (x, y, self.slot_size, self.slot_size), 3, border_radius=10)

    def _draw_draw_slot(self, surface: pygame.Surface, index: int):
        x = self.slot_x[index]
        y = self.draw_y

        bg_color = 'success' if self.matched_draw[index] and self.game_state == 'result' else 'gold_dark'
        self._draw_slot_bg(surface, x, y, bg_color)

        # Slot number label (below the slot)
        label_surf = self.font_small.render(f'第{index + 1}个', True, hex_to_rgb(COLORS['text_secondary']))
        surface.blit(label_surf, label_surf.get_rect(center=(x + self.slot_size // 2, y + self.slot_size + 14)))

        display = self.slot_flash[index] if self.slot_flash[index] else None
        if display:
            num_color = '#00FF00' if self.matched_draw[index] and self.game_state == 'result' else COLORS['gold']
            self._draw_number(surface, x, y, display, num_color)
        else:
            self._draw_number(surface, x, y, '?', COLORS['text_secondary'])

        if index < 2:
            arrow_x = x + self.slot_size + self.slot_gap // 2
            arrow_surf = self.font_small.render('→', True, hex_to_rgb(COLORS['gold']))
            surface.blit(arrow_surf, arrow_surf.get_rect(center=(arrow_x, y + self.slot_size // 2)))

    def _draw_pick_slot(self, surface: pygame.Surface, index: int):
        x = self.slot_x[index]
        y = self.pick_y

        bg_color = 'success' if self.matched_pick[index] and self.game_state == 'result' else 'gold_dark'
        self._draw_slot_bg(surface, x, y, bg_color)

        if self.player_picks[index] is not None:
            num_color = '#00FF00' if self.matched_pick[index] else COLORS['gold']
            self._draw_number(surface, x, y, self.player_picks[index], num_color)

            if self.game_state == 'result':
                if self.matched_pick[index]:
                    mark_surf = self.font_info.render('✓', True, hex_to_rgb('#00FF00'))
                else:
                    mark_surf = self.font_info.render('✗', True, hex_to_rgb('#FF4444'))
                surface.blit(mark_surf, mark_surf.get_rect(center=(x + self.slot_size // 2, y + self.slot_size + 14)))

        if index < 2:
            arrow_x = x + self.slot_size + self.slot_gap // 2
            arrow_surf = self.font_small.render('→', True, hex_to_rgb(COLORS['gold']))
            surface.blit(arrow_surf, arrow_surf.get_rect(center=(arrow_x, y + self.slot_size // 2)))

    def _draw_pick_buttons(self, surface: pygame.Surface):
        for i in range(3):
            for num in LOTTERY_NUMBERS:
                btn_x = self.slot_x[i] + self.slot_size // 2
                btn_y = self.pick_y + self.slot_size + 30 + (num - 1) * 42
                btn_w, btn_h = 46, 34

                selected = self.player_picks[i] == num
                bg_color = hex_to_rgb(COLORS['gold']) if selected else hex_to_rgb(COLORS['card_bg'])
                border = hex_to_rgb(COLORS['gold']) if selected else hex_to_rgb(COLORS['gold_dark'])

                pygame.draw.rect(surface, bg_color,
                                 (btn_x - btn_w // 2, btn_y - btn_h // 2, btn_w, btn_h),
                                 border_radius=6)
                pygame.draw.rect(surface, border,
                                 (btn_x - btn_w // 2, btn_y - btn_h // 2, btn_w, btn_h),
                                 2, border_radius=6)

                text_color = hex_to_rgb(COLORS['bg_primary']) if selected else hex_to_rgb(COLORS['gold'])
                num_surf = self.font_btn.render(str(num), True, text_color)
                surface.blit(num_surf, num_surf.get_rect(center=(btn_x, btn_y)))

    def _draw_start_button(self, surface: pygame.Surface):
        if not all(p is not None for p in self.player_picks):
            return

        btn_x = WINDOW_WIDTH // 2
        btn_y = self.pick_y + self.slot_size + 30 + 2 * 42 + 30

        bg_color = hex_to_rgb(COLORS['red_primary'])
        pygame.draw.rect(surface, bg_color, (btn_x - 65, btn_y - 16, 130, 32), border_radius=8)
        pygame.draw.rect(surface, hex_to_rgb(COLORS['gold']),
                         (btn_x - 65, btn_y - 16, 130, 32), 2, border_radius=8)

        start_surf = self.font_info.render('开 奖', True, hex_to_rgb(COLORS['gold']))
        surface.blit(start_surf, start_surf.get_rect(center=(btn_x, btn_y)))

    def _draw_spinning(self, surface: pygame.Surface):
        if not (0 <= self.current_reveal < 3):
            return

        hint_y = self.pick_y + self.slot_size + 30 + 3 * 42 + 20

        if self.game_state == 'spinning' and self.reveal_timer < SLOT_SPIN_DURATION:
            hint_surf = self.font_info.render(
                f'正在揭晓第 {self.current_reveal + 1} 个...',
                True, hex_to_rgb(COLORS['gold'])
            )
        elif self.game_state == 'revealing' and self.reveal_timer < DONE_SHOW_PAUSE:
            hint_surf = self.font_info.render(
                '变化完成!',
                True, hex_to_rgb('#00FF00')
            )
        else:
            return
        surface.blit(hint_surf, hint_surf.get_rect(center=(WINDOW_WIDTH // 2, hint_y)))

    def _draw_result(self, surface: pygame.Surface):
        if self.result_timer < 0.2:
            return

        progress = clamp(self.result_timer / 0.6, 0, 1)
        eased = ease_out_quad(progress)

        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, int(180 * eased)))
        surface.blit(overlay, (0, 0))

        if self.total_won > 0:
            if self.match_count == 3:
                win_text = '全中！+¥1000！'
            else:
                win_text = f'恭喜！中奖 +¥{self.total_won}'
            color = hex_to_rgb(COLORS['gold'])
        else:
            win_text = '未中奖'
            color = hex_to_rgb(COLORS['text_secondary'])

        win_surf = self.font_big.render(win_text, True, color)
        surface.blit(win_surf, win_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 30)))

        if self.result_timer >= 1.0:
            back_surf = self.font_small.render('点击任意位置返回', True, hex_to_rgb(COLORS['text_secondary']))
            back_surf.set_alpha(int(150 + 100 * math.sin(self.water_offset * 4)))
            surface.blit(back_surf, back_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 50)))

    def _draw_number(self, surface, x, y, num, color, font=None):
        if font is None:
            font = self.font_slot
        num_surf = font.render(str(num), True, hex_to_rgb(color))
        surface.blit(num_surf, num_surf.get_rect(center=(x + 40, y + 40)))
