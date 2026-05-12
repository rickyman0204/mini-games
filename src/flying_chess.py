"""Flying Chess - Red vs Blue race with weather, horse-racing style"""
import math
import random
import pygame

from src.settings import (
    WINDOW_WIDTH, WINDOW_HEIGHT, COLORS,
    FLYING_CHESS_ENTRY_COST,
)
from src.utils import (
    s, get_font, hex_to_rgb, get_mouse_pos, clamp,
    draw_text_with_shadow, draw_exit_button, draw_game_border,
    draw_breathing_hint, ease_out_quad,
)
from src.particles import ParticleEmitter

BOARD_SIZE = 100
PRIZE = 200

# Track layout (horse-racing style)
CELL_W = s(100)
CELL_H = s(80)
CELL_GAP = s(6)
TRACK_LENGTH = BOARD_SIZE + 1  # 0=start, 1..99=pattern, 100=end/finish

# Cell colors
CELL_RED = '#FF6B6B'
CELL_BLUE = '#6BAAFF'
CELL_GREY = '#909090'
CELL_START = '#FFE066'
CELL_END = '#FFD700'

WEATHER_NONE = 0
WEATHER_RED = 1
WEATHER_BLUE = 2
WEATHER_GREY = 3

WEATHER_NAMES = {
    WEATHER_RED: '红天',
    WEATHER_BLUE: '蓝天',
    WEATHER_GREY: '灰天',
}
WEATHER_COLORS = {
    WEATHER_RED: '#FF5E5E',
    WEATHER_BLUE: '#5E8AFF',
    WEATHER_GREY: '#AAAAAA',
}

WEATHER_PROB = 0.10
WEATHER_TYPES = [WEATHER_RED, WEATHER_BLUE, WEATHER_GREY]
WEIGHTS = [0.40, 0.35, 0.25]

DICE_SPECIALS = [
    {'type': '+10', 'prob': 0.01, 'label': '+10步！'},
    {'type': 'x2', 'prob': 0.05, 'label': '×2步！'},
    {'type': '/2', 'prob': 0.04, 'label': '÷2步'},
]

TRACK_LABELS = {0: '红(你)', 1: '蓝(电脑)'}
TRACK_COLORS = {0: '#FF4444', 1: '#4444FF'}

MOVE_LABELS = {'+10': '冲刺!', 'x2': '爆发!', '/2': '受阻!'}


class FlyingChessGame:

    def __init__(self, wallet):
        self.wallet = wallet
        self.particles = ParticleEmitter()

        self.game_state = 'idle'

        # Logical positions (integer, 0 = before cell 1, TRACK_LENGTH = finished)
        self.red_pos = 0
        self.blue_pos = 0

        # Display positions (float, for smooth animation)
        self.red_display = 0.0
        self.blue_display = 0.0

        # Animation targets
        self.red_target = 0.0
        self.blue_target = 0.0

        # Dice state
        self.red_dice = 0
        self.blue_dice = 0
        self.red_steps = 0
        self.blue_steps = 0

        # Phase state machine
        self.phase = 'idle'
        self.phase_timer = 0.0
        self.phase_delay = 0.5

        self.weather_active = False
        self.weather_type = WEATHER_NONE
        self.weather_timer = 0.0
        self.weather_target = ''

        self.special_label = ''
        self.special_timer = 0.0

        self.result_text = ''
        self.result_timer = 0.0

        self.log_lines = []

        self.start_btn_rect = pygame.Rect(0, 0, 0, 0)
        self.roll_btn_rect = pygame.Rect(0, 0, 0, 0)
        self.exit_btn_rect = pygame.Rect(0, 0, 0, 0)

        # Viewport for scrolling
        self.viewport_offset = 0.0
        self.track_start_x = s(20)
        self.viewport_w = 0
        self.total_track_w = 0
        self.track_x = 0
        self.track_y = 0

        self.shake_intensity = 0.0
        self.anim_timer = 0.0
        self.step_label = ''

        self._calc_layout()

        self.font_title = get_font(36, bold=True)
        self.font_big = get_font(48, bold=True)
        self.font_small = get_font(20)
        self.font_btn = get_font(24, bold=True)
        self.font_cell = get_font(16, bold=True)
        self.font_log = get_font(18)
        self.font_result = get_font(42, bold=True)

    def _calc_layout(self):
        self.total_track_w = TRACK_LENGTH * (CELL_W + CELL_GAP) - CELL_GAP
        self.track_x = self.track_start_x
        self.track_y = s(110)
        self.viewport_w = WINDOW_WIDTH - self.track_start_x * 2

    def reset(self):
        self.game_state = 'idle'
        self.red_pos = 0
        self.blue_pos = 0
        self.red_display = 0.0
        self.blue_display = 0.0
        self.red_target = 0.0
        self.blue_target = 0.0
        self.red_dice = 0
        self.blue_dice = 0
        self.red_steps = 0
        self.blue_steps = 0
        self.phase = 'idle'
        self.phase_timer = 0.0
        self.weather_active = False
        self.weather_type = WEATHER_NONE
        self.weather_timer = 0.0
        self.weather_target = ''
        self.special_label = ''
        self.special_timer = 0.0
        self.result_text = ''
        self.result_timer = 0.0
        self.log_lines = []
        self.viewport_offset = 0.0
        self.shake_intensity = 0.0
        self.anim_timer = 0.0
        self.step_label = ''
        self._red_last_weather_check = 0
        self._blue_last_weather_check = 0
        self.particles.clear()
        self._calc_layout()

    def _get_cell_x(self, col: int) -> float:
        return self.track_x + col * (CELL_W + CELL_GAP) - self.viewport_offset

    def _cell_color(self, idx: int) -> str:
        """Get cell color by board index (0=start, 1..99=pattern, 100=end)"""
        if idx <= 0:
            return CELL_START
        if idx >= BOARD_SIZE:
            return CELL_END
        mod = idx % 3
        if mod == 1:
            return CELL_RED
        elif mod == 2:
            return CELL_BLUE
        else:
            return CELL_GREY

    def handle_click(self, mouse_pos: tuple):
        if self.exit_btn_rect.collidepoint(mouse_pos):
            self.game_state = 'done'
            return

        if self.game_state == 'idle':
            if self.start_btn_rect.collidepoint(mouse_pos):
                self._start_race()
            return

        if self.game_state == 'racing' and self.phase == 'idle':
            if self.roll_btn_rect.collidepoint(mouse_pos):
                self._start_red_turn()
            return

        if self.game_state == 'result' and self.result_timer >= 1.0:
            self.game_state = 'done'

    def _start_race(self):
        self.game_state = 'racing'
        self.phase = 'idle'
        self.log_lines = ['游戏开始！你掷骰子吧']
        self.phase_timer = 0.0

    def _start_red_turn(self):
        self.phase = 'red_roll'
        self.phase_timer = 0.0
        self.red_dice = random.randint(1, 6)
        self.red_steps = self.red_dice
        self.log_lines.append(f'你掷了 {self.red_dice}')

        # Check special
        roll = random.random()
        cumulative = 0.0
        for sp in DICE_SPECIALS:
            cumulative += sp['prob']
            if roll <= cumulative:
                if sp['type'] == '+10':
                    self.red_steps += 10
                    self.special_label = '+10步！'
                elif sp['type'] == 'x2':
                    self.red_steps *= 2
                    self.special_label = '×2步！'
                elif sp['type'] == '/2':
                    self.red_steps = math.ceil(self.red_steps / 2)
                    self.special_label = '÷2步'
                self.special_timer = 1.5
                self.phase = 'red_special'
                self.log_lines.append(f'特效！{self.special_label}')
                self.step_label = MOVE_LABELS.get(sp['type'], '')
                break
        else:
            self.phase = 'red_move'

        self.red_target = self.red_pos + self.red_steps
        self.red_target = min(self.red_target, BOARD_SIZE)

    def _start_blue_turn(self):
        self.phase = 'blue_roll'
        self.phase_timer = 0.0
        self.blue_dice = random.randint(1, 6)
        self.blue_steps = self.blue_dice
        self.log_lines.append(f'蓝方掷了 {self.blue_dice}')

        roll = random.random()
        cumulative = 0.0
        for sp in DICE_SPECIALS:
            cumulative += sp['prob']
            if roll <= cumulative:
                if sp['type'] == '+10':
                    self.blue_steps += 10
                elif sp['type'] == 'x2':
                    self.blue_steps *= 2
                elif sp['type'] == '/2':
                    self.blue_steps = math.ceil(self.blue_steps / 2)
                self.log_lines.append('蓝方特效！')
                self.step_label = MOVE_LABELS.get(sp['type'], '')
                break

        self.blue_target = self.blue_pos + self.blue_steps
        self.blue_target = min(self.blue_target, BOARD_SIZE)
        self.phase = 'blue_move'

    def update(self, dt: float):
        self.particles.update(dt)
        self.anim_timer += dt
        self.shake_intensity *= (1 - dt * 6)

        if self.special_timer > 0:
            self.special_timer -= dt

        if self.game_state == 'racing':
            self._update_phase(dt)

        if self.weather_active:
            self.weather_timer -= dt
            if self.weather_timer <= 0:
                self.weather_active = False

        if len(self.log_lines) > 4:
            self.log_lines = self.log_lines[-4:]

        if self.game_state == 'result':
            self.result_timer += dt

    def _update_phase(self, dt: float):
        self.phase_timer += dt

        # Handle special display phase -> transition to move
        if self.phase == 'red_special':
            if self.special_timer <= 0:
                self.phase = 'red_move'

        # Smooth interpolation toward target
        move_speed = 8.0  # units per second for lerp
        if self.phase == 'red_move':
            diff = self.red_target - self.red_display
            if diff > 0.01:
                old_display = self.red_display
                step = diff * min(1.0, move_speed * dt)
                self.red_display += step
                # Check weather each time we cross a cell boundary
                new_cell = int(self.red_display) + 1
                old_cell = int(old_display) + 1
                if new_cell > old_cell:
                    last_check = getattr(self, '_red_last_weather_check', 0)
                    for cp in range(old_cell + 1, new_cell + 1):
                        if cp > last_check and cp < BOARD_SIZE:
                            self._red_last_weather_check = cp
                            if random.random() < WEATHER_PROB:
                                self._trigger_weather('red', cp)
            else:
                self.red_display = self.red_target
                self.red_pos = int(round(self.red_display))
                if self.red_pos >= BOARD_SIZE:
                    self.red_pos = BOARD_SIZE
                    self._end_round('red_win')
                    return
                self.phase = 'idle'
                self.phase_timer = 0.0
                self._start_blue_turn()

        if self.phase == 'blue_move':
            diff = self.blue_target - self.blue_display
            if diff > 0.01:
                old_display = self.blue_display
                step = diff * min(1.0, move_speed * dt)
                self.blue_display += step
                new_cell = int(self.blue_display) + 1
                old_cell = int(old_display) + 1
                if new_cell > old_cell:
                    last_check = getattr(self, '_blue_last_weather_check', 0)
                    for cp in range(old_cell + 1, new_cell + 1):
                        if cp > last_check and cp < BOARD_SIZE:
                            self._blue_last_weather_check = cp
                            if random.random() < WEATHER_PROB:
                                self._trigger_weather('blue', cp)
            else:
                self.blue_display = self.blue_target
                self.blue_pos = int(round(self.blue_display))
                if self.blue_pos >= BOARD_SIZE:
                    self.blue_pos = BOARD_SIZE
                    self._end_round('blue_win')
                    return
                self.phase = 'idle'
                self.phase_timer = 0.0

        # Update viewport to follow leading piece
        leading_pos = max(self.red_display, self.blue_display)
        leading_pixel = leading_pos * (CELL_W + CELL_GAP)
        target_offset = leading_pixel - self.viewport_w * 0.33
        self.viewport_offset += (target_offset - self.viewport_offset) * 0.08
        self.viewport_offset = max(0, min(self.viewport_offset, self.total_track_w - self.viewport_w))

    def _trigger_weather(self, who: str, cell_idx: int):
        w = random.choices(WEATHER_TYPES, weights=WEIGHTS, k=1)[0]
        cell_color = self._cell_color(cell_idx)

        self.weather_type = w
        self.weather_active = True
        self.weather_timer = 2.0
        self.weather_target = who

        if who == 'red':
            pos = self.red_pos
        else:
            pos = self.blue_pos

        if w == WEATHER_RED and cell_color == CELL_RED:
            new_pos = max(pos - 5, 0)
            if who == 'red':
                self.red_pos = new_pos
                self.red_display = float(new_pos)
                self.log_lines.append('红天！后退5步')
            else:
                self.blue_pos = new_pos
                self.blue_display = float(new_pos)
                self.log_lines.append('红天！蓝方后退5步')
        elif w == WEATHER_BLUE and cell_color == CELL_BLUE:
            new_pos = min(pos + 5, BOARD_SIZE)
            if who == 'red':
                self.red_pos = new_pos
                self.red_display = float(new_pos)
                self.log_lines.append('蓝天！前进5步')
                if self.red_pos >= BOARD_SIZE:
                    self._end_round('red_win')
                    return
            else:
                self.blue_pos = new_pos
                self.blue_display = float(new_pos)
                self.log_lines.append('蓝天！蓝方前进5步')
                if self.blue_pos >= BOARD_SIZE:
                    self._end_round('blue_win')
                    return
        elif w == WEATHER_GREY and cell_color == CELL_GREY:
            if who == 'red':
                self.red_pos = 0
                self.red_display = 0.0
                self.log_lines.append('灰天！回到起点')
            else:
                self.blue_pos = 0
                self.blue_display = 0.0
                self.log_lines.append('灰天！蓝方回到起点')

    def _end_round(self, winner: str):
        self.game_state = 'result'
        self.result_timer = 0.0
        self.shake_intensity = 8.0
        if winner == 'red_win':
            self.result_text = '你赢了！获得 ¥200'
            self.wallet.add(PRIZE)
            self.particles.emit_confetti(
                (WINDOW_WIDTH // 2, self.track_y + CELL_H),
                50, ['#FFD700', '#FF6B6B', '#FFFFFF'], lifetime=2.5
            )
        else:
            self.result_text = '蓝方先到终点！'
            self.particles.emit_confetti(
                (WINDOW_WIDTH // 2, self.track_y + CELL_H + CELL_GAP + CELL_H),
                30, ['#4A90D9', '#87CEEB', '#FFFFFF'], lifetime=2.0
            )

    def draw(self, surface: pygame.Surface):
        surface.fill(hex_to_rgb(COLORS['bg_primary']))
        draw_game_border(surface)

        ox, oy = 0.0, 0.0
        if self.shake_intensity > 0.5:
            ox = random.uniform(-self.shake_intensity, self.shake_intensity)
            oy = random.uniform(-self.shake_intensity, self.shake_intensity)

        self._draw_title(surface)
        self._draw_tracks(surface, ox, oy)
        self._draw_log(surface)

        if self.game_state == 'idle':
            self._draw_start_button(surface)
        elif self.game_state == 'racing':
            self._draw_turn_info(surface)
            if self.phase == 'idle':
                self._draw_roll_button(surface)
            if self.special_timer > 0:
                self._draw_special(surface)
            if self.weather_active:
                self._draw_weather(surface)
        elif self.game_state == 'result':
            self._draw_result(surface)

        self.particles.draw(surface)
        mouse_pos = get_mouse_pos()
        self.exit_btn_rect = draw_exit_button(surface, mouse_pos, font_size=s(26))

    def _draw_title(self, surface: pygame.Surface):
        draw_text_with_shadow(surface, '飞行棋', self.font_title,
                              COLORS['gold'], (WINDOW_WIDTH // 2, s(18)))

    def _draw_tracks(self, surface: pygame.Surface, ox: float, oy: float):
        ty = self.track_y + oy

        # Clip track drawing to viewport
        total_h = CELL_H * 2 + CELL_GAP * 2
        clip_rect = pygame.Rect(self.track_x, ty - 10, self.viewport_w, total_h + 80)
        surface.set_clip(clip_rect)

        # Track background
        total_w = TRACK_LENGTH * (CELL_W + CELL_GAP) - CELL_GAP
        track_bg = pygame.Rect(self.track_x - 4, ty - 4, total_w + 8, total_h + 8)
        pygame.draw.rect(surface, hex_to_rgb('#2d1515'), track_bg, border_radius=s(8))
        pygame.draw.rect(surface, hex_to_rgb(COLORS['gold_dark']), track_bg, s(2), border_radius=s(8))

        # Lane labels
        red_label = self.font_small.render('红(你)', True, hex_to_rgb('#FF6B6B'))
        blue_label = self.font_small.render('蓝(电脑)', True, hex_to_rgb('#4A90D9'))
        surface.blit(red_label, (self.track_x - s(70), ty + CELL_H // 2 - s(6)))
        surface.blit(blue_label, (self.track_x - s(75), ty + CELL_H * 2 + CELL_GAP + CELL_H // 2 - s(6)))

        # Only draw visible cells
        start_col = max(0, int(self.viewport_offset // (CELL_W + CELL_GAP)) - 1)
        end_col = min(TRACK_LENGTH, start_col + (self.viewport_w // (CELL_W + CELL_GAP)) + 3)

        for lane in range(2):
            for col in range(start_col, end_col):
                x = self._get_cell_x(col) + ox
                y = ty + lane * (CELL_H + CELL_GAP)

                # Determine cell color
                if col == 0:
                    bg_color = CELL_START
                elif col == TRACK_LENGTH - 1:
                    bg_color = CELL_END
                else:
                    bg_color = self._cell_color(col)

                pygame.draw.rect(surface, hex_to_rgb(bg_color),
                                 (x, y, CELL_W, CELL_H), border_radius=s(4))
                pygame.draw.rect(surface, (45, 45, 70),
                                 (x, y, CELL_W, CELL_H), 1, border_radius=s(4))

                # Cell number
                if col == TRACK_LENGTH - 1:
                    finish_surf = self.font_cell.render('终点', True, hex_to_rgb('#2D1515'))
                    surface.blit(finish_surf, finish_surf.get_rect(center=(x + CELL_W // 2, y + CELL_H // 2)))
                elif col > 0 and col % 10 == 0:
                    num_surf = self.font_cell.render(str(col), True, (60, 60, 80))
                    surface.blit(num_surf, num_surf.get_rect(center=(x + CELL_W // 2, y + CELL_H // 2)))

        # Finish line
        finish_x = self._get_cell_x(TRACK_LENGTH - 1) + CELL_W + ox
        pygame.draw.line(surface, hex_to_rgb(COLORS['gold']),
                         (finish_x, ty - 4), (finish_x, ty + total_h + 4), s(3))

        # Draw pieces
        self._draw_piece(surface, 'red', ox, oy)
        self._draw_piece(surface, 'blue', ox, oy)

        # Reset clip
        surface.set_clip(None)

        # Step label
        if self.step_label and self.game_state == 'racing':
            step_font = get_font(48, bold=True)
            step_surf = step_font.render(self.step_label, True, hex_to_rgb(COLORS['gold']))
            alpha = int(200 + 55 * math.sin(self.anim_timer * 6))
            step_surf.set_alpha(alpha)
            surface.blit(step_surf, step_surf.get_rect(
                center=(WINDOW_WIDTH // 2, ty + total_h + s(50))))

        # Progress bars
        bar_x = self.track_x + s(10)
        bar_y = ty - s(30)
        bar_w = self.viewport_w - s(20)
        bar_h = s(6)
        pygame.draw.rect(surface, (40, 40, 60), (bar_x, bar_y, bar_w, bar_h), border_radius=s(3))
        red_progress = min(self.red_display / TRACK_LENGTH, 1.0)
        blue_progress = min(self.blue_display / TRACK_LENGTH, 1.0)
        pygame.draw.rect(surface, hex_to_rgb('#FF6B6B'),
                         (bar_x, bar_y, bar_w * red_progress, bar_h), border_radius=s(3))
        pygame.draw.rect(surface, hex_to_rgb('#4A90D9'),
                         (bar_x, bar_y + bar_h + s(2), bar_w * blue_progress, bar_h), border_radius=s(3))

    def _draw_piece(self, surface: pygame.Surface, color: str, ox: float, oy: float):
        pos = self.red_display if color == 'red' else self.blue_display
        lane = 0 if color == 'red' else 1

        ty = self.track_y + oy + lane * (CELL_H + CELL_GAP)

        # Map position to cell x
        display_pos = clamp(pos, 0, TRACK_LENGTH)
        cell_idx = min(int(display_pos), TRACK_LENGTH - 1)
        cell_offset = display_pos - cell_idx  # 0-1 within cell

        x = self._get_cell_x(cell_idx) + ox + cell_offset * (CELL_W + CELL_GAP)
        y = ty + CELL_H // 2

        piece_color = hex_to_rgb('#CC3333') if color == 'red' else hex_to_rgb('#3333CC')
        glow_color = hex_to_rgb('#FF6666') if color == 'red' else hex_to_rgb('#6666FF')

        # Glow
        glow_surf = pygame.Surface((s(30), s(30)), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*glow_color, 40), (s(15), s(15)), s(14))
        surface.blit(glow_surf, (int(x) - s(15), int(y) - s(15)))

        # Piece body
        pygame.draw.circle(surface, piece_color, (int(x), int(y)), s(12))
        pygame.draw.circle(surface, glow_color, (int(x) - s(3), int(y) - s(4)), s(5))

        # Direction arrow
        pygame.draw.polygon(surface, piece_color, [
            (int(x) + s(12), int(y)),
            (int(x) + s(20), int(y) - s(5)),
            (int(x) + s(20), int(y) + s(5)),
        ])

        # Weather indicator on piece
        if self.weather_active and self.weather_target == color:
            w_color = WEATHER_COLORS.get(self.weather_type, '#AAAAAA')
            weather_alpha = int(200 + 55 * math.sin(self.anim_timer * 8))
            w_surf = self.font_cell.render(WEATHER_NAMES[self.weather_type], True, hex_to_rgb(w_color))
            w_surf.set_alpha(weather_alpha)
            surface.blit(w_surf, w_surf.get_rect(center=(int(x), int(y) - s(28))))

    def _draw_start_button(self, surface: pygame.Surface):
        btn_w, btn_h = s(200), s(55)
        btn_x = WINDOW_WIDTH // 2
        btn_y = self.track_y + CELL_H * 2 + CELL_GAP * 2 + s(100)
        self.start_btn_rect = pygame.Rect(btn_x - btn_w // 2, btn_y, btn_w, btn_h)

        mouse_pos = get_mouse_pos()
        is_hover = self.start_btn_rect.collidepoint(mouse_pos)

        bg_color = hex_to_rgb(COLORS['gold']) if is_hover else hex_to_rgb(COLORS['gold_dark'])
        pygame.draw.rect(surface, bg_color, self.start_btn_rect, border_radius=s(12))
        pygame.draw.rect(surface, hex_to_rgb(COLORS['gold_light']), self.start_btn_rect,
                         s(2), border_radius=s(12))

        btn_surf = self.font_btn.render(f'开始游戏 ¥{FLYING_CHESS_ENTRY_COST}', True, hex_to_rgb('#2D1515'))
        surface.blit(btn_surf, btn_surf.get_rect(center=(btn_x, btn_y + btn_h // 2)))

    def _draw_turn_info(self, surface: pygame.Surface):
        cx = WINDOW_WIDTH // 2
        info_y = self.track_y + CELL_H * 2 + CELL_GAP * 2 + s(15)

        phase_texts = {
            'red_roll': f'你掷了 {self.red_dice}',
            'red_special': f'{self.special_label}',
            'red_move': f'前进中... {int(round(self.red_display))}/{self.red_steps}',
            'blue_roll': f'蓝方掷了 {self.blue_dice}',
            'blue_move': f'蓝方前进中... {int(round(self.blue_display))}/{self.blue_steps}',
        }
        text = phase_texts.get(self.phase, '')
        if text:
            surf = self.font_small.render(text, True, hex_to_rgb(COLORS['gold']))
            surface.blit(surf, surf.get_rect(center=(cx, info_y)))

    def _draw_roll_button(self, surface: pygame.Surface):
        btn_w, btn_h = s(200), s(60)
        btn_x = WINDOW_WIDTH // 2
        btn_y = self.track_y + CELL_H * 2 + CELL_GAP * 2 + s(120)
        self.roll_btn_rect = pygame.Rect(btn_x - btn_w // 2, btn_y, btn_w, btn_h)

        mouse_pos = get_mouse_pos()
        is_hover = self.roll_btn_rect.collidepoint(mouse_pos)

        bg_color = hex_to_rgb(COLORS['gold']) if is_hover else hex_to_rgb(COLORS['gold_dark'])
        pygame.draw.rect(surface, bg_color, self.roll_btn_rect, border_radius=s(12))
        pygame.draw.rect(surface, hex_to_rgb(COLORS['gold_light']), self.roll_btn_rect,
                         s(2), border_radius=s(12))

        btn_surf = self.font_btn.render('掷骰子', True, hex_to_rgb('#2D1515'))
        surface.blit(btn_surf, btn_surf.get_rect(center=(btn_x, btn_y + btn_h // 2)))

    def _draw_log(self, surface: pygame.Surface):
        if not self.log_lines:
            return
        log_y = self.track_y + CELL_H * 2 + CELL_GAP * 2 + s(180)
        cx = WINDOW_WIDTH // 2

        for i, line in enumerate(self.log_lines):
            surf = self.font_log.render(line, True, hex_to_rgb(COLORS['text_secondary']))
            surface.blit(surf, surf.get_rect(center=(cx, log_y + i * s(22))))

    def _draw_special(self, surface: pygame.Surface):
        alpha = int(255 * min(1.0, self.special_timer))
        cx = WINDOW_WIDTH // 2
        cy = s(70)

        surf = self.font_btn.render(self.special_label, True, hex_to_rgb('#FFD700'))
        surf.set_alpha(alpha)
        surface.blit(surf, surf.get_rect(center=(cx, cy)))

    def _draw_weather(self, surface: pygame.Surface):
        if not self.weather_active:
            return

        w_color = WEATHER_COLORS.get(self.weather_type, '#AAAAAA')
        cx = WINDOW_WIDTH // 2
        cy = self.track_y + CELL_H // 2

        surf = self.font_btn.render(f'{WEATHER_NAMES[self.weather_type]}!', True, hex_to_rgb(w_color))
        surface.blit(surf, surf.get_rect(center=(cx, cy)))

    def _draw_result(self, surface: pygame.Surface):
        if self.result_timer < 0.2:
            return

        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        progress = min(1.0, (self.result_timer - 0.2) / 0.5)
        eased = ease_out_quad(progress)
        overlay.fill((0, 0, 0, int(140 * eased)))
        surface.blit(overlay, (0, 0))

        result_color = hex_to_rgb(COLORS['gold']) if '你赢' in self.result_text else hex_to_rgb(COLORS['red_primary'])
        draw_text_with_shadow(surface, self.result_text, self.font_result,
                              result_color, (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - s(20)))

        sub_text = f'你: {self.red_pos}  蓝方: {self.blue_pos}'
        sub_surf = self.font_small.render(sub_text, True, hex_to_rgb(COLORS['text_secondary']))
        surface.blit(sub_surf, sub_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + s(50))))

        if self.result_timer >= 1.0:
            draw_breathing_hint(surface, '点击任意位置返回', self.font_small,
                                COLORS['text_secondary'],
                                (WINDOW_WIDTH // 2, WINDOW_HEIGHT - s(50)),
                                self.result_timer, speed=4)
