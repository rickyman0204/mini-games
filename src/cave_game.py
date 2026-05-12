"""Cave Game - Choose a cave, then coins are thrown in"""
import random
import math
import pygame
from pygame.math import Vector2

from src.settings import (
    COLORS, WINDOW_WIDTH, WINDOW_HEIGHT,
    CAVE_COUNT, CAVE_COIN_MIN, CAVE_COIN_MAX, CAVE_COIN_TYPES,
    CAVE_THROW_ANIM_DURATION, CAVE_RESULT_DURATION
)
from src.utils import hex_to_rgb


class ThrowingCoin:
    """A coin being thrown into a cave"""

    def __init__(self, coin_type: str, cave_index: int, cave_x: int, delay: float = 0.0):
        self.coin_type = coin_type
        self.coin_data = CAVE_COIN_TYPES[coin_type]
        self.cave_index = cave_index
        self.cave_x = cave_x
        self.delay = delay  # Delay before this coin starts throwing

        # Animation state
        self.is_throwing = False
        self.throw_progress = 0.0
        self.start_pos = Vector2(WINDOW_WIDTH // 2, 50)
        self.end_pos = Vector2(cave_x, 380)
        self.current_pos = Vector2(self.start_pos)
        self.has_landed = False
        self.landed_timer = 0.0

    def update(self, dt: float):
        """Update coin state"""
        if self.delay > 0:
            self.delay -= dt
            return

        if not self.is_throwing:
            self.is_throwing = True

        if self.throw_progress < 1.0:
            self.throw_progress = min(1.0, self.throw_progress + dt / CAVE_THROW_ANIM_DURATION)
            # Parabolic arc
            t = self.throw_progress
            self.current_pos.x = self.start_pos[0] + (self.end_pos[0] - self.start_pos[0]) * t
            self.current_pos.y = (self.start_pos[1] + (self.end_pos[1] - self.start_pos[1]) * t
                                 - math.sin(t * math.pi) * 100)

        if self.throw_progress >= 1.0 and not self.has_landed:
            self.has_landed = True
            self.landed_timer = 0.0

        if self.has_landed:
            self.landed_timer += dt

    def draw(self, surface: pygame.Surface):
        """Draw the coin"""
        if self.delay > 0:
            return

        color = hex_to_rgb(self.coin_data['color'])
        size = 12

        if not self.is_throwing:
            return

        if self.has_landed:
            # Draw coin at cave position with fade
            alpha = min(255, int(self.landed_timer * 400))
            coin_surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            coin_surf.set_alpha(alpha)
            pygame.draw.circle(coin_surf, color, (size, size), size)
            pygame.draw.circle(coin_surf, hex_to_rgb(COLORS['gold_dark']),
                             (size, size), size, 1)
            surface.blit(coin_surf, (self.end_pos[0] - size, self.end_pos[1] - size))
        else:
            # Draw coin in flight
            pygame.draw.circle(surface, color,
                             (int(self.current_pos[0]), int(self.current_pos[1])), size)
            pygame.draw.circle(surface, hex_to_rgb(COLORS['gold_dark']),
                             (int(self.current_pos[0]), int(self.current_pos[1])), size, 1)

            # Trail sparkles
            if self.throw_progress > 0.1 and self.throw_progress < 0.9:
                for _ in range(3):
                    spark_x = self.current_pos[0] + random.uniform(-8, 8)
                    spark_y = self.current_pos[1] + random.uniform(-8, 8)
                    spark_size = random.randint(1, 3)
                    pygame.draw.circle(surface, color,
                                     (int(spark_x), int(spark_y)), spark_size)


class Cave:
    """A single cave/mountain in the game"""

    def __init__(self, index: int, x: int, y: int):
        self.index = index
        self.x = x
        self.y = y
        self.width = 100
        self.height = 120
        self.is_selected = False
        self.coins_in_cave = []  # List of (coin_type, value) tuples
        self.total_value = 0

    def get_rect(self) -> pygame.Rect:
        """Get clickable area"""
        return pygame.Rect(self.x - self.width // 2, self.y - self.height,
                          self.width, self.height + 20)

    def handle_click(self, mouse_pos: tuple) -> bool:
        """Check if click is on this cave"""
        return self.get_rect().collidepoint(mouse_pos)

    def draw(self, surface: pygame.Surface):
        """Draw the cave/mountain"""
        # Mountain shape
        points = [
            (self.x - self.width // 2, self.y),
            (self.x - self.width // 4, self.y - self.height * 0.6),
            (self.x - self.width // 6, self.y - self.height * 0.8),
            (self.x, self.y - self.height),
            (self.x + self.width // 6, self.y - self.height * 0.8),
            (self.x + self.width // 4, self.y - self.height * 0.6),
            (self.x + self.width // 2, self.y),
        ]
        pygame.draw.polygon(surface, (100, 80, 60), points)
        pygame.draw.polygon(surface, (80, 60, 40), points, width=2)

        # Cave opening (dark circle at base)
        cave_opening = pygame.Rect(self.x - 20, self.y - 35, 40, 30)
        pygame.draw.ellipse(surface, (20, 15, 10), cave_opening)
        pygame.draw.ellipse(surface, (0, 0, 0), cave_opening.inflate(-4, -4))

        # Selection glow
        if self.is_selected:
            glow_surf = pygame.Surface((self.width + 20, self.height + 40), pygame.SRCALPHA)
            pygame.draw.polygon(glow_surf, (255, 215, 0, 80),
                              [(p[0] - self.x + self.width // 2 + 10, p[1] - self.y + self.height + 20)
                               for p in points])
            surface.blit(glow_surf, (self.x - self.width // 2 - 10, self.y - self.height - 20))

        # Cave number
        font = pygame.font.SysFont('microsoftyahei', 16, bold=True)
        num_surf = font.render(f'{self.index + 1}', True, (255, 255, 255))
        num_rect = num_surf.get_rect(center=(self.x, self.y - self.height // 2))
        surface.blit(num_surf, num_rect)


class CaveGame:
    """The cave game - choose a cave, coins are thrown in"""

    def __init__(self, wallet):
        self.wallet = wallet
        self.caves = []
        self.selected_cave_index = -1
        self.game_state = 'choosing'  # 'choosing' -> 'throwing' -> 'result' -> 'done'
        self.coins = []
        self.result_text = ''
        self.result_color = COLORS['gold']
        self.result_timer = 0.0
        self.total_won = 0
        self.throw_timer = 0.0

    def reset(self):
        """Start new game"""
        self.game_state = 'choosing'
        self.selected_cave_index = -1
        self.coins = []
        self.result_text = ''
        self.total_won = 0
        self.result_timer = 0.0
        self.throw_timer = 0.0
        self.actual_coin_count = random.randint(CAVE_COIN_MIN, CAVE_COIN_MAX)

        # Create 4 caves evenly spaced
        total_width = CAVE_COUNT * 100
        start_x = (WINDOW_WIDTH - total_width) // 2 + 50
        cave_y = 420
        self.caves = []
        for i in range(CAVE_COUNT):
            x = start_x + i * 100
            cave = Cave(i, x, cave_y)
            self.caves.append(cave)

    def handle_click(self, mouse_pos: tuple) -> bool:
        """Handle cave selection"""
        if self.game_state != 'choosing':
            return False

        for cave in self.caves:
            if cave.handle_click(mouse_pos):
                self.selected_cave_index = cave.index
                cave.is_selected = True
                self._start_throwing()
                return True
        return False

    def _get_random_coin_type(self) -> str:
        """Get random coin type based on probabilities"""
        roll = random.random()
        cumulative = 0.0
        for coin_type, coin_data in CAVE_COIN_TYPES.items():
            cumulative += coin_data['probability']
            if roll <= cumulative:
                return coin_type
        return 'copper'

    def _start_throwing(self):
        """Generate and start throwing coins"""
        self.game_state = 'throwing'
        self.coins = []

        # Generate random number of coins
        for i in range(self.actual_coin_count):
            coin_type = self._get_random_coin_type()
            cave_index = random.randint(0, CAVE_COUNT - 1)
            cave = self.caves[cave_index]
            coin = ThrowingCoin(coin_type, cave_index, cave.x, delay=i * 0.4)
            self.coins.append(coin)

    def update(self, dt: float):
        """Update game state"""
        for coin in self.coins:
            coin.update(dt)

        if self.game_state == 'throwing':
            # Check if all coins have landed
            all_landed = all(c.delay <= 0 and c.has_landed for c in self.coins)
            if all_landed:
                self.game_state = 'result'
                self.result_timer = 0.0
                self._calculate_result()

        if self.game_state == 'result':
            self.result_timer += dt
            if self.result_timer >= CAVE_RESULT_DURATION:
                self.game_state = 'done'

        if self.game_state == 'done':
            self.result_timer += dt

    def _calculate_result(self):
        """Calculate winnings from coins in selected cave"""
        self.total_won = 0
        self.coins_in_cave = []

        for coin in self.coins:
            if coin.cave_index == self.selected_cave_index:
                self.coins_in_cave.append(coin.coin_data)
                self.total_won += coin.coin_data['value']

        if self.total_won > 0:
            self.result_text = f'获得 ¥{self.total_won}！'
            self.result_color = COLORS['gold']
            self.wallet.add(self.total_won)
        else:
            self.result_text = '空无一物！'
            self.result_color = COLORS['text_secondary']

    def draw(self, surface: pygame.Surface):
        """Draw the cave game"""
        self._draw_ground(surface)
        self._draw_caves(surface)
        self._draw_coins(surface)
        self._draw_result(surface)

    def _draw_ground(self, surface: pygame.Surface):
        """Draw layered ground"""
        ground_y = 420
        for y in range(ground_y, WINDOW_HEIGHT):
            ratio = (y - ground_y) / (WINDOW_HEIGHT - ground_y)
            r = int(55 + ratio * 20)
            g = int(40 + ratio * 15)
            b = int(25 + ratio * 10)
            pygame.draw.line(surface, (r, g, b), (0, y), (WINDOW_WIDTH, y))

        pygame.draw.line(surface, (80, 120, 40), (0, ground_y), (WINDOW_WIDTH, ground_y), 2)

        for x in range(0, WINDOW_WIDTH, 10):
            gh = random.randint(4, 10)
            pygame.draw.line(surface, (100, 150, 50),
                           (x, ground_y), (x, ground_y - gh), 2)

    def _draw_caves(self, surface: pygame.Surface):
        """Draw all caves"""
        for cave in self.caves:
            cave.draw(surface)

    def _draw_coins(self, surface: pygame.Surface):
        """Draw all coins"""
        for coin in self.coins:
            coin.draw(surface)

    def _draw_result(self, surface: pygame.Surface):
        """Draw result text"""
        if self.game_state in ('result', 'done') and self.result_text:
            font = pygame.font.SysFont('microsoftyahei', 32, bold=True)
            result_surf = font.render(self.result_text, True, hex_to_rgb(self.result_color))
            rect = result_surf.get_rect(center=(WINDOW_WIDTH // 2, 100))
            surface.blit(result_surf, rect)

            # Show coin breakdown
            if self.coins_in_cave:
                font_small = pygame.font.SysFont('microsoftyahei', 16)
                for i, coin_data in enumerate(self.coins_in_cave):
                    coin_text = f'{coin_data["name"]} +¥{coin_data["value"]}'
                    text_surf = font_small.render(coin_text, True, hex_to_rgb(coin_data['color']))
                    text_rect = text_surf.get_rect(center=(WINDOW_WIDTH // 2, 140 + i * 25))
                    surface.blit(text_surf, text_rect)

    def _draw_hud(self, surface: pygame.Surface):
        """Draw HUD with shadow effects"""
        font = pygame.font.SysFont('microsoftyahei', 36, bold=True)
        shadow_s = font.render('躲 藏 山 洞', True, (30, 25, 10))
        surface.blit(shadow_s, shadow_s.get_rect(center=(WINDOW_WIDTH // 2 + 2, 37)))
        title_surf = font.render('躲 藏 山 洞', True, hex_to_rgb(COLORS['gold']))
        title_rect = title_surf.get_rect(center=(WINDOW_WIDTH // 2, 35))
        surface.blit(title_surf, title_rect)

        if self.game_state == 'choosing':
            font_hint = pygame.font.SysFont('microsoftyahei', 18)
            hint_surf = font_hint.render('点击选择一个山洞', True, hex_to_rgb(COLORS['text_secondary']))
            hint_rect = hint_surf.get_rect(center=(WINDOW_WIDTH // 2, 75))
            surface.blit(hint_surf, hint_rect)

            # Show how many coins will be thrown
            coin_count_surf = font_hint.render(f'本次投掷: {self.actual_coin_count} 枚硬币',
                                               True, hex_to_rgb(COLORS['gold']))
            coin_count_rect = coin_count_surf.get_rect(center=(WINDOW_WIDTH // 2, 100))
            surface.blit(coin_count_surf, coin_count_rect)
