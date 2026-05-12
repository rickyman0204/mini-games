"""Exam Grading - judge 5 questions right or wrong"""
import random
import math
import pygame

from src.settings import (
    WINDOW_WIDTH, WINDOW_HEIGHT, COLORS,
)
from src.utils import (
    s, get_font, hex_to_rgb, get_mouse_pos,
    draw_text_with_shadow, draw_exit_button, draw_game_border,
    draw_breathing_hint, ease_out_quad, ease_out_back,
)
from src.particles import ParticleEmitter

QUESTION_VALUES = [5, 10, 20, 50, 100]
PASS_THRESHOLD = 60

# Symbol pattern questions — each shows a pattern, player judges 对/错
QUESTION_BANK = [
    '★ ★ ★  ★ ★',
    '◆ ◇ ◆ ◇ ◆',
    '△ ▽ △ ▽ △',
    '○ ● ○ ● ○',
    '▲ ▼ ▲ ▼ ▲',
    '♠ ♣ ♠ ♣ ♠',
    '♥ ♦ ♥ ♦ ♥',
    '⬛ ⬜ ⬛ ⬜ ⬛',
    '⚫ ⚪ ⚫ ⚪ ⚫',
    '✦ ✧ ✦ ✧ ✦',
    '◐ ◑ ◐ ◑ ◐',
    '☀ ☽ ☀ ☽ ☀',
    '⊕ ⊗ ⊕ ⊗ ⊕',
    '⟐ ⟑ ⟐ ⟑ ⟐',
    '⬟ ⬡ ⬟ ⬡ ⬟',
    '✿ ❀ ✿ ❀ ✿',
    '☯ ☮ ☯ ☮ ☯',
    '⚿ ⛎ ⚿ ⛎ ⚿',
    '◉ ◎ ◉ ◎ ◉',
    '⚙ ⚒ ⚙ ⚒ ⚙',
    '∞ ∝ ∞ ∝ ∞',
    '∑ ∏ ∑ ∏ ∑',
    '∫ ∂ ∫ ∂ ∫',
    '⊞ ⊟ ⊞ ⊟ ⊞',
    '♩ ♪ ♩ ♪ ♩',
]

REVEAL_STAGGER = 0.6
RESULT_DURATION = 2.0


class ExamGradingGame:

    def __init__(self, wallet):
        self.wallet = wallet
        self.particles = ParticleEmitter()

        # States: 'idle' -> 'answering' -> 'grading' -> 'result' -> 'done'
        self.game_state = 'idle'

        self.questions = []
        # Player's answers: True = chose "对", False = chose "错", None = not answered
        self.answers = []
        # Actual results: True = correct, False = wrong (50/50 random)
        self.results = []
        # Reveal progress
        self.revealed = []
        self.reveal_timer = 0.0
        self.current_index = 0
        self.total_score = 0
        self.result_money = 0

        self.shake_intensity = 0.0
        self.result_timer = 0.0
        self.bob_timer = 0.0

        self.start_btn_rect = pygame.Rect(0, 0, 0, 0)
        self.grade_btn_rect = pygame.Rect(0, 0, 0, 0)
        self.exit_btn_rect = pygame.Rect(0, 0, 0, 0)
        self.choice_btn = {
            'right': pygame.Rect(0, 0, 0, 0),
            'wrong': pygame.Rect(0, 0, 0, 0),
        }

        self.font_title = get_font(58, bold=True)
        self.font_big = get_font(70, bold=True)
        self.font_question = get_font(26, bold=True)
        self.font_value = get_font(24, bold=True)
        self.font_small = get_font(26)
        self.font_btn = get_font(38, bold=True)
        self.font_score = get_font(48, bold=True)
        self.font_choice = get_font(52, bold=True)

    def reset(self):
        self.game_state = 'idle'
        self.questions = random.sample(QUESTION_BANK, len(QUESTION_VALUES))
        self.answers = [None] * len(QUESTION_VALUES)
        self.results = []
        self.revealed = [False] * len(QUESTION_VALUES)
        self.reveal_timer = 0.0
        self.current_index = 0
        self.total_score = 0
        self.result_money = 0
        self.shake_intensity = 0.0
        self.result_timer = 0.0
        self.bob_timer = 0.0
        self.particles.clear()

    def handle_click(self, mouse_pos: tuple):
        if self.exit_btn_rect.collidepoint(mouse_pos):
            self.game_state = 'done'
            return

        if self.game_state == 'idle':
            if self.start_btn_rect.collidepoint(mouse_pos):
                self.game_state = 'answering'
                self.answers = [None] * len(QUESTION_VALUES)
                self.current_index = 0
            return

        if self.game_state == 'answering':
            # Check right/wrong choice buttons
            if self.choice_btn['right'].collidepoint(mouse_pos):
                self.answers[self.current_index] = True
                self._advance_current_index()
                return
            if self.choice_btn['wrong'].collidepoint(mouse_pos):
                self.answers[self.current_index] = False
                self._advance_current_index()
                return

            # Check grade button if all answered
            if all(a is not None for a in self.answers) and self.grade_btn_rect.collidepoint(mouse_pos):
                self._start_grading()
                return

        if self.game_state == 'result' and self.result_timer >= 0.5:
            self.game_state = 'done'

    def _advance_current_index(self):
        """Move to next unanswered question, or stay if all answered"""
        for i in range(len(self.answers)):
            if self.answers[i] is None:
                self.current_index = i
                return

    def _start_grading(self):
        self.game_state = 'grading'
        # Generate 50/50 results for each question
        self.results = [random.choice([True, False]) for _ in range(len(QUESTION_VALUES))]
        self.reveal_timer = 0.0
        self.current_index = 0

    def update(self, dt: float):
        self.bob_timer += dt
        self.particles.update(dt)
        self.shake_intensity *= (1 - dt * 6)

        if self.game_state == 'grading':
            self.reveal_timer += dt

            idx = int(self.reveal_timer / REVEAL_STAGGER)
            if idx != self.current_index and idx < len(QUESTION_VALUES):
                self.current_index = idx

            for i in range(min(idx + 1, len(QUESTION_VALUES))):
                if not self.revealed[i]:
                    self.revealed[i] = True
                    if self.results[i]:
                        self.total_score += QUESTION_VALUES[i]
                        self.particles.emit_confetti(
                            (WINDOW_WIDTH // 2, self._get_question_y(i)),
                            15, ['#2ECC71', '#27AE60', '#FFFFFF'], lifetime=1.0
                        )
                    else:
                        self.shake_intensity = 8.0

            if all(self.revealed):
                if self.reveal_timer - len(QUESTION_VALUES) * REVEAL_STAGGER >= RESULT_DURATION:
                    self._end_round()

        if self.game_state == 'result':
            self.result_timer += dt

    def _get_question_y(self, index: int) -> int:
        start_y = s(140)
        spacing = s(95)
        return start_y + index * spacing

    def _end_round(self):
        self.game_state = 'result'
        self.result_timer = 0.0
        if self.total_score >= PASS_THRESHOLD:
            self.result_money = self.total_score
            self.particles.emit_confetti(
                (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2),
                50, ['#FFD700', '#FFFFFF', '#FFA500'], lifetime=2.0
            )
        self.wallet.add(self.result_money)

    def draw(self, surface: pygame.Surface):
        surface.fill(hex_to_rgb(COLORS['bg_primary']))
        draw_game_border(surface)

        ox, oy = 0, 0
        if self.shake_intensity > 0.5:
            ox = random.uniform(-self.shake_intensity, self.shake_intensity)
            oy = random.uniform(-self.shake_intensity, self.shake_intensity)

        self._draw_title(surface)

        if self.game_state == 'idle':
            self._draw_questions_preview(surface)
            self._draw_start_button(surface)
        elif self.game_state == 'answering':
            self._draw_answer_phase(surface)
        elif self.game_state == 'grading':
            self._draw_questions_with_results(surface, ox, oy)
        elif self.game_state == 'result':
            self._draw_questions_with_results(surface, ox, oy)
            self._draw_result_overlay(surface)

        mouse_pos = get_mouse_pos()
        self.exit_btn_rect = draw_exit_button(surface, mouse_pos, font_size=s(26))

    def _draw_title(self, surface: pygame.Surface):
        draw_text_with_shadow(surface, '试卷批阅', self.font_title,
                              COLORS['gold'], (WINDOW_WIDTH // 2, s(24)))

    def _draw_questions_preview(self, surface: pygame.Surface):
        cx = WINDOW_WIDTH // 2
        start_y = s(130)
        spacing = s(95)

        for i, (q, val) in enumerate(zip(self.questions, QUESTION_VALUES)):
            y = start_y + i * spacing

            panel_w = s(600)
            panel_h = s(50)
            panel_x = cx - panel_w // 2
            panel_y = y - panel_h // 2

            pygame.draw.rect(surface, hex_to_rgb(COLORS['card_bg']),
                             (panel_x, panel_y, panel_w, panel_h), border_radius=s(8))
            pygame.draw.rect(surface, hex_to_rgb(COLORS['card_border']),
                             (panel_x, panel_y, panel_w, panel_h), s(2), border_radius=s(8))

            val_text = f'¥{val}'
            val_surf = self.font_value.render(val_text, True, hex_to_rgb(COLORS['gold']))
            surface.blit(val_surf, (panel_x + s(16), panel_y + panel_h // 2 - val_surf.get_height() // 2))

            q_surf = self.font_question.render(q, True, hex_to_rgb(COLORS['text_primary']))
            surface.blit(q_surf, (panel_x + s(100), panel_y + panel_h // 2 - q_surf.get_height() // 2))

    def _draw_start_button(self, surface: pygame.Surface):
        btn_w, btn_h = s(200), s(60)
        btn_x = WINDOW_WIDTH // 2
        btn_y = WINDOW_HEIGHT - s(100)
        self.start_btn_rect = pygame.Rect(btn_x - btn_w // 2, btn_y, btn_w, btn_h)

        mouse_pos = get_mouse_pos()
        is_hover = self.start_btn_rect.collidepoint(mouse_pos)

        bg_color = hex_to_rgb(COLORS['gold']) if is_hover else hex_to_rgb(COLORS['gold_dark'])
        pygame.draw.rect(surface, bg_color, self.start_btn_rect, border_radius=s(12))
        pygame.draw.rect(surface, hex_to_rgb(COLORS['gold_light']), self.start_btn_rect,
                         s(2), border_radius=s(12))

        btn_surf = self.font_btn.render('开始答题', True, hex_to_rgb('#2D1515'))
        surface.blit(btn_surf, btn_surf.get_rect(center=(btn_x, btn_y + btn_h // 2)))

    def _draw_answer_phase(self, surface: pygame.Surface):
        cx = WINDOW_WIDTH // 2
        start_y = s(140)
        spacing = s(95)

        # Draw all questions
        for i, (q, val) in enumerate(zip(self.questions, QUESTION_VALUES)):
            y = start_y + i * spacing
            if i == self.current_index and self.answers[i] is None:
                # Current unanswered question — highlight
                self._draw_current_question(surface, cx, y, q, val, i)
            elif self.answers[i] is not None:
                # Already answered
                self._draw_answered_question(surface, cx, y, q, val, i)
            else:
                # Not yet answered, muted
                self._draw_upcoming_question(surface, cx, y, q, val, i)

        # Progress indicator
        answered_count = sum(1 for a in self.answers if a is not None)
        progress_text = f'{answered_count}/{len(QUESTION_VALUES)} 已答'
        draw_text_with_shadow(surface, progress_text, self.font_small,
                              COLORS['text_secondary'], (cx, s(80)))

        # Grade button if all answered
        if all(a is not None for a in self.answers):
            self._draw_grade_button(surface)

    def _draw_current_question(self, surface: pygame.Surface, cx: int, y: int,
                                q: str, val: int, index: int):
        panel_w = s(600)
        panel_h = s(100)
        panel_x = cx - panel_w // 2
        panel_y = y - panel_h // 2

        # Glowing border
        pulse = 0.5 + 0.5 * math.sin(self.bob_timer * 4)
        border_color = hex_to_rgb(COLORS['gold']) if pulse > 0.5 else hex_to_rgb(COLORS['gold_dark'])

        pygame.draw.rect(surface, hex_to_rgb(COLORS['card_bg']),
                         (panel_x, panel_y, panel_w, panel_h), border_radius=s(12))
        pygame.draw.rect(surface, border_color,
                         (panel_x, panel_y, panel_w, panel_h), s(3), border_radius=s(12))

        # Question number + value
        num_surf = self.font_value.render(f'Q{index + 1}', True, hex_to_rgb(COLORS['gold']))
        surface.blit(num_surf, (panel_x + s(16), panel_y + s(10)))

        val_surf = self.font_value.render(f'¥{val}', True, hex_to_rgb(COLORS['gold']))
        surface.blit(val_surf, (panel_x + panel_w - s(80), panel_y + s(10)))

        # Question text
        q_surf = self.font_question.render(q, True, hex_to_rgb(COLORS['text_primary']))
        surface.blit(q_surf, (panel_x + s(100), panel_y + panel_h // 2 - q_surf.get_height() // 2))

        # 对 / 错 buttons
        btn_w, btn_h = s(120), s(50)
        btn_gap = s(40)
        total_w = btn_w * 2 + btn_gap
        btn_x_start = cx - total_w // 2
        btn_y = panel_y + panel_h - btn_h - s(10)

        # Right button (green)
        self.choice_btn['right'] = pygame.Rect(btn_x_start, btn_y, btn_w, btn_h)
        mouse_pos = get_mouse_pos()
        is_hover_right = self.choice_btn['right'].collidepoint(mouse_pos)

        bg_right = hex_to_rgb('#3da848') if is_hover_right else hex_to_rgb('#2d7a38')
        pygame.draw.rect(surface, bg_right, self.choice_btn['right'], border_radius=s(8))
        pygame.draw.rect(surface, hex_to_rgb('#51cf66'), self.choice_btn['right'], s(2), border_radius=s(8))
        right_surf = self.font_choice.render('✓ 对', True, (255, 255, 255))
        surface.blit(right_surf, right_surf.get_rect(center=self.choice_btn['right'].center))

        # Wrong button (red)
        self.choice_btn['wrong'] = pygame.Rect(btn_x_start + btn_w + btn_gap, btn_y, btn_w, btn_h)
        is_hover_wrong = self.choice_btn['wrong'].collidepoint(mouse_pos)

        bg_wrong = hex_to_rgb('#c94040') if is_hover_wrong else hex_to_rgb('#a03030')
        pygame.draw.rect(surface, bg_wrong, self.choice_btn['wrong'], border_radius=s(8))
        pygame.draw.rect(surface, hex_to_rgb('#ff5e5e'), self.choice_btn['wrong'], s(2), border_radius=s(8))
        wrong_surf = self.font_choice.render('✗ 错', True, (255, 255, 255))
        surface.blit(wrong_surf, wrong_surf.get_rect(center=self.choice_btn['wrong'].center))

    def _draw_answered_question(self, surface: pygame.Surface, cx: int, y: int,
                                 q: str, val: int, index: int):
        panel_w = s(600)
        panel_h = s(50)
        panel_x = cx - panel_w // 2
        panel_y = y - panel_h // 2

        chosen = self.answers[index]
        chosen_text = '✓ 对' if chosen else '✗ 错'

        # Panel with chosen answer
        pygame.draw.rect(surface, hex_to_rgb(COLORS['card_bg']),
                         (panel_x, panel_y, panel_w, panel_h), border_radius=s(8))
        pygame.draw.rect(surface, hex_to_rgb(COLORS['card_border']),
                         (panel_x, panel_y, panel_w, panel_h), s(1), border_radius=s(8))

        # Question number
        num_surf = self.font_value.render(f'Q{index + 1}', True, hex_to_rgb(COLORS['text_secondary']))
        surface.blit(num_surf, (panel_x + s(16), panel_y + panel_h // 2 - num_surf.get_height() // 2))

        # Question text (muted)
        q_surf = self.font_question.render(q, True, hex_to_rgb(COLORS['text_secondary']))
        surface.blit(q_surf, (panel_x + s(100), panel_y + panel_h // 2 - q_surf.get_height() // 2))

        # Chosen answer
        choice_surf = self.font_value.render(chosen_text, True, hex_to_rgb(COLORS['gold']))
        surface.blit(choice_surf, (panel_x + panel_w - s(100), panel_y + panel_h // 2 - choice_surf.get_height() // 2))

    def _draw_upcoming_question(self, surface: pygame.Surface, cx: int, y: int,
                                 q: str, val: int, index: int):
        panel_w = s(600)
        panel_h = s(50)
        panel_x = cx - panel_w // 2
        panel_y = y - panel_h // 2

        pygame.draw.rect(surface, hex_to_rgb('#1a1a1a'),
                         (panel_x, panel_y, panel_w, panel_h), border_radius=s(8))
        pygame.draw.rect(surface, hex_to_rgb(COLORS['text_muted']),
                         (panel_x, panel_y, panel_w, panel_h), s(1), border_radius=s(8))

        num_surf = self.font_value.render(f'Q{index + 1}', True, hex_to_rgb(COLORS['text_muted']))
        surface.blit(num_surf, (panel_x + s(16), panel_y + panel_h // 2 - num_surf.get_height() // 2))

        q_surf = self.font_question.render(q, True, hex_to_rgb(COLORS['text_muted']))
        surface.blit(q_surf, (panel_x + s(100), panel_y + panel_h // 2 - q_surf.get_height() // 2))

        val_surf = self.font_value.render(f'¥{val}', True, hex_to_rgb(COLORS['text_muted']))
        surface.blit(val_surf, (panel_x + panel_w - s(80), panel_y + panel_h // 2 - val_surf.get_height() // 2))

    def _draw_grade_button(self, surface: pygame.Surface):
        btn_w, btn_h = s(200), s(60)
        btn_x = WINDOW_WIDTH // 2
        btn_y = WINDOW_HEIGHT - s(100)
        self.grade_btn_rect = pygame.Rect(btn_x - btn_w // 2, btn_y, btn_w, btn_h)

        mouse_pos = get_mouse_pos()
        is_hover = self.grade_btn_rect.collidepoint(mouse_pos)

        bg_color = hex_to_rgb(COLORS['gold']) if is_hover else hex_to_rgb(COLORS['gold_dark'])
        pygame.draw.rect(surface, bg_color, self.grade_btn_rect, border_radius=s(12))
        pygame.draw.rect(surface, hex_to_rgb(COLORS['gold_light']), self.grade_btn_rect,
                         s(2), border_radius=s(12))

        btn_surf = self.font_btn.render('批阅试卷', True, hex_to_rgb('#2D1515'))
        surface.blit(btn_surf, btn_surf.get_rect(center=(btn_x, btn_y + btn_h // 2)))

    def _draw_questions_with_results(self, surface: pygame.Surface, ox: float, oy: float):
        cx = WINDOW_WIDTH // 2
        start_y = s(140)
        spacing = s(95)

        for i, (q, val) in enumerate(zip(self.questions, QUESTION_VALUES)):
            y = start_y + i * spacing
            if not self.revealed[i]:
                self._draw_unrevealed_question(surface, cx, y, q, val, i)
            else:
                self._draw_revealed_question(surface, cx, y, q, val, i, ox, oy)

    def _draw_unrevealed_question(self, surface: pygame.Surface, cx: int, y: int,
                                   q: str, val: int, index: int):
        panel_w = s(600)
        panel_h = s(50)
        panel_x = cx - panel_w // 2
        panel_y = y - panel_h // 2

        chosen = self.answers[index]
        chosen_text = '✓ 对' if chosen else '✗ 错'

        pygame.draw.rect(surface, hex_to_rgb('#1a1a1a'),
                         (panel_x, panel_y, panel_w, panel_h), border_radius=s(8))
        pygame.draw.rect(surface, hex_to_rgb(COLORS['text_muted']),
                         (panel_x, panel_y, panel_w, panel_h), s(2), border_radius=s(8))

        choice_surf = self.font_value.render(chosen_text, True, hex_to_rgb(COLORS['text_muted']))
        surface.blit(choice_surf, (panel_x + panel_w - s(100), panel_y + panel_h // 2 - choice_surf.get_height() // 2))

        q_surf = self.font_question.render(q, True, hex_to_rgb(COLORS['text_muted']))
        surface.blit(q_surf, (panel_x + s(100), panel_y + panel_h // 2 - q_surf.get_height() // 2))

    def _draw_revealed_question(self, surface: pygame.Surface, cx: int, y: int,
                                 q: str, val: int, index: int, ox: float, oy: float):
        panel_w = s(600)
        panel_h = s(50)
        panel_x = cx - panel_w // 2
        panel_y = y - panel_h // 2

        is_correct = self.results[index]

        if is_correct:
            panel_color = hex_to_rgb('#1a3a1a')
            border_color = hex_to_rgb('#2ECC71')
            text_color = hex_to_rgb(COLORS['text_primary'])
        else:
            panel_color = hex_to_rgb('#3a1a1a')
            border_color = hex_to_rgb('#E74C3C')
            text_color = hex_to_rgb(COLORS['text_primary'])

        pygame.draw.rect(surface, panel_color,
                         (panel_x, panel_y, panel_w, panel_h), border_radius=s(8))
        pygame.draw.rect(surface, border_color,
                         (panel_x, panel_y, panel_w, panel_h), s(2), border_radius=s(8))

        symbol_color = hex_to_rgb('#2ECC71') if is_correct else hex_to_rgb('#E74C3C')

        scale = 1.0
        reveal_progress = self.reveal_timer - index * REVEAL_STAGGER
        if 0 <= reveal_progress < 0.5:
            t = reveal_progress / 0.5
            scale = 1.0 + 0.3 * math.sin(t * math.pi)

        symbol_size = int(s(22) * scale)
        symbol_cx = panel_x + s(30)
        symbol_cy = panel_y + panel_h // 2
        self._draw_symbol(surface, symbol_cx, symbol_cy, symbol_size, is_correct, symbol_color)

        q_surf = self.font_question.render(q, True, text_color)
        surface.blit(q_surf, (panel_x + s(70), panel_y + panel_h // 2 - q_surf.get_height() // 2))

        val_surf = self.font_value.render(f'+¥{val}' if is_correct else '¥0',
                                           True, symbol_color)
        surface.blit(val_surf, (panel_x + panel_w - s(70) - val_surf.get_width(),
                                panel_y + panel_h // 2 - val_surf.get_height() // 2))

        if self.total_score > 0 and is_correct:
            score_surf = self.font_score.render(f'累计: ¥{self.total_score}',
                                                 True, hex_to_rgb(COLORS['gold']))
            surface.blit(score_surf, score_surf.get_rect(center=(cx, WINDOW_HEIGHT - s(60))))

    def _draw_symbol(self, surface, cx: int, cy: int, size: int, is_correct: bool, color: tuple):
        thickness = max(3, size // 5)
        half = size // 2

        if is_correct:
            pts = [
                (cx - half, cy),
                (cx - half // 3, cy + half // 2),
                (cx + half, cy - half // 2),
            ]
            pygame.draw.lines(surface, color, False, pts, thickness)
        else:
            pygame.draw.line(surface, color, (cx - half, cy - half), (cx + half, cy + half), thickness)
            pygame.draw.line(surface, color, (cx + half, cy - half), (cx - half, cy + half), thickness)

    def _draw_result_overlay(self, surface: pygame.Surface):
        if self.result_timer < 0.2:
            return

        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        progress = min(1.0, (self.result_timer - 0.2) / 0.5)
        eased = ease_out_quad(progress)
        overlay.fill((0, 0, 0, int(160 * eased)))
        surface.blit(overlay, (0, 0))

        cx = WINDOW_WIDTH // 2
        cy = WINDOW_HEIGHT // 2 - s(20)

        passed = self.total_score >= PASS_THRESHOLD

        if passed:
            result_text = f'及格！获得 ¥{self.result_money}'
            result_color = hex_to_rgb(COLORS['gold'])
        else:
            result_text = f'不及格！得分 ¥{self.total_score} < ¥{PASS_THRESHOLD}'
            result_color = hex_to_rgb(COLORS['red_primary'])

        draw_text_with_shadow(surface, result_text, self.font_big,
                              result_color, (cx, cy))

        sub_text = f'总分: ¥{self.total_score} / ¥{sum(QUESTION_VALUES)}'
        sub_font = get_font(28)
        sub_surf = sub_font.render(sub_text, True, hex_to_rgb(COLORS['text_secondary']))
        surface.blit(sub_surf, sub_surf.get_rect(center=(cx, cy + s(50))))

        if self.result_timer >= 0.5:
            draw_breathing_hint(surface, '点击任意位置返回', sub_font,
                                COLORS['text_secondary'],
                                (WINDOW_WIDTH // 2, WINDOW_HEIGHT - s(50)),
                                self.result_timer, speed=4)
