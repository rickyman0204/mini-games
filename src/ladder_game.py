"""Ladder climbing game - climb higher, save money, but risk falling"""
import math
import random
import pygame

from src.settings import (
    WINDOW_WIDTH, WINDOW_HEIGHT, COLORS,
    LADDER_ENTRY_COST, LADDER_START_FALL_RATE, LADDER_FALL_RATE_INCREMENT,
    LADDER_SAVE_MIN, LADDER_SAVE_MAX
)
from src.utils import get_mouse_pos, clamp, ease_out_quad, hex_to_rgb
from src.particles import ParticleEmitter


# How many rungs to show on screen
VISIBLE_RUNGS = 8
STEP_DURATION = 0.8        # Time for climb/fall animation
MAX_STEP = 20              # Maximum steps before auto-win


class LadderGame:
    """Climb the ladder, save money each step, risk falling"""

    def __init__(self, wallet):
        self.wallet = wallet
        self.particles = ParticleEmitter()

        # Game state: 'idle', 'climbing', 'falling', 'safe', 'result', 'done'
        self.game_state = 'idle'

        # Progress
        self.current_step = 0       # Which step we're on
        self.accumulated = 0        # Money accumulated
        self.step_saves = []        # How much saved each step

        # Result
        self.result_timer = 0.0
        self.fell_from = 0

        # Animation
        self.anim_timer = 0.0
        self.anim_from_y = 0
        self.anim_to_y = 0
        self.player_y = 0.0         # Current player visual position
        self.shake_intensity = 0.0
        self.door_glow = 0.0

        # Particle emitted
        self.particle_emitted = False

        # Fonts
        self.font_title = pygame.font.SysFont('microsoftyahei', 36, bold=True)
        self.font_big = pygame.font.SysFont('microsoftyahei', 60, bold=True)
        self.font_info = pygame.font.SysFont('microsoftyahei', 20)
        self.font_small = pygame.font.SysFont('microsoftyahei', 16)
        self.font_money = pygame.font.SysFont('microsoftyahei', 28, bold=True)

        # Ladder positions
        self.ladder_x = WINDOW_WIDTH // 2
        self.rung_spacing = 50
        self.ladder_width = 120
        self.player_size = 30

    def reset(self):
        """Reset game state"""
        self.game_state = 'idle'
        self.current_step = 0
        self.accumulated = 0
        self.step_saves = []
        self.result_timer = 0.0
        self.fell_from = 0
        self.anim_timer = 0.0
        self.player_y = 0.0
        self.shake_intensity = 0.0
        self.door_glow = 0.0
        self.particle_emitted = False
        self.particles.clear()

    def handle_click(self, mouse_pos: tuple):
        """Handle mouse click"""
        if self.game_state == 'idle':
            self._climb()
        elif self.game_state == 'safe':
            up_rect, down_rect = self._get_button_rects()
            if up_rect.collidepoint(mouse_pos):
                self._climb()
            elif down_rect.collidepoint(mouse_pos):
                self._descend()
        elif self.game_state == 'result' and self.result_timer >= 1.0:
            self.game_state = 'done'

    def _get_button_rects(self) -> tuple:
        """Get climb up and descend button rects"""
        btn_w, btn_h = 160, 50
        y = WINDOW_HEIGHT - 80
        up_rect = pygame.Rect(WINDOW_WIDTH // 2 - btn_w - 15, y, btn_w, btn_h)
        down_rect = pygame.Rect(WINDOW_WIDTH // 2 + 15, y, btn_w, btn_h)
        return up_rect, down_rect

    def _get_fall_chance(self) -> float:
        """Get current fall probability"""
        return min(1.0, LADDER_START_FALL_RATE + self.current_step * LADDER_FALL_RATE_INCREMENT)

    def _climb(self):
        """Climb one step up"""
        self.current_step += 1

        # Save money for this step
        saved = random.randint(LADDER_SAVE_MIN, LADDER_SAVE_MAX)
        self.step_saves.append(saved)
        self.accumulated += saved

        # Check if fell
        if random.random() < self._get_fall_chance():
            # Fell!
            self.fell_from = self.current_step
            self.game_state = 'falling'
            self.anim_timer = 0.0
            self.shake_intensity = 12.0
            self.accumulated = 0  # Lost everything
        else:
            # Safe!
            self.game_state = 'safe'
            self.anim_timer = 0.0

            # Celebration for big accumulated amounts
            if self.accumulated >= 500:
                self.particles.emit_confetti(
                    (self.ladder_x, self.player_y),
                    40, ['#FFD700', '#FF9800', '#FFFFFF'], lifetime=2.0
                )

    def _descend(self):
        """Descend the ladder safely, collect accumulated money"""
        self.game_state = 'result'
        self.result_timer = 0.0

        if self.accumulated > 0:
            self.wallet.add(self.accumulated)
            self.particles.emit_burst(
                (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2), 50,
                hex_to_rgb('#FFD700'),
                speed_range=(100, 300), lifetime=2.0, size=5
            )

    def update(self, dt: float):
        """Update game state"""
        self.particles.update(dt)
        self.door_glow += dt * 2
        self.shake_intensity *= (1 - dt * 6)

        if self.game_state == 'climbing':
            self.anim_timer += dt
            if self.anim_timer >= STEP_DURATION:
                self._climb()

        elif self.game_state == 'falling':
            self.anim_timer += dt
            if self.anim_timer >= STEP_DURATION:
                self.game_state = 'result'
                self.result_timer = 0.0

        elif self.game_state == 'result':
            self.result_timer += dt
            if self.result_timer >= 3.0:
                self.game_state = 'done'

    def draw(self, surface: pygame.Surface):
        """Draw the ladder game"""
        # Apply shake
        offset_x, offset_y = 0, 0
        if self.shake_intensity > 0.5:
            offset_x = random.uniform(-self.shake_intensity, self.shake_intensity)
            offset_y = random.uniform(-self.shake_intensity, self.shake_intensity)

        # Background
        self._draw_background(surface, offset_x, offset_y)

        # Ladder
        self._draw_ladder(surface)

        # Player
        player_screen_y = self._get_player_screen_y()
        self.player_y = player_screen_y
        self._draw_player(surface, self.ladder_x, player_screen_y)

        # UI
        self._draw_ui(surface)

        # Buttons
        if self.game_state == 'safe':
            self._draw_buttons(surface)
        elif self.game_state == 'idle':
            self._draw_idle_prompt(surface)

        # Result
        if self.game_state == 'result':
            self._draw_result(surface)

        self.particles.draw(surface)

    def _draw_background(self, surface: pygame.Surface, ox: float, oy: float):
        """Draw sky/height background"""
        # Height indicator: gets darker as you climb
        height_progress = min(1.0, self.current_step / MAX_STEP)

        # Sky gradient gets darker with height
        for y in range(WINDOW_HEIGHT):
            t = y / WINDOW_HEIGHT
            r = int(40 + t * 30 - height_progress * 20)
            g = int(50 + t * 20 - height_progress * 15)
            b = int(80 + t * 30 - height_progress * 25)
            pygame.draw.line(surface, (r, g, b), (0, y), (WINDOW_WIDTH, y))

        # Stars appearing as you climb higher
        if height_progress > 0.2:
            star_count = int(height_progress * 30)
            for i in range(star_count):
                sx = (i * 137 + 50) % WINDOW_WIDTH
                sy = (i * 97 + 30) % (WINDOW_HEIGHT // 2)
                twinkle = 0.5 + 0.5 * math.sin(self.door_glow * 2 + i)
                size = 1 + int(twinkle)
                alpha = int(150 + 100 * twinkle)
                star_surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
                pygame.draw.circle(star_surf, (255, 255, 255, alpha), (size, size), size)
                surface.blit(star_surf, (sx - size, sy - size))

    def _draw_ladder(self, surface: pygame.Surface):
        """Draw the ladder with visible rungs"""
        center_x = self.ladder_x
        half_w = self.ladder_width // 2
        bottom_y = WINDOW_HEIGHT - 120

        # Calculate visible rung range based on current step
        top_rung = max(0, self.current_step - VISIBLE_RUNGS + 2)
        bottom_rung = top_rung + VISIBLE_RUNGS + 2

        # Ladder rails
        rail_color = (140, 100, 50)
        pygame.draw.line(surface, rail_color, (center_x - half_w, bottom_y),
                         (center_x - half_w, 0), 8)
        pygame.draw.line(surface, rail_color, (center_x + half_w, bottom_y),
                         (center_x + half_w, 0), 8)

        # Rungs
        for i in range(top_rung, bottom_rung + 1):
            rung_y = bottom_y - i * self.rung_spacing
            if rung_y < -20 or rung_y > WINDOW_HEIGHT + 20:
                continue

            # Rung color based on whether we've passed it
            if i < self.current_step:
                color = hex_to_rgb(COLORS['gold'])
            elif i == self.current_step:
                pulse = 0.5 + 0.5 * math.sin(self.door_glow * 3)
                color = (int(255 * pulse), 200, 50)
            else:
                color = (80, 70, 50)

            pygame.draw.line(surface, color,
                           (center_x - half_w, rung_y),
                           (center_x + half_w, rung_y), 5)

            # Step number on left side
            if i > 0 and i <= MAX_STEP:
                fall_chance = min(1.0, LADDER_START_FALL_RATE + i * LADDER_FALL_RATE_INCREMENT)
                num_surf = self.font_small.render(f'{i}', True, color)
                surface.blit(num_surf, (center_x - half_w - 25, rung_y - 8))

                # Fall chance indicator
                if i > 0 and i <= self.current_step + 3:
                    chance_color = hex_to_rgb('#FF6B6B') if fall_chance > 0.3 else hex_to_rgb(COLORS['text_secondary'])
                    chance_surf = self.font_small.render(f'{int(fall_chance * 100)}%', True, chance_color)
                    surface.blit(chance_surf, (center_x + half_w + 10, rung_y - 8))

    def _get_player_screen_y(self) -> float:
        """Get player visual Y position on screen"""
        bottom_y = WINDOW_HEIGHT - 120
        if self.game_state == 'falling':
            progress = clamp(self.anim_timer / STEP_DURATION, 0, 1)
            eased = progress * progress  # Accelerate downward
            return bottom_y - self.current_step * self.rung_spacing + eased * (bottom_y + 100)
        else:
            return bottom_y - self.current_step * self.rung_spacing

    def _draw_player(self, surface: pygame.Surface, x: float, y: float):
        """Draw the player character on the ladder"""
        if self.game_state == 'idle':
            y = WINDOW_HEIGHT - 120

        size = self.player_size

        # Body
        body_color = hex_to_rgb(COLORS['red_primary'])
        if self.game_state == 'falling':
            body_color = hex_to_rgb('#FF0000')
        elif self.game_state == 'safe':
            body_color = hex_to_rgb(COLORS['success'])

        # Simple stick figure
        # Head
        pygame.draw.circle(surface, hex_to_rgb('#FFD5B0'), (x, y - size), 10)

        # Body
        pygame.draw.line(surface, body_color, (x, y - size + 10), (x, y + 5), 4)

        # Arms (grabbing the rails)
        half_w = self.ladder_width // 2
        pygame.draw.line(surface, hex_to_rgb('#FFD5B0'), (x, y - 5), (x - half_w + 5, y - 10), 3)
        pygame.draw.line(surface, hex_to_rgb('#FFD5B0'), (x, y - 5), (x + half_w - 5, y - 10), 3)

        # Legs
        pygame.draw.line(surface, hex_to_rgb('#3366CC'), (x, y + 5), (x - 12, y + 25), 3)
        pygame.draw.line(surface, hex_to_rgb('#3366CC'), (x, y + 5), (x + 12, y + 25), 3)

        # Falling spin effect
        if self.game_state == 'falling':
            spin = self.anim_timer * 10
            for i in range(3):
                angle = spin + i * 2.1
                dx = int(20 * math.cos(angle))
                dy = int(20 * math.sin(angle))
                pygame.draw.circle(surface, (255, 255, 0, 150), (x + dx, y + dy), 3)

    def _draw_ui(self, surface: pygame.Surface):
        """Draw title, accumulated money, step info"""
        # Title
        shadow = self.font_title.render('爬梯子', True, (25, 20, 10))
        surface.blit(shadow, shadow.get_rect(center=(WINDOW_WIDTH // 2 + 2, 20)))
        title_surf = self.font_title.render('爬梯子', True, hex_to_rgb(COLORS['gold']))
        surface.blit(title_surf, title_surf.get_rect(center=(WINDOW_WIDTH // 2, 30)))

        if self.current_step > 0:
            # Accumulated money
            money_text = f'已存: ¥{self.accumulated}'
            money_surf = self.font_money.render(money_text, True, hex_to_rgb(COLORS['gold']))
            surface.blit(money_surf, money_surf.get_rect(center=(WINDOW_WIDTH // 2, 70)))

            # Step info
            if self.game_state == 'safe':
                fall_chance = self._get_fall_chance()
                next_step = self.current_step + 1
                fall_text = f'下一步坠落概率: {int(fall_chance * 100)}%'
                fall_surf = self.font_small.render(fall_text, True, hex_to_rgb('#FF6B6B'))
                surface.blit(fall_surf, fall_surf.get_rect(center=(WINDOW_WIDTH // 2, 100)))

    def _draw_buttons(self, surface: pygame.Surface):
        """Draw climb up and descend buttons"""
        up_rect, down_rect = self._get_button_rects()
        mouse_pos = get_mouse_pos()
        up_hover = up_rect.collidepoint(mouse_pos)
        down_hover = down_rect.collidepoint(mouse_pos)

        # Climb up button
        up_color = hex_to_rgb(COLORS['success']) if up_hover else tuple(int(c * 0.7) for c in hex_to_rgb(COLORS['success']))
        pygame.draw.rect(surface, up_color, up_rect, border_radius=10)
        pygame.draw.rect(surface, hex_to_rgb(COLORS['gold']), up_rect, 2, border_radius=10)
        up_surf = self.font_info.render('继续爬 ▲', True, (255, 255, 255))
        surface.blit(up_surf, up_surf.get_rect(center=up_rect.center))

        # Descend button
        down_color = hex_to_rgb(COLORS['gold_dark']) if down_hover else tuple(int(c * 0.7) for c in hex_to_rgb(COLORS['gold_dark']))
        pygame.draw.rect(surface, down_color, down_rect, border_radius=10)
        pygame.draw.rect(surface, hex_to_rgb(COLORS['gold']), down_rect, 2, border_radius=10)
        down_surf = self.font_info.render('下梯子 ▼', True, (255, 255, 255))
        surface.blit(down_surf, down_surf.get_rect(center=down_rect.center))

    def _draw_idle_prompt(self, surface: pygame.Surface):
        """Draw idle prompt"""
        pulse = 0.5 + 0.5 * math.sin(self.door_glow * 2)
        alpha = int(150 + 100 * pulse)
        prompt_surf = self.font_info.render('点击开始爬梯子', True, hex_to_rgb(COLORS['text_primary']))
        prompt_surf.set_alpha(alpha)
        surface.blit(prompt_surf, prompt_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 60)))

    def _draw_result(self, surface: pygame.Surface):
        """Draw result overlay"""
        progress = clamp(self.result_timer / 0.6, 0, 1)
        eased = ease_out_quad(progress)

        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, int(180 * eased)))
        surface.blit(overlay, (0, 0))

        if self.game_state == 'result' and self.accumulated > 0:
            # Successfully descended
            win_text = f'安全下梯！+¥{self.accumulated}'
            color = hex_to_rgb(COLORS['gold'])
            result_surf = self.font_big.render(win_text, True, color)
            surface.blit(result_surf, result_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 20)))

            detail_surf = self.font_info.render(f'爬了 {self.current_step} 步', True, hex_to_rgb(COLORS['text_secondary']))
            surface.blit(detail_surf, detail_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 30)))

        elif self.game_state == 'result':
            # Fell
            fail_text = '坠落！'
            color = hex_to_rgb('#FF4444')
            result_surf = self.font_big.render(fail_text, True, color)
            surface.blit(result_surf, result_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 20)))

            detail_surf = self.font_info.render(
                f'在第 {self.fell_from} 步摔了下来，积蓄清零',
                True, hex_to_rgb(COLORS['text_secondary'])
            )
            surface.blit(detail_surf, detail_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 30)))

        if self.result_timer >= 1.0:
            back_surf = self.font_small.render('点击任意位置返回', True, hex_to_rgb(COLORS['text_secondary']))
            back_surf.set_alpha(int(150 + 100 * math.sin(self.door_glow * 4)))
            surface.blit(back_surf, back_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 50)))
