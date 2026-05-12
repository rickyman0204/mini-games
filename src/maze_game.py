"""Maze exploration game - choose left or right at each junction"""
import math
import random
import pygame

from src.settings import (
    WINDOW_WIDTH, WINDOW_HEIGHT, COLORS,
    MAZE_ENTRY_COST, MAZE_CHOICES, MAZE_ROOMS, MAZE_PRIZES,
    MAZE_CHOICE_DURATION, MAZE_RESULT_DURATION
)
from src.utils import get_mouse_pos, clamp, ease_out_quad, ease_in_out_quad, hex_to_rgb
from src.particles import ParticleEmitter


# Tunnel styles for each step
TUNNEL_STYLES = [
    {  # Step 1: Stone arch corridor
        'wall_color': (70, 65, 55),
        'floor_color': (50, 45, 40),
        'ceiling_color': (80, 75, 65),
        'accent_color': (160, 140, 110),
        'pillar_color': (100, 90, 75),
        'name': '石门走廊',
    },
    {  # Step 2: Crystal tunnel
        'wall_color': (35, 50, 60),
        'floor_color': (25, 40, 50),
        'ceiling_color': (45, 60, 70),
        'accent_color': (100, 200, 220),
        'pillar_color': (60, 130, 150),
        'name': '水晶通道',
    },
    {  # Step 3: Gold vein tunnel
        'wall_color': (55, 45, 30),
        'floor_color': (40, 35, 25),
        'ceiling_color': (65, 55, 35),
        'accent_color': (220, 180, 50),
        'pillar_color': (140, 110, 40),
        'name': '金矿密道',
    },
]

# Ore/room final display
ORE_VISUALS = {
    'diamond': {'color': '#00BFFF', 'crystal_shape': 'diamond'},
    'gold_ore': {'color': '#FFD700', 'crystal_shape': 'nugget'},
    'iron_ore': {'color': '#808080', 'crystal_shape': 'rock'},
    'empty': {'color': '#555555', 'crystal_shape': 'none'},
}


def generate_maze_prizes() -> list:
    """Generate a list of 8 prizes (1 diamond, 2 gold, 3 iron, 2 empty), shuffled"""
    prizes = []
    for prize_key, prize_data in MAZE_PRIZES.items():
        prizes.extend([prize_key] * prize_data['count'])
    random.shuffle(prizes)
    return prizes


class MazeGame:
    """Manages the maze exploration game"""

    def __init__(self, wallet):
        self.wallet = wallet
        self.particles = ParticleEmitter()

        # Game state
        self.game_state = 'choosing'  # 'choosing', 'transition', 'result', 'done'
        self.current_choice = 0
        self.path_taken = []
        self.final_prize = None
        self.final_prize_key = None
        self.result_timer = 0.0
        self.won_amount = 0

        # Transition animation
        self.transition_timer = 0.0
        self.chosen_direction = None

        # Corridor animation
        self.door_glow = 0.0
        self.crystal_angle = 0.0  # Rotation for final ore display

        # Fonts
        self.font_title = pygame.font.SysFont('microsoftyahei', 36, bold=True)
        self.font_result = pygame.font.SysFont('microsoftyahei', 40, bold=True)
        self.font_info = pygame.font.SysFont('microsoftyahei', 20)
        self.font_choice = pygame.font.SysFont('microsoftyahei', 28, bold=True)

    def reset(self):
        """Reset game state"""
        self.game_state = 'choosing'
        self.current_choice = 0
        self.path_taken = []
        self.final_prize = None
        self.final_prize_key = None
        self.result_timer = 0.0
        self.won_amount = 0
        self.transition_timer = 0.0
        self.chosen_direction = None
        self.crystal_angle = 0.0
        self.particles.clear()

    def _determine_prize(self) -> tuple:
        """Determine the final prize based on the path taken"""
        prizes = generate_maze_prizes()
        index = 0
        for p in self.path_taken:
            index = index * 2 + (1 if p == 'right' else 0)
        prize_key = prizes[index]
        prize_data = MAZE_PRIZES[prize_key]
        return prize_key, prize_data

    def handle_click(self, mouse_pos: tuple):
        """Handle mouse click"""
        if self.game_state == 'choosing':
            left_rect, right_rect = self._get_door_rects()
            if left_rect.collidepoint(mouse_pos):
                self._make_choice('left')
            elif right_rect.collidepoint(mouse_pos):
                self._make_choice('right')

    def _get_door_rects(self) -> tuple:
        """Get left and right button clickable areas"""
        btn_width = 200
        btn_height = 80
        y = WINDOW_HEIGHT - 160
        left_rect = pygame.Rect(WINDOW_WIDTH // 2 - btn_width - 20, y, btn_width, btn_height)
        right_rect = pygame.Rect(WINDOW_WIDTH // 2 + 20, y, btn_width, btn_height)
        return left_rect, right_rect

    def _make_choice(self, direction: str):
        """Make a choice (left or right)"""
        self.path_taken.append(direction)
        self.chosen_direction = direction
        self.game_state = 'transition'
        self.transition_timer = 0.0

        if self.current_choice >= MAZE_CHOICES - 1:
            # Last choice, determine prize
            self.final_prize_key, self.final_prize = self._determine_prize()
            self.won_amount = self.final_prize['value']
            if self.won_amount > 0:
                self.wallet.add(self.won_amount)

    def update(self, dt: float):
        """Update game state"""
        self.particles.update(dt)
        self.door_glow += dt * 2
        self.crystal_angle += dt * 30  # Rotate crystal slowly

        if self.game_state == 'transition':
            self.transition_timer += dt
            progress = self.transition_timer / MAZE_CHOICE_DURATION

            if progress >= 1.0:
                self.current_choice += 1
                if self.current_choice >= MAZE_CHOICES:
                    # Show result
                    self.game_state = 'result'
                    self.result_timer = 0.0

                    # Celebration for big wins
                    if self.won_amount >= 500:
                        self.particles.emit_confetti(
                            (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2),
                            80, ['#00BFFF', '#FFD700', '#FFFFFF'], lifetime=3.0
                        )
                    elif self.won_amount >= 100:
                        self.particles.emit_burst(
                            (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2), 40,
                            hex_to_rgb(self.final_prize['color']),
                            speed_range=(100, 300), lifetime=2.0, size=5
                        )
                else:
                    # Next choice
                    self.game_state = 'choosing'
                    self.transition_timer = 0.0

        elif self.game_state == 'result':
            self.result_timer += dt

            # Auto-return to menu after showing result
            if self.result_timer >= MAZE_RESULT_DURATION:
                self.game_state = 'done'

    def draw(self, surface: pygame.Surface):
        """Draw the maze game"""
        # Title
        shadow = self.font_title.render('迷宫探险', True, (25, 20, 10))
        surface.blit(shadow, shadow.get_rect(center=(WINDOW_WIDTH // 2 + 2, 20)))
        title_surf = self.font_title.render('迷宫探险', True, hex_to_rgb(COLORS['gold']))
        title_rect = title_surf.get_rect(center=(WINDOW_WIDTH // 2, 35))
        surface.blit(title_surf, title_rect)

        # Progress dots
        self._draw_progress(surface)

        if self.game_state == 'choosing':
            self._draw_junction(surface)
        elif self.game_state == 'transition':
            self._draw_corridor(surface)
            self._draw_transition(surface)
        elif self.game_state == 'result':
            self._draw_corridor(surface)
            self._draw_result(surface)

        self.particles.draw(surface)

    def _draw_progress(self, surface: pygame.Surface):
        """Draw progress dots showing how far through the maze"""
        y = 75
        dot_spacing = 40
        start_x = WINDOW_WIDTH // 2 - dot_spacing

        for i in range(MAZE_CHOICES):
            x = start_x + i * dot_spacing
            if i < len(self.path_taken):
                style = TUNNEL_STYLES[i]
                color = style['accent_color']
            else:
                color = hex_to_rgb(COLORS['text_secondary'])
            pygame.draw.circle(surface, color, (x, y), 6)

        if self.current_choice < MAZE_CHOICES:
            style = TUNNEL_STYLES[self.current_choice]
            step_text = f'{style["name"]} - 第 {self.current_choice + 1}/{MAZE_CHOICES} 次选择'
            step_surf = self.font_info.render(step_text, True, hex_to_rgb(COLORS['text_secondary']))
            step_rect = step_surf.get_rect(center=(WINDOW_WIDTH // 2, y))
            surface.blit(step_surf, step_rect)

    def _draw_junction(self, surface: pygame.Surface):
        """Draw a junction with left/right choice buttons"""
        center_x = WINDOW_WIDTH // 2
        self._draw_corridor(surface)

        left_rect, right_rect = self._get_door_rects()
        glow = 0.5 + 0.5 * math.sin(self.door_glow)

        self._draw_choice_button(surface, left_rect, '◄ 左', hex_to_rgb('#2196F3'), glow)
        self._draw_choice_button(surface, right_rect, '右 ►', hex_to_rgb('#FF5722'), glow)

        pulse = 0.5 + 0.5 * math.sin(self.door_glow * 1.5)
        prompt_surf = self.font_info.render('选择左或右', True, hex_to_rgb(COLORS['text_primary']))
        prompt_surf.set_alpha(int(150 + 105 * pulse))
        surface.blit(prompt_surf, prompt_surf.get_rect(center=(center_x, WINDOW_HEIGHT - 200)))

    def _draw_choice_button(self, surface: pygame.Surface, rect: pygame.Rect, label: str,
                            color: tuple, glow_amount: float):
        """Draw a large choice button with label"""
        mouse_pos = get_mouse_pos()
        is_hover = rect.collidepoint(mouse_pos)

        btn_color = color if is_hover else tuple(int(c * 0.7) for c in color)
        pygame.draw.rect(surface, btn_color, rect, border_radius=12)

        border_color = hex_to_rgb(COLORS['gold']) if is_hover else hex_to_rgb(COLORS['gold_dark'])
        pygame.draw.rect(surface, border_color, rect, width=3, border_radius=12)

        if is_hover and glow_amount > 0.3:
            glow_surf = pygame.Surface(rect.inflate(30, 30).size, pygame.SRCALPHA)
            for r in range(50, 0, -2):
                alpha = int(glow_amount * 30 * (1 - r / 50))
                pygame.draw.ellipse(glow_surf, (*color, alpha), (0, 0, rect.inflate(30, 30).width, rect.inflate(30, 30).height))
            surface.blit(glow_surf, rect.move(-15, -15), special_flags=pygame.BLEND_RGBA_ADD)

        label_surf = self.font_choice.render(label, True, (255, 255, 255))
        surface.blit(label_surf, label_surf.get_rect(center=rect.center))

    def _draw_corridor(self, surface: pygame.Surface):
        """Draw the corridor with distinct style per step"""
        style = TUNNEL_STYLES[self.current_choice] if self.current_choice < 3 else TUNNEL_STYLES[-1]

        # Base fill
        surface.fill(style['wall_color'])

        # Ceiling gradient
        for y in range(0, WINDOW_HEIGHT // 3):
            progress = y / (WINDOW_HEIGHT // 3)
            r = int(style['ceiling_color'][0] * (1 - progress * 0.3))
            g = int(style['ceiling_color'][1] * (1 - progress * 0.3))
            b = int(style['ceiling_color'][2] * (1 - progress * 0.3))
            pygame.draw.line(surface, (r, g, b), (0, y), (WINDOW_WIDTH, y))

        # Floor gradient
        floor_y = WINDOW_HEIGHT // 2 + 50
        for y in range(floor_y, WINDOW_HEIGHT):
            progress = (y - floor_y) / (WINDOW_HEIGHT - floor_y)
            r = int(style['floor_color'][0] * (1 - progress * 0.2))
            g = int(style['floor_color'][1] * (1 - progress * 0.2))
            b = int(style['floor_color'][2] * (1 - progress * 0.2))
            pygame.draw.line(surface, (r, g, b), (0, y), (WINDOW_WIDTH, y))

        # Tunnel walls - perspective lines converging to center
        center_x = WINDOW_WIDTH // 2
        vanish_y = WINDOW_HEIGHT // 3

        for i in range(8):
            t = i / 7.0
            wall_left_x = int(30 + t * (center_x - 30))
            wall_right_x = int(WINDOW_WIDTH - 30 - t * (WINDOW_WIDTH - 30 - center_x))
            top_y = int(vanish_y + t * (WINDOW_HEIGHT // 2 - vanish_y))
            bottom_y = int(floor_y + t * (WINDOW_HEIGHT - floor_y))

            alpha_val = int(200 * (1 - t * 0.5))
            accent = tuple(int(c * (1 - t * 0.3)) for c in style['accent_color'])
            pygame.draw.line(surface, accent, (wall_left_x, top_y), (wall_left_x, bottom_y), 2)
            pygame.draw.line(surface, accent, (wall_right_x, top_y), (wall_right_x, bottom_y), 2)

        # Horizontal arch beams
        for i in range(6):
            t = i / 5.0
            beam_y = int(vanish_y + t * (floor_y - vanish_y))
            wall_left_x = int(30 + t * (center_x - 30))
            wall_right_x = int(WINDOW_WIDTH - 30 - t * (WINDOW_WIDTH - 30 - center_x))

            pygame.draw.line(surface, style['pillar_color'],
                           (wall_left_x, beam_y), (wall_right_x, beam_y), 3)

        # Step-specific decorations
        if self.current_choice == 0:
            self._draw_stone_corridor(surface, vanish_y, center_x, floor_y)
        elif self.current_choice == 1:
            self._draw_crystal_corridor(surface, vanish_y, center_x, floor_y)
        elif self.current_choice == 2:
            self._draw_gold_corridor(surface, vanish_y, center_x, floor_y)

        # Torch lights
        self._draw_torches(surface)

    def _draw_stone_corridor(self, surface: pygame.Surface, vanish_y: int, center_x: int, floor_y: int):
        """Step 1: Stone arch with brick pattern"""
        # Stone arch at top
        arch_points = []
        for angle in range(180, 0, -5):
            rad = math.radians(angle)
            x = center_x + int(200 * math.cos(rad))
            y = vanish_y + int(40 * math.sin(rad))
            arch_points.append((x, y))
        if arch_points:
            pygame.draw.polygon(surface, (90, 85, 70), arch_points)
            pygame.draw.polygon(surface, (120, 110, 90), arch_points, 3)

        # Brick pattern on walls
        for x in range(0, center_x - 200, 40):
            for y in range(vanish_y + 50, floor_y, 30):
                rect = pygame.Rect(x, y, 35, 25)
                pygame.draw.rect(surface, (80, 75, 65), rect, 1)
            mirror_x = WINDOW_WIDTH - x - 40
            for y in range(vanish_y + 50, floor_y, 30):
                rect = pygame.Rect(mirror_x, y, 35, 25)
                pygame.draw.rect(surface, (80, 75, 65), rect, 1)

    def _draw_crystal_corridor(self, surface: pygame.Surface, vanish_y: int, center_x: int, floor_y: int):
        """Step 2: Crystal formations on walls"""
        # Crystal clusters on left and right walls
        crystal_colors = [(100, 200, 220), (80, 180, 200), (120, 220, 240)]

        for side in [-1, 1]:
            base_x = center_x + side * 250
            for i in range(4):
                cy = vanish_y + 60 + i * 70
                crystal_color = crystal_colors[i % len(crystal_colors)]
                glow = 0.5 + 0.5 * math.sin(self.door_glow * 2 + i)

                # Draw crystal as diamond shape
                cx = base_x + side * int(30 * math.sin(self.door_glow + i * 0.5))
                size = 15 + int(5 * glow)
                points = [
                    (cx, cy - size),
                    (cx + size // 2, cy),
                    (cx, cy + size),
                    (cx - size // 2, cy),
                ]
                pygame.draw.polygon(surface, crystal_color, points)
                pygame.draw.polygon(surface, tuple(min(255, c + 50) for c in crystal_color), points, 2)

        # Shimmering particles floating
        for i in range(6):
            px = 100 + i * 120 + int(20 * math.sin(self.door_glow + i))
            py = vanish_y + 80 + int(40 * math.cos(self.door_glow * 0.7 + i * 1.2))
            size = 2 + int(2 * math.sin(self.door_glow * 3 + i))
            pygame.draw.circle(surface, (150, 230, 255, 100), (px, py), size)

    def _draw_gold_corridor(self, surface: pygame.Surface, vanish_y: int, center_x: int, floor_y: int):
        """Step 3: Gold veins running through walls"""
        # Gold veins as wavy lines on walls
        for side in [-1, 1]:
            base_x = center_x + side * 200
            points = []
            for y in range(vanish_y + 40, floor_y, 5):
                t = (y - vanish_y - 40) / (floor_y - vanish_y - 40)
                x = base_x + int(20 * math.sin(y * 0.05 + self.door_glow * 0.5))
                color_val = int(180 + 40 * math.sin(t * math.pi + self.door_glow))
                points.append((x, y, color_val))

            for i in range(len(points) - 1):
                color_val = points[i][2]
                gold = (color_val, color_val - 40, 30)
                pygame.draw.line(surface, gold, (points[i][0], points[i][1]),
                               (points[i + 1][0], points[i + 1][1]), 3)

        # Gold nuggets embedded in walls
        for i in range(5):
            x = 120 + i * 150
            y = vanish_y + 80 + int(50 * math.sin(i * 2.1))
            size = 8 + int(3 * math.sin(self.door_glow + i))
            pygame.draw.circle(surface, (200, 170, 40), (x, y), size)
            pygame.draw.circle(surface, (240, 210, 80), (x - 2, y - 2), max(1, size - 3))

    def _draw_torches(self, surface: pygame.Surface):
        """Draw torch lights on walls"""
        for tx in [120, WINDOW_WIDTH - 120]:
            flicker = 0.5 + 0.5 * math.sin(self.door_glow * 5 + tx * 0.01)
            torch_y = 160

            # Glow
            glow_size = int(50 + 20 * flicker)
            glow_surf = pygame.Surface((glow_size * 2, glow_size * 2), pygame.SRCALPHA)
            for r in range(glow_size, 0, -2):
                alpha = int(20 * (1 - r / glow_size))
                pygame.draw.circle(glow_surf, (255, 180, 80, alpha), (glow_size, glow_size), r)
            surface.blit(glow_surf, (tx - glow_size, torch_y - glow_size),
                        special_flags=pygame.BLEND_RGBA_ADD)

            # Torch body
            pygame.draw.rect(surface, (100, 70, 40), (tx - 4, torch_y, 8, 25), border_radius=2)
            # Flame
            flame_height = int(12 + 6 * flicker)
            pygame.draw.ellipse(surface, (255, 200, 50),
                              (tx - 6, torch_y - flame_height, 12, flame_height))

    def _draw_transition(self, surface: pygame.Surface):
        """Draw transition animation between choices"""
        progress = clamp(self.transition_timer / MAZE_CHOICE_DURATION, 0, 1)
        eased = ease_in_out_quad(progress)

        if progress < 0.5:
            alpha = int(eased * 2 * 200)
        else:
            alpha = int((1 - (eased - 0.5) * 2) * 200)

        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, alpha))
        surface.blit(overlay, (0, 0))

        if progress < 0.5:
            dir_text = '向左' if self.chosen_direction == 'left' else '向右'
            dir_surf = self.font_choice.render(dir_text, True, hex_to_rgb(COLORS['gold']))
            dir_surf.set_alpha(int(255 * (1 - progress * 2)))
            surface.blit(dir_surf, dir_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2)))

    def _draw_result(self, surface: pygame.Surface):
        """Draw final result with ore visual"""
        progress = clamp(self.result_timer / 0.5, 0, 1)
        eased = ease_out_quad(progress)

        # Darken background
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, int(eased * 180)))
        surface.blit(overlay, (0, 0))

        if progress > 0.1:
            ore_scale = min(1.0, (progress - 0.1) * 2)

            # Draw ore visual
            ore_center = (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 60)
            ore_size = int(80 * ore_scale)
            self._draw_ore_visual(surface, ore_center, ore_size)

            # Prize name
            if progress > 0.2:
                name_scale = min(1.0, (progress - 0.2) * 2.5)
                name_size = int(100 * name_scale)
                name_font = pygame.font.SysFont('microsoftyahei', name_size, bold=True)

                color = hex_to_rgb(self.final_prize['color'])
                prize_name = self.final_prize['name']

                name_surf = name_font.render(prize_name, True, color)
                surface.blit(name_surf, name_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 20)))

            # Value
            if self.won_amount > 0:
                value_text = f'+¥{self.won_amount}'
                value_color = COLORS['gold']
            else:
                value_text = '一无所获...'
                value_color = COLORS['text_secondary']

            value_surf = self.font_info.render(value_text, True, hex_to_rgb(value_color))
            surface.blit(value_surf, value_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 70)))

            # Timer countdown hint
            time_left = max(0, MAZE_RESULT_DURATION - self.result_timer)
            back_surf = self.font_info.render(f'{time_left:.0f}秒后返回菜单...', True, hex_to_rgb(COLORS['text_secondary']))
            back_surf.set_alpha(180)
            surface.blit(back_surf, back_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 80)))

    def _draw_ore_visual(self, surface: pygame.Surface, center: tuple, size: int):
        """Draw visual representation of the final ore/prize"""
        if self.final_prize_key is None:
            return

        visual = ORE_VISUALS.get(self.final_prize_key, ORE_VISUALS['empty'])
        shape = visual['crystal_shape']
        color = hex_to_rgb(visual['color'])

        glow = 0.5 + 0.5 * math.sin(self.door_glow * 3)

        if shape == 'diamond':
            # Diamond - faceted crystal shape
            points = [
                (center[0], center[1] - size),
                (center[0] + size // 2, center[1] - size // 4),
                (center[0] + size // 3, center[1] + size // 2),
                (center[0] - size // 3, center[1] + size // 2),
                (center[0] - size // 2, center[1] - size // 4),
            ]
            pygame.draw.polygon(surface, color, points)

            # Inner facets
            for i in range(3):
                facet_pts = [
                    center,
                    (points[i][0], points[i][1]),
                    (points[(i + 1) % 5][0], points[(i + 1) % 5][1]),
                ]
                facet_color = tuple(max(0, min(255, c + 40 * (i + 1))) for c in color)
                pygame.draw.polygon(surface, facet_color, facet_pts, 2)

            # Sparkle
            sparkle_r = int(60 + 20 * glow)
            sparkle_surf = pygame.Surface((sparkle_r * 2, sparkle_r * 2), pygame.SRCALPHA)
            for r in range(sparkle_r, 0, -2):
                alpha = int(15 * (1 - r / sparkle_r))
                pygame.draw.circle(sparkle_surf, (150, 220, 255, alpha), (sparkle_r, sparkle_r), r)
            surface.blit(sparkle_surf, (center[0] - sparkle_r, center[1] - sparkle_r),
                        special_flags=pygame.BLEND_RGBA_ADD)

        elif shape == 'nugget':
            # Gold ore - rough lump shape
            pygame.draw.ellipse(surface, color,
                              (center[0] - size, center[1] - size * 3 // 4, size * 2, size * 3 // 2))

            # Gold highlights
            pygame.draw.ellipse(surface, (255, 230, 100),
                              (center[0] - size // 2, center[1] - size // 2, size // 2, size // 3))

            # Rock matrix (dark veins)
            for angle in range(0, 360, 45):
                rad = math.radians(angle)
                x1 = center[0] + int(size * 0.3 * math.cos(rad))
                y1 = center[1] + int(size * 0.3 * math.sin(rad))
                x2 = center[0] + int(size * 0.8 * math.cos(rad))
                y2 = center[1] + int(size * 0.6 * math.sin(rad))
                pygame.draw.line(surface, (120, 100, 30), (x1, y1), (x2, y2), 3)

            # Glow
            glow_r = int(80 + 20 * glow)
            glow_surf = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
            for r in range(glow_r, 0, -2):
                alpha = int(12 * (1 - r / glow_r))
                pygame.draw.circle(glow_surf, (255, 200, 50, alpha), (glow_r, glow_r), r)
            surface.blit(glow_surf, (center[0] - glow_r, center[1] - glow_r),
                        special_flags=pygame.BLEND_RGBA_ADD)

        elif shape == 'rock':
            # Iron ore - rough angular rock
            rock_pts = [
                (center[0] - size * 3 // 4, center[1] - size // 3),
                (center[0] - size // 4, center[1] - size * 2 // 3),
                (center[0] + size // 2, center[1] - size // 2),
                (center[0] + size * 3 // 4, center[1] - size // 6),
                (center[0] + size // 2, center[1] + size // 2),
                (center[0] - size // 4, center[1] + size * 3 // 4),
                (center[0] - size * 2 // 3, center[1] + size // 3),
            ]
            pygame.draw.polygon(surface, color, rock_pts)

            # Iron highlights (dark metallic sheen)
            highlight_pts = [
                (center[0] - size // 4, center[1] - size // 4),
                (center[0], center[1] - size // 3),
                (center[0] + size // 4, center[1] - size // 6),
                (center[0] + size // 4, center[1]),
                (center[0], center[1] + size // 6),
                (center[0] - size // 4, center[1]),
            ]
            pygame.draw.polygon(surface, (140, 140, 140), highlight_pts, 2)

            # Metallic sparkles
            for i in range(3):
                sx = center[0] + int(size * 0.4 * math.cos(self.crystal_angle * 0.02 + i * 2))
                sy = center[1] + int(size * 0.3 * math.sin(self.crystal_angle * 0.02 + i * 2))
                pygame.draw.circle(surface, (180, 180, 180), (sx, sy), 2)

        elif shape == 'none':
            # Empty room - cracked wall / rubble
            rubble_color = (80, 75, 70)
            for i in range(5):
                rx = center[0] - size + i * size // 2 + int(10 * math.sin(i * 1.7))
                ry = center[1] + size // 3 + int(8 * math.cos(i * 2.3))
                rw = 20 + i * 5
                rh = 12 + i * 3
                pygame.draw.rect(surface, rubble_color, (rx, ry, rw, rh), border_radius=3)
                pygame.draw.rect(surface, (60, 55, 50), (rx, ry, rw, rh), 1, border_radius=3)

            # Cracked wall lines
            for i in range(4):
                x1 = center[0] - size + i * size // 2
                y1 = center[1] - size // 2
                x2 = x1 + int(15 * math.sin(i * 1.5))
                y2 = y1 + size
                pygame.draw.line(surface, (70, 65, 60), (x1, y1), (x2, y2), 2)

            # Empty symbol
            empty_surf = self.font_info.render('(空)', True, (100, 95, 90))
            surface.blit(empty_surf, empty_surf.get_rect(center=center))
