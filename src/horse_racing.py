"""Horse Racing Game - bet on your red horse vs blue horse"""
import math
import random
import pygame

from src.settings import (
    WINDOW_WIDTH, WINDOW_HEIGHT, COLORS,
    HORSE_ENTRY_COST, HORSE_WIN_MIN, HORSE_WIN_MAX,
    HORSE_DRAW_COST, HORSE_TRACK_CELLS,
)
from src.utils import get_mouse_pos, clamp, ease_out_quad, hex_to_rgb
from src.particles import ParticleEmitter

# Track layout
CELL_W = 100
CELL_H = 90
CELL_GAP = 6
TRACK_LENGTH = 30  # number of cells

# Move probabilities: 5%→4, 10%→3, 30%→2, 50%→1, 5%→0


class HorseRacingGame:
    """Horse race: red (player) vs blue horse across 10 cells"""

    def __init__(self, wallet):
        self.wallet = wallet
        self.particles = ParticleEmitter()

        # Game state: 'idle', 'racing', 'result', 'done'
        self.game_state = 'idle'

        # Horse positions (0 = before cell 1, TRACK_LENGTH = finished)
        self.red_pos = 0
        self.blue_pos = 0

        # Race animation
        self.race_timer = 0.0
        self.race_phase = 0.0       # accumulated time for alternating moves
        self.red_target = 0          # where red is animating toward
        self.blue_target = 0         # where blue is animating toward
        self.red_anim = 0.0          # animation progress 0-1 for current move
        self.blue_anim = 0.0
        self.move_interval = 0.7     # time between each horse's move
        self.race_started = False
        self.step_label = ''         # last step label ('冲!', '快跑!')

        # Result
        self.winner = ''             # 'red', 'blue', 'tie'
        self.reward = 0
        self.result_timer = 0.0
        self.shake_intensity = 0.0
        self.water_offset = 0.0

        # Buttons
        self.start_btn_rect = pygame.Rect(0, 0, 0, 0)
        self.exit_btn_rect = pygame.Rect(0, 0, 0, 0)

        # Fonts
        self.font_title = pygame.font.SysFont('microsoftyahei', 36, bold=True)
        self.font_big = pygame.font.SysFont('microsoftyahei', 48, bold=True)
        self.font_info = pygame.font.SysFont('microsoftyahei', 20)
        self.font_small = pygame.font.SysFont('microsoftyahei', 16)
        self.font_btn = pygame.font.SysFont('microsoftyahei', 24, bold=True)
        self.font_cell = pygame.font.SysFont('microsoftyahei', 16, bold=True)
        self.font_finish = pygame.font.SysFont('microsoftyahei', 18, bold=True)

        # Viewport for scrolling
        self.viewport_offset = 0.0  # horizontal scroll offset
        self.track_start_x = 20     # where track starts on screen

        self._calc_layout()

    def _calc_layout(self):
        self.total_track_w = TRACK_LENGTH * (CELL_W + CELL_GAP) - CELL_GAP
        self.track_x = self.track_start_x
        self.track_y = 110
        self.viewport_w = WINDOW_WIDTH - self.track_start_x * 2  # visible width

    def reset(self):
        self.game_state = 'idle'
        self.red_pos = 0
        self.blue_pos = 0
        self.race_timer = 0.0
        self.race_phase = 0.0
        self.red_target = 0
        self.blue_target = 0
        self.red_anim = 0.0
        self.blue_anim = 0.0
        self.race_started = False
        self.step_label = ''
        self.winner = ''
        self.reward = 0
        self.result_timer = 0.0
        self.shake_intensity = 0.0
        self.water_offset = 0.0
        self.particles.clear()
        self.viewport_offset = 0.0
        self._calc_layout()

    def _roll_move(self):
        """Return steps: 5%→4, 10%→3, 30%→2, 50%→1, 5%→0"""
        r = random.random()
        if r < 0.05:
            return 4, '冲刺!'
        elif r < 0.15:
            return 3, '快跑!'
        elif r < 0.45:
            return 2, ''
        elif r < 0.95:
            return 1, ''
        else:
            return 0, '停!'

    def _check_winner(self):
        red_done = self.red_pos >= TRACK_LENGTH
        blue_done = self.blue_pos >= TRACK_LENGTH
        if red_done and blue_done:
            self.winner = 'tie'
            return True
        if red_done:
            self.winner = 'red'
            return True
        if blue_done:
            self.winner = 'blue'
            return True
        return False

    def _finish_race(self):
        self.game_state = 'result'
        self.result_timer = 0.0
        self.shake_intensity = 6.0

        if self.winner == 'red':
            self.reward = random.randint(HORSE_WIN_MIN, HORSE_WIN_MAX)
            self.wallet.add(self.reward)
            self.particles.emit_confetti(
                (WINDOW_WIDTH // 2, self.track_y + 30),
                50, ['#FFD700', '#FF6B6B', '#FFFFFF'], lifetime=2.5
            )
        elif self.winner == 'blue':
            self.reward = 0
        else:  # tie
            self.reward = HORSE_DRAW_COST
            self.wallet.add(self.reward)
            self.particles.emit_confetti(
                (WINDOW_WIDTH // 2, self.track_y + 30),
                30, ['#FFD700', '#87CEEB', '#FFFFFF'], lifetime=2.0
            )

    def handle_click(self, mouse_pos: tuple):
        if self.exit_btn_rect.collidepoint(mouse_pos):
            self.game_state = 'done'
            return

        if self.game_state == 'idle':
            if self.start_btn_rect.collidepoint(mouse_pos):
                self._start_race()
        elif self.game_state == 'result' and self.result_timer >= 1.5:
            self.game_state = 'done'

    def _start_race(self):
        self.game_state = 'racing'
        self.race_timer = 0.0
        self.race_phase = 0.0
        self.red_target = 0
        self.blue_target = 0
        self.red_anim = 0.0
        self.blue_anim = 0.0
        self.race_started = True
        self.step_label = ''

    def _do_red_move(self):
        steps, label = self._roll_move()
        self.red_pos = min(self.red_pos + steps, TRACK_LENGTH + 5)  # overshoot ok
        self.red_target = self.red_pos
        self.red_anim = 0.0
        self.step_label = label

    def _do_blue_move(self):
        steps, label = self._roll_move()
        self.blue_pos = min(self.blue_pos + steps, TRACK_LENGTH + 5)
        self.blue_target = self.blue_pos
        self.blue_anim = 0.0
        if label:
            self.step_label = label

    def update(self, dt: float):
        self.particles.update(dt)
        self.water_offset += dt * 2
        self.shake_intensity *= (1 - dt * 6)

        if self.game_state == 'racing':
            self.race_timer += dt
            elapsed = self.race_timer

            # Both horses move at the same time, alternating: red then blue each turn
            turns = int((elapsed + 0.001) / self.move_interval)
            red_turns = turns
            blue_turns = turns

            # Execute red moves
            for _ in range(red_turns - getattr(self, '_red_moves_done', 0)):
                if self.red_pos < TRACK_LENGTH:
                    self._do_red_move()
            self._red_moves_done = red_turns

            # Execute blue moves
            for _ in range(blue_turns - getattr(self, '_blue_moves_done', 0)):
                if self.blue_pos < TRACK_LENGTH:
                    self._do_blue_move()
            self._blue_moves_done = blue_turns

            # Update viewport: follow leading horse, keep it at 1/3 of screen
            leading_pos = max(self.red_pos, self.blue_pos)
            leading_pixel = leading_pos * (CELL_W + CELL_GAP)
            target_offset = leading_pixel - self.viewport_w * 0.3
            self.viewport_offset += (target_offset - self.viewport_offset) * 0.08
            self.viewport_offset = max(0, min(self.viewport_offset, self.total_track_w - self.viewport_w))

            # Check winner
            if self._check_winner():
                self._finish_race()

        elif self.game_state == 'result':
            self.result_timer += dt

    def draw(self, surface: pygame.Surface):
        surface.fill(hex_to_rgb('#1a1a2e'))

        ox, oy = 0, 0
        if self.shake_intensity > 0.5:
            ox = random.uniform(-self.shake_intensity, self.shake_intensity)
            oy = random.uniform(-self.shake_intensity, self.shake_intensity)

        self._draw_border(surface)
        self._draw_title(surface)
        self._draw_track(surface, ox, oy)
        self._draw_info(surface)

        if self.game_state == 'idle':
            self._draw_start_button(surface)

        if self.game_state == 'result':
            self._draw_result_overlay(surface)

        self._draw_exit_button(surface)
        self.particles.draw(surface)

    def _draw_border(self, surface: pygame.Surface):
        pygame.draw.rect(surface, hex_to_rgb(COLORS['red_primary']),
                         (4, 4, WINDOW_WIDTH - 8, WINDOW_HEIGHT - 8), 2)

    def _draw_title(self, surface: pygame.Surface):
        title_surf = self.font_title.render('赛马游戏', True, hex_to_rgb(COLORS['gold']))
        surface.blit(title_surf, title_surf.get_rect(center=(WINDOW_WIDTH // 2, 18)))

    def _draw_info(self, surface: pygame.Surface):
        info_surf = self.font_small.render(
            '5%走4步 | 10%走3步 | 30%走2步 | 50%走1步 | 5%停步',
            True, hex_to_rgb(COLORS['text_secondary']))
        surface.blit(info_surf, info_surf.get_rect(center=(WINDOW_WIDTH // 2, 46)))

    def _get_cell_x(self, col):
        return self.track_x + col * (CELL_W + CELL_GAP) - self.viewport_offset

    def _draw_track(self, surface: pygame.Surface, ox: float, oy: float):
        ty = self.track_y + oy

        # Clip track drawing to viewport
        clip_rect = pygame.Rect(self.track_x, ty - 10, self.viewport_w, CELL_H * 2 + CELL_GAP * 2 + 80)
        surface.set_clip(clip_rect)

        # Track background
        total_w = TRACK_LENGTH * (CELL_W + CELL_GAP) - CELL_GAP
        total_h = CELL_H * 2 + CELL_GAP * 2
        track_bg = pygame.Rect(self.track_x - 4, ty - 4, total_w + 8, total_h + 8)
        pygame.draw.rect(surface, hex_to_rgb('#2d1515'), track_bg, border_radius=8)
        pygame.draw.rect(surface, hex_to_rgb(COLORS['gold_dark']), track_bg, 2, border_radius=8)

        # Lane labels (fixed position, left of track)
        label_font = self.font_small
        red_label = label_font.render('红马（你）', True, hex_to_rgb('#FF6B6B'))
        blue_label = label_font.render('蓝马（对手）', True, hex_to_rgb('#4A90D9'))
        surface.blit(red_label, (self.track_x - 85, ty + CELL_H // 2 - 6))
        surface.blit(blue_label, (self.track_x - 90, ty + CELL_H * 2 + CELL_GAP + CELL_H // 2 - 6))

        # Only draw visible cells
        start_col = max(0, int(self.viewport_offset // (CELL_W + CELL_GAP)) - 1)
        end_col = min(TRACK_LENGTH, start_col + (self.viewport_w // (CELL_W + CELL_GAP)) + 3)

        for lane in range(2):
            for col in range(start_col, end_col):
                x = self._get_cell_x(col) + ox
                y = ty + lane * (CELL_H + CELL_GAP)

                # Cell background
                cell_color = (25, 25, 45) if col < TRACK_LENGTH - 1 else (35, 25, 20)
                pygame.draw.rect(surface, cell_color,
                               (x, y, CELL_W, CELL_H), border_radius=4)
                pygame.draw.rect(surface, (45, 45, 70),
                               (x, y, CELL_W, CELL_H), 1, border_radius=4)

                # Cell number
                if col == TRACK_LENGTH - 1:
                    finish_surf = self.font_finish.render('终点', True, hex_to_rgb(COLORS['gold']))
                    surface.blit(finish_surf, finish_surf.get_rect(center=(x + CELL_W // 2, y + CELL_H // 2)))
                else:
                    num_surf = self.font_cell.render(str(col + 1), True, (60, 60, 80))
                    surface.blit(num_surf, num_surf.get_rect(center=(x + CELL_W // 2, y + CELL_H // 2)))

        # Draw finish line
        finish_x = self._get_cell_x(TRACK_LENGTH - 1) + CELL_W + ox
        pygame.draw.line(surface, hex_to_rgb(COLORS['gold']),
                         (finish_x, ty - 4), (finish_x, ty + total_h + 4), 3)

        # Draw horses
        self._draw_horse(surface, 'red', ox, oy)
        self._draw_horse(surface, 'blue', ox, oy)

        # Reset clip
        surface.set_clip(None)

        # Step label (outside clip area)
        if self.step_label and self.game_state == 'racing':
            step_surf = self.font_big.render(self.step_label, True, hex_to_rgb(COLORS['gold']))
            alpha = int(200 + 55 * math.sin(self.water_offset * 6))
            step_surf.set_alpha(alpha)
            surface.blit(step_surf, step_surf.get_rect(center=(WINDOW_WIDTH // 2, ty + total_h + 50)))

        # Progress bar at top of track
        bar_x = self.track_x + 10
        bar_y = ty - 30
        bar_w = self.viewport_w - 20
        bar_h = 6
        pygame.draw.rect(surface, (40, 40, 60), (bar_x, bar_y, bar_w, bar_h), border_radius=3)
        red_progress = min(self.red_pos / TRACK_LENGTH, 1.0)
        blue_progress = min(self.blue_pos / TRACK_LENGTH, 1.0)
        pygame.draw.rect(surface, hex_to_rgb('#FF6B6B'), (bar_x, bar_y, bar_w * red_progress, bar_h), border_radius=3)
        pygame.draw.rect(surface, hex_to_rgb('#4A90D9'), (bar_x, bar_y + bar_h + 2, bar_w * blue_progress, bar_h), border_radius=3)

    def _draw_horse(self, surface: pygame.Surface, color: str, ox: float, oy: float):
        pos = self.red_pos if color == 'red' else self.blue_pos
        lane = 0 if color == 'red' else 1

        # Calculate screen position
        ty = self.track_y + oy + lane * (CELL_H + CELL_GAP)

        # Interpolate position for animation
        if color == 'red':
            anim = clamp(self.red_anim, 0, 1)
            current = self.red_pos - (self.red_target - self.red_pos) * (1 - anim) if self.red_anim < 1 else self.red_pos
        else:
            anim = clamp(self.blue_anim, 0, 1)
            current = self.blue_pos - (self.blue_target - self.blue_pos) * (1 - anim) if self.blue_anim < 1 else self.blue_pos

        # Clamp for display
        display_pos = min(max(current, 0), TRACK_LENGTH)

        # Map position to cell x
        # pos=0 means before cell 1, pos=1 means in cell 1
        cell_idx = min(int(display_pos), TRACK_LENGTH - 1)
        cell_offset = display_pos - cell_idx  # 0-1 within cell

        x = self._get_cell_x(cell_idx) + ox + cell_offset * (CELL_W + CELL_GAP)
        y = ty + CELL_H // 2

        # Draw horse (simple emoji-style)
        horse_color = hex_to_rgb('#FF6B6B') if color == 'red' else hex_to_rgb('#4A90D9')
        glow_color = hex_to_rgb('#FF8888') if color == 'red' else hex_to_rgb('#6BB0FF')

        # Glow
        glow_surf = pygame.Surface((30, 30), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*glow_color, 40), (15, 15), 14)
        surface.blit(glow_surf, (int(x) - 15, int(y) - 15))

        # Horse body
        pygame.draw.circle(surface, horse_color, (int(x), int(y)), 12)
        pygame.draw.circle(surface, glow_color, (int(x) - 3, int(y) - 4), 5)

        # Direction arrow
        pygame.draw.polygon(surface, horse_color, [
            (int(x) + 12, int(y)),
            (int(x) + 20, int(y) - 5),
            (int(x) + 20, int(y) + 5),
        ])

        # Finished flag
        if pos >= TRACK_LENGTH and self.game_state in ('result', 'done'):
            flag_surf = self.font_cell.render('🏁', True, hex_to_rgb(COLORS['gold']))
            surface.blit(flag_surf, (int(x) + 22, int(y) - 20))

    def _draw_start_button(self, surface: pygame.Surface):
        btn_w, btn_h = 180, 55
        btn_x = WINDOW_WIDTH // 2
        btn_y = self.track_y + CELL_H * 2 + CELL_GAP * 2 + 100
        self.start_btn_rect = pygame.Rect(btn_x - btn_w // 2, btn_y, btn_w, btn_h)

        mouse_pos = get_mouse_pos()
        is_hover = self.start_btn_rect.collidepoint(mouse_pos)

        bg_color = hex_to_rgb(COLORS['gold']) if is_hover else hex_to_rgb(COLORS['gold_dark'])
        pygame.draw.rect(surface, bg_color, self.start_btn_rect, border_radius=12)
        pygame.draw.rect(surface, hex_to_rgb(COLORS['gold_light']), self.start_btn_rect, 2, border_radius=12)

        btn_surf = self.font_btn.render(f'开始赛马 ¥{HORSE_ENTRY_COST}', True, hex_to_rgb('#2D1515'))
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
        if self.result_timer < 0.2:
            return

        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        progress = clamp((self.result_timer - 0.2) / 0.5, 0, 1)
        eased = ease_out_quad(progress)
        overlay.fill((0, 0, 0, int(140 * eased)))
        surface.blit(overlay, (0, 0))

        if self.winner == 'red':
            result_text = f'🏆 你的红马赢了！+¥{self.reward}'
            color = hex_to_rgb(COLORS['gold'])
        elif self.winner == 'blue':
            result_text = '蓝马先到... 无奖励'
            color = hex_to_rgb(COLORS['text_secondary'])
        else:
            result_text = f'同时到达！平局 +¥{self.reward}'
            color = hex_to_rgb(COLORS['info'])

        result_surf = self.font_big.render(result_text, True, color)
        surface.blit(result_surf, result_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 20)))

        if self.result_timer >= 1.5:
            back_surf = self.font_small.render('点击任意位置继续', True, hex_to_rgb(COLORS['text_secondary']))
            back_surf.set_alpha(int(150 + 100 * math.sin(self.water_offset * 4)))
            surface.blit(back_surf, back_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 50)))
