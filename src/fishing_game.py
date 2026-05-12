"""Fishing game - cast line and mash to catch fish"""
import math
import random
import pygame

from src.settings import (
    WINDOW_WIDTH, WINDOW_HEIGHT, COLORS,
    FISHING_ENTRY_COST, FISHING_CASTS_PER_ENTRY,
    FISH_TYPES, FISHING_RESULT_DURATION
)
from src.utils import clamp, ease_out_quad, hex_to_rgb
from src.particles import ParticleEmitter


# Mash time range (seconds)
MASH_MIN_TIME = 4.0
MASH_MAX_TIME = 7.0
INTRO_DURATION = 0.5  # Brief intro before mashing starts


class FishingGame:
    """Fishing mini-game with mash-to-catch mechanic"""

    def __init__(self, wallet):
        self.wallet = wallet
        self.particles = ParticleEmitter()

        # Game state: 'idle', 'waiting', 'intro', 'mashing', 'success', 'fail', 'result', 'done'
        self.game_state = 'idle'
        self.casts_left = 0
        self.catch_time = 0.0
        self.wait_timer = 0.0
        self.result_timer = 0.0

        # Catch mechanics
        self.caught_fish_key = None
        self.caught_fish = None
        self.won_amount = 0
        self.mash_count = 0
        self.mash_target = 0
        self.catch_timer = 0.0
        self.catch_progress = 0.0

        # Visual elements
        self.bobber_y = 0.0
        self.bobber_target_y = 0.0
        self.bobber_shake = 0.0
        self.water_offset = 0.0
        self.bite_flash = 0.0
        self.result_y = WINDOW_HEIGHT + 200
        self.shake_intensity = 0.0

        # Fonts
        self.font_title = pygame.font.SysFont('microsoftyahei', 36, bold=True)
        self.font_big = pygame.font.SysFont('microsoftyahei', 60, bold=True)
        self.font_info = pygame.font.SysFont('microsoftyahei', 20)
        self.font_small = pygame.font.SysFont('microsoftyahei', 16)
        self.font_mash = pygame.font.SysFont('microsoftyahei', 28, bold=True)

    def reset(self):
        """Reset game state"""
        self.game_state = 'idle'
        self.casts_left = 0
        self.catch_time = 0.0
        self.wait_timer = 0.0
        self.result_timer = 0.0
        self.caught_fish_key = None
        self.caught_fish = None
        self.won_amount = 0
        self.mash_count = 0
        self.mash_target = 0
        self.catch_timer = 0.0
        self.catch_duration = 0.0
        self.catch_progress = 0.0
        self.bobber_y = 0.0
        self.bobber_shake = 0.0
        self.bite_flash = 0.0
        self.result_y = WINDOW_HEIGHT + 200
        self.shake_intensity = 0.0
        self.particles.clear()

    def handle_click(self, mouse_pos: tuple):
        """Handle mouse click"""
        self._handle_mash()
        if self.game_state == 'idle':
            self._cast_line()
        elif self.game_state == 'result' and self.result_timer >= 1.0:
            self.game_state = 'done'

    def handle_key(self, key):
        """Handle key press (space to mash)"""
        if key == pygame.K_SPACE:
            if self.game_state == 'idle':
                self._cast_line()
            elif self.game_state == 'result' and self.result_timer >= 1.0:
                self.game_state = 'done'
            else:
                self._handle_mash()

    def _handle_mash(self):
        """Handle mash input during catching phase"""
        if self.game_state == 'mashing':
            self.mash_count += 1
            self.catch_progress = self.mash_count / self.mash_target
            self.shake_intensity = 5.0

            if self.mash_count >= self.mash_target:
                self._catch_success()

    def _cast_line(self):
        """Cast fishing line (uses one cast)"""
        if self.casts_left <= 0:
            return

        self.casts_left -= 1

        # Pre-determine fish so wait time matches difficulty
        self.caught_fish_key, self.caught_fish = self._determine_catch()
        catch_min = self.caught_fish.get('catch_min', 3)
        catch_max = self.caught_fish.get('catch_max', 8)

        self.game_state = 'waiting'
        self.wait_timer = 0.0
        self.catch_time = random.uniform(catch_min, catch_max)
        self.bobber_target_y = WINDOW_HEIGHT // 2 + 40
        self.bobber_y = WINDOW_HEIGHT // 2 - 60
        self.bobber_shake = 0.0
        self.bite_flash = 0.0
        self.shake_intensity = 0.0

    def _determine_catch(self) -> tuple:
        """Determine what fish is on the line"""
        roll = random.random()
        cumulative = 0.0
        for fish_key, fish_data in FISH_TYPES.items():
            cumulative += fish_data['probability']
            if roll <= cumulative:
                return fish_key, fish_data
        return list(FISH_TYPES.items())[-1]

    def _start_bite(self):
        """Start the bite/mashing phase"""
        # Fish already determined in _cast_line, now randomize mash difficulty
        mash_min = self.caught_fish.get('mash_min', 5)
        mash_max = self.caught_fish.get('mash_max', 10)
        self.mash_target = random.randint(mash_min, mash_max)
        self.mash_count = 0
        self.catch_progress = 0.0
        self.catch_timer = 0.0
        self.catch_duration = random.uniform(MASH_MIN_TIME, MASH_MAX_TIME)
        self.bobber_shake = 0.0

        # Brief intro showing the fish, then mashing starts
        self.game_state = 'intro'

    def _catch_success(self):
        """Player successfully caught the fish"""
        self.won_amount = self.caught_fish['value']
        if self.won_amount > 0:
            self.wallet.add(self.won_amount)

        self.game_state = 'success'
        self.result_timer = 0.0
        self.result_y = WINDOW_HEIGHT + 200

        if self.won_amount >= 500:
            self.particles.emit_confetti(
                (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2),
                80, ['#FFD700', '#FF9800', '#FFFFFF'], lifetime=3.0
            )
        elif self.won_amount >= 100:
            self.particles.emit_burst(
                (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2), 40,
                hex_to_rgb(self.caught_fish['color']),
                speed_range=(100, 300), lifetime=2.0, size=5
            )

    def _catch_fail(self):
        """Fish escaped"""
        self.won_amount = 0
        self.game_state = 'fail'
        self.result_timer = 0.0
        self.result_y = WINDOW_HEIGHT + 200

    def update(self, dt: float):
        """Update game state"""
        self.particles.update(dt)
        self.water_offset += dt * 2
        self.bite_flash += dt * 8
        self.shake_intensity *= (1 - dt * 8)

        if self.game_state == 'waiting':
            self.wait_timer += dt
            self.bobber_y += (self.bobber_target_y - self.bobber_y) * dt * 2
            if self.wait_timer >= self.catch_time:
                self._start_bite()

        elif self.game_state == 'intro':
            self.catch_timer += dt
            if self.catch_timer >= INTRO_DURATION:
                self.catch_timer = 0.0
                self.game_state = 'mashing'

        elif self.game_state == 'mashing':
            self.catch_timer += dt
            self.bobber_shake += dt * 20
            if self.catch_timer >= self.catch_duration:
                self._catch_fail()

        elif self.game_state in ('success', 'fail'):
            self.result_timer += dt
            self.result_y += (WINDOW_HEIGHT // 2 - self.result_y) * dt * 4
            if self.result_timer >= FISHING_RESULT_DURATION:
                self.game_state = 'done'

    def draw(self, surface: pygame.Surface):
        """Draw the fishing game"""
        # Apply screen shake during mashing
        offset_x = 0
        offset_y = 0
        if self.shake_intensity > 0.5:
            offset_x = random.uniform(-self.shake_intensity, self.shake_intensity)
            offset_y = random.uniform(-self.shake_intensity, self.shake_intensity)

        self._draw_sky(surface)
        self._draw_water(surface)
        self._draw_rod(surface)

        if self.game_state in ('waiting', 'intro', 'mashing'):
            self._draw_bobber(surface)

        if self.game_state == 'waiting':
            self._draw_wait_prompt(surface)

        if self.game_state == 'intro':
            self._draw_fish_intro(surface)

        if self.game_state == 'mashing':
            self._draw_mash_ui(surface)

        if self.game_state == 'idle':
            self._draw_idle_prompt(surface)

        if self.game_state in ('success', 'fail'):
            self._draw_result(surface)

        # Title
        title_surf = self.font_title.render('钓鱼', True, hex_to_rgb(COLORS['gold']))
        surface.blit(title_surf, title_surf.get_rect(center=(WINDOW_WIDTH // 2, 30)))

        # Cost info
        cost_surf = self.font_small.render(
            f'入场: ¥{FISHING_ENTRY_COST}',
            True, hex_to_rgb(COLORS['text_secondary'])
        )
        surface.blit(cost_surf, cost_surf.get_rect(center=(WINDOW_WIDTH // 2, 65)))

        self.particles.draw(surface)

    def _draw_wait_prompt(self, surface: pygame.Surface):
        remaining = max(0, self.catch_time - self.wait_timer)
        timer_surf = self.font_info.render(
            f'等待中... {remaining:.0f}秒',
            True, hex_to_rgb(COLORS['text_secondary'])
        )
        surface.blit(timer_surf, timer_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 80)))

    def _draw_fish_intro(self, surface: pygame.Surface):
        """Brief flash showing what fish is on the line"""
        pulse = 0.5 + 0.5 * math.sin(self.catch_timer * 15)
        alpha = int(200 + 55 * pulse)

        if self.caught_fish is None:
            return

        text_surf = self.font_big.render(
            self.caught_fish['name'], True, hex_to_rgb(self.caught_fish['color'])
        )
        text_surf.set_alpha(alpha)
        surface.blit(text_surf, text_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 100)))

        sub_surf = self.font_info.render('快按空格/点击!', True, hex_to_rgb('#FF4444'))
        sub_surf.set_alpha(alpha)
        surface.blit(sub_surf, sub_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 40)))

    def _draw_mash_ui(self, surface: pygame.Surface):
        """Draw mash progress bar and countdown"""
        fish_name = self.caught_fish['name'] if self.caught_fish else ''
        fish_color = hex_to_rgb(self.caught_fish['color']) if self.caught_fish else '#FFF'

        # Fish name
        name_surf = self.font_info.render(fish_name, True, fish_color)
        surface.blit(name_surf, name_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 110)))

        # Timer
        remaining = max(0, self.catch_duration - self.catch_timer)
        timer_surf = self.font_mash.render(f'{remaining:.1f}s', True, hex_to_rgb('#FF6B6B'))
        surface.blit(timer_surf, timer_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 80)))

        # Progress bar background
        bar_width = 400
        bar_height = 30
        bar_x = (WINDOW_WIDTH - bar_width) // 2
        bar_y = WINDOW_HEIGHT // 2 - 40

        pygame.draw.rect(surface, (40, 40, 40), (bar_x, bar_y, bar_width, bar_height), border_radius=6)
        pygame.draw.rect(surface, hex_to_rgb(COLORS['gold']), (bar_x, bar_y, bar_width, bar_height), 2, border_radius=6)

        # Progress fill
        progress = clamp(self.catch_progress, 0, 1)
        fill_width = int(bar_width * progress)
        if fill_width > 0:
            fill_surf = pygame.Surface((fill_width, bar_height - 4), pygame.SRCALPHA)
            fill_color = hex_to_rgb(self.caught_fish['color']) if self.caught_fish else hex_to_rgb(COLORS['gold'])
            for x in range(fill_width):
                alpha = int(200 * (1 - x / fill_width * 0.3))
                fill_surf.set_at((x, 0), (*fill_color, alpha))
                for y in range(1, bar_height - 4):
                    fill_surf.set_at((x, y), (*fill_color, alpha))
            pygame.draw.rect(surface, fill_color, (bar_x + 2, bar_y + 2, fill_width, bar_height - 4), border_radius=4)

        # Press count
        count_surf = self.font_mash.render(f'{self.mash_count} / {self.mash_target}', True, hex_to_rgb(COLORS['text_primary']))
        surface.blit(count_surf, count_surf.get_rect(center=(WINDOW_WIDTH // 2, bar_y + bar_height + 25)))

        # Prompt
        prompt_surf = self.font_small.render('狂按空格 / 狂点鼠标!', True, hex_to_rgb('#FF6B6B'))
        surface.blit(prompt_surf, prompt_surf.get_rect(center=(WINDOW_WIDTH // 2, bar_y + bar_height + 55)))

    def _draw_result(self, surface: pygame.Surface):
        """Draw catch result"""
        if self.result_timer < 0.2:
            return

        progress = clamp(self.result_timer / 0.8, 0, 1)
        eased = ease_out_quad(progress)

        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, int(180 * eased)))
        surface.blit(overlay, (0, 0))

        if self.caught_fish is None:
            return

        if self.game_state == 'success':
            fish_name = self.caught_fish['name']
            text_color = hex_to_rgb(self.caught_fish['color'])
            emoji = self.caught_fish.get('emoji', '')

            name_font = pygame.font.SysFont('microsoftyahei', int(60 * eased), bold=True)
            emoji_text = f'{emoji} {fish_name}' if emoji else fish_name
            name_surf = name_font.render(emoji_text, True, text_color)
            surface.blit(name_surf, name_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 30)))

            if self.won_amount > 0:
                value_surf = self.font_info.render(f'+¥{self.won_amount}', True, hex_to_rgb(COLORS['gold']))
                surface.blit(value_surf, value_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 30)))

        elif self.game_state == 'fail':
            fail_surf = self.font_big.render('鱼跑了!', True, hex_to_rgb('#FF4444'))
            surface.blit(fail_surf, fail_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 20)))

            escape_surf = self.font_info.render(f'{self.caught_fish["name"]} 挣脱了...', True, hex_to_rgb(COLORS['text_secondary']))
            surface.blit(escape_surf, escape_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 30)))

        if self.result_timer >= 1.0:
            back_surf = self.font_small.render('点击任意位置返回', True, hex_to_rgb(COLORS['text_secondary']))
            back_surf.set_alpha(int(150 + 100 * math.sin(self.water_offset * 4)))
            surface.blit(back_surf, back_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 70)))

    def _draw_sky(self, surface: pygame.Surface):
        sky_top = hex_to_rgb('#87CEEB')
        sky_bottom = hex_to_rgb('#B0E0E6')
        for y in range(WINDOW_HEIGHT // 2):
            progress = y / (WINDOW_HEIGHT // 2)
            r = int(sky_top[0] + (sky_bottom[0] - sky_top[0]) * progress)
            g = int(sky_top[1] + (sky_bottom[1] - sky_top[1]) * progress)
            b = int(sky_top[2] + (sky_bottom[2] - sky_top[2]) * progress)
            pygame.draw.line(surface, (r, g, b), (0, y), (WINDOW_WIDTH, y))

        sun_x, sun_y = WINDOW_WIDTH - 80, 70
        for r in range(40, 0, -2):
            alpha = int(30 * (1 - r / 40))
            glow = pygame.Surface((80, 80), pygame.SRCALPHA)
            pygame.draw.circle(glow, (255, 255, 200, alpha), (40, 40), r)
            surface.blit(glow, (sun_x - 40, sun_y - 40), special_flags=pygame.BLEND_RGBA_ADD)
        pygame.draw.circle(surface, '#FFD700', (sun_x, sun_y), 25)

        self._draw_cloud(surface, 100, 50, 0.3)
        self._draw_cloud(surface, 400, 80, 0.5)
        self._draw_cloud(surface, 600, 40, 0.2)

    def _draw_cloud(self, surface: pygame.Surface, x: int, y: int, speed: float):
        offset = (self.water_offset * speed * 20) % (WINDOW_WIDTH + 200) - 100
        cx = (x + offset) % (WINDOW_WIDTH + 200) - 100
        cloud_surf = pygame.Surface((80, 30), pygame.SRCALPHA)
        pygame.draw.ellipse(cloud_surf, (255, 255, 255, 180), (0, 0, 80, 30))
        pygame.draw.ellipse(cloud_surf, (255, 255, 255, 180), (20, -10, 40, 30))
        pygame.draw.ellipse(cloud_surf, (255, 255, 255, 180), (-10, 5, 30, 25))
        surface.blit(cloud_surf, (cx, y))

    def _draw_water(self, surface: pygame.Surface):
        water_y = WINDOW_HEIGHT // 2
        for y in range(water_y, WINDOW_HEIGHT):
            progress = (y - water_y) / (WINDOW_HEIGHT - water_y)
            r = int(20 + progress * 10)
            g = int(60 + progress * 20 + 10 * math.sin(self.water_offset + y * 0.05))
            b = int(120 + progress * 30 + 15 * math.sin(self.water_offset * 1.3 + y * 0.03))
            pygame.draw.line(surface, (r, g, b), (0, y), (WINDOW_WIDTH, y))

        for x in range(WINDOW_WIDTH):
            wave_y = water_y + int(3 * math.sin(self.water_offset * 3 + x * 0.05))
            pygame.draw.line(surface, (100, 180, 255, 100), (x, wave_y), (x, wave_y + 2), 2)

    def _draw_rod(self, surface: pygame.Surface):
        rod_start = (WINDOW_WIDTH // 2 + 50, 100)
        rod_end = (WINDOW_WIDTH // 2 + 150, 160)
        rod_tip = (WINDOW_WIDTH // 2 + 180, 170)

        # Rod bends more during mashing
        bend = self.shake_intensity * 0.5
        rod_tip_actual = (WINDOW_WIDTH // 2 + 180, 170 + bend)

        pygame.draw.line(surface, '#8B4513', rod_start, rod_end, 8)
        pygame.draw.line(surface, '#666666', rod_end, rod_tip_actual, 4)

        if self.game_state in ('waiting', 'intro', 'mashing'):
            pygame.draw.line(surface, (200, 200, 200), rod_tip_actual, (WINDOW_WIDTH // 2 + 180, self.bobber_y), 1)

    def _draw_bobber(self, surface: pygame.Surface):
        x = WINDOW_WIDTH // 2 + 180
        y = self.bobber_y

        if self.game_state in ('intro', 'mashing'):
            shake_x = int(5 * math.sin(self.bobber_shake * 30))
            x += shake_x

        pygame.draw.circle(surface, '#FF0000', (x, y - 6), 8)
        pygame.draw.circle(surface, '#FFFFFF', (x, y + 6), 8)

        if self.game_state == 'mashing':
            blink = 0.5 + 0.5 * math.sin(self.bite_flash * 10)
            glow_surf = pygame.Surface((40, 40), pygame.SRCALPHA)
            for r in range(20, 0, -2):
                alpha = int(blink * 40 * (1 - r / 20))
                pygame.draw.circle(glow_surf, (255, 100, 100, alpha), (20, 20), r)
            surface.blit(glow_surf, (x - 20, y - 20), special_flags=pygame.BLEND_RGBA_ADD)

    def _draw_idle_prompt(self, surface: pygame.Surface):
        pulse = 0.5 + 0.5 * math.sin(self.water_offset * 3)
        alpha = int(150 + 100 * pulse)

        prompt_surf = self.font_info.render(
            '点击或按空格下竿',
            True, hex_to_rgb(COLORS['text_primary'])
        )
        prompt_surf.set_alpha(alpha)
        surface.blit(prompt_surf, prompt_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 40)))
