"""Money Tree cultivation - fulfill the tree's demands to earn rewards"""
import math
import random
import pygame

from src.settings import (
    WINDOW_WIDTH, WINDOW_HEIGHT, COLORS,
    TREE_SHAKE_COST, PRIZES, SCRATCH_TICKET_COST
)
from src.utils import clamp, ease_out_quad, hex_to_rgb, get_mouse_pos
from src.particles import ParticleEmitter


# Demand interval in seconds (gameplay-friendly: 10-30s)
DEMAND_MIN_TIME = 10
DEMAND_MAX_TIME = 30

# Quick-catalyze demand (instant trigger button) - random cost ¥15~105
QUICK_DEMAND_MIN = 15
QUICK_DEMAND_MAX = 105

# Reward probabilities
REWARD_NOTHING = 0.20    # 20% chance: nothing
REWARD_SCRATCH = 0.50    # 50% chance: free scratch card
REWARD_MONEY = 0.30      # 30% chance: ¥50-200

# Cultivation actions
ACTIONS = [
    {'key': 'fertilize', 'name': '施肥', 'cost': 50, 'color': '#8B4513', 'icon': '💩'},
    {'key': 'water', 'name': '浇水', 'cost': 25, 'color': '#2196F3', 'icon': '💧'},
    {'key': 'sunlight', 'name': '晒太阳', 'cost': 10, 'color': '#FFD700', 'icon': '☀️'},
]


class MoneyTree:
    """Money tree that makes demands and rewards cultivation"""

    def __init__(self, wallet):
        self.wallet = wallet
        self.particles = ParticleEmitter()

        # Game state: 'idle', 'demand', 'reward', 'done'
        self.game_state = 'idle'

        # Demand system
        self.demand_timer = 0.0
        self.demand_interval = 0.0  # Time until next demand
        self.current_demand = None  # Which action the tree wants
        self.demand_fulfilled = False

        # Reward
        self.reward_type = None     # 'nothing', 'scratch', 'money'
        self.reward_amount = 0
        self.reward_message = ''
        self.reward_timer = 0.0
        self.won_free_scratch = False  # Set to True when scratch reward won

        # Tree visual
        self.tree_angle = 0.0       # Sway angle
        self.tree_sway_speed = 0.0
        self.leaf_health = 0.5      # 0 = dead, 1 = lush
        self.tree_height = 1.0      # Visual growth
        self.water_offset = 0.0
        self.particle_emitted = False

        # Fonts
        self.font_title = pygame.font.SysFont('microsoftyahei', 36, bold=True)
        self.font_big = pygame.font.SysFont('microsoftyahei', 48, bold=True)
        self.font_info = pygame.font.SysFont('microsoftyahei', 20)
        self.font_small = pygame.font.SysFont('microsoftyahei', 16)
        self.font_action = pygame.font.SysFont('microsoftyahei', 22, bold=True)

        # Tree position
        self.tree_x = WINDOW_WIDTH // 2
        self.tree_base_y = 420

        # Quick demand button
        self.quick_btn_rect = pygame.Rect(0, 0, 0, 0)
        self.exit_btn_rect = pygame.Rect(0, 0, 0, 0)

    def reset(self):
        """Reset game state"""
        self.game_state = 'idle'
        self.demand_timer = 0.0
        self.demand_interval = random.uniform(DEMAND_MIN_TIME, DEMAND_MAX_TIME)
        self.current_demand = None
        self.demand_fulfilled = False
        self.reward_type = None
        self.reward_amount = 0
        self.reward_message = ''
        self.reward_timer = 0.0
        self.won_free_scratch = False
        self.tree_angle = 0.0
        self.tree_sway_speed = 1.0 + random.random()
        self.leaf_health = 0.5
        self.tree_height = 1.0
        self.water_offset = 0.0
        self.particle_emitted = False
        self.particles.clear()

    def _get_quick_demand_cost(self) -> int:
        """Get a random quick demand cost"""
        return random.randint(QUICK_DEMAND_MIN, QUICK_DEMAND_MAX)

    def handle_click(self, mouse_pos: tuple):
        """Handle mouse click"""
        # Exit button - available in all states
        if self.exit_btn_rect.collidepoint(mouse_pos):
            self.game_state = 'done'
            return

        if self.game_state == 'idle':
            # Check quick-catalyze button
            if self.quick_btn_rect.collidepoint(mouse_pos):
                cost = self._get_quick_demand_cost()
                if self.wallet.can_afford(cost):
                    self.wallet.spend(cost)
                    self._generate_demand()
            # Check action buttons even during idle (they work anytime)
            for action in ACTIONS:
                rect = self._get_action_rect(action)
                if rect.collidepoint(mouse_pos):
                    self._fulfill_demand(action['key'])
                    return
        elif self.game_state == 'demand':
            # Check if clicked an action button
            for action in ACTIONS:
                rect = self._get_action_rect(action)
                if rect.collidepoint(mouse_pos):
                    self._fulfill_demand(action['key'])
                    return
        elif self.game_state == 'reward' and self.reward_timer >= 2.0:
            self.game_state = 'done'
        elif self.game_state == 'done':
            pass  # Will return to menu via main.py

    def _get_action_rect(self, action: dict) -> pygame.Rect:
        """Get clickable rect for an action button"""
        idx = ACTIONS.index(action)
        btn_w, btn_h = 150, 60
        spacing = 20
        total_w = btn_w * 3 + spacing * 2
        start_x = (WINDOW_WIDTH - total_w) // 2
        x = start_x + idx * (btn_w + spacing)
        y = WINDOW_HEIGHT - 100
        return pygame.Rect(x, y, btn_w, btn_h)

    def _generate_demand(self):
        """Generate a new demand from the tree"""
        action = random.choice(ACTIONS)
        self.current_demand = action['key']
        self.demand_fulfilled = False
        self.game_state = 'demand'

        # Shake tree to get attention
        self.tree_angle = 10.0

    def _fulfill_demand(self, action_key: str):
        """Player clicked an action to fulfill the demand"""
        action = next(a for a in ACTIONS if a['key'] == action_key)

        if not self.wallet.can_afford(action['cost']):
            return

        self.wallet.spend(action['cost'])

        # Increase tree health/height
        self.leaf_health = min(1.0, self.leaf_health + 0.2)
        self.tree_height = min(1.5, self.tree_height + 0.05)

        if action_key == self.current_demand:
            # Correct action! Generate reward
            self._generate_reward()
            self.current_demand = None
        else:
            # Wrong action - tree shakes, no reward
            self.tree_angle = 15.0
            self.reward_message = '树不满意...'
            self.reward_type = 'wrong'
            self.reward_timer = 0.0
            self.game_state = 'reward'

            # Schedule next demand sooner
            self.demand_timer = 0.0
            self.demand_interval = random.uniform(30, 60)

    def _generate_reward(self):
        """Generate reward after fulfilling demand correctly"""
        roll = random.random()

        if roll < REWARD_NOTHING:
            self.reward_type = 'nothing'
            self.reward_message = '树什么都没给...'
            self.reward_amount = 0
        elif roll < REWARD_NOTHING + REWARD_SCRATCH:
            self.reward_type = 'scratch'
            self.reward_message = '获得免费刮刮乐！'
            self.reward_amount = 0
            self.won_free_scratch = True
        else:
            self.reward_type = 'money'
            self.reward_amount = random.randint(50, 200)
            self.reward_message = f'获得 ¥{self.reward_amount}！'
            self.wallet.add(self.reward_amount)

        self.game_state = 'reward'
        self.reward_timer = 0.0

        # Celebration for money or scratch rewards
        if self.reward_type in ('money', 'scratch'):
            self.particles.emit_confetti(
                (self.tree_x, self.tree_base_y - 100),
                60, ['#FFD700', '#228B22', '#FFFFFF'], lifetime=3.0
            )

        # Schedule next demand
        self.demand_timer = 0.0
        self.demand_interval = random.uniform(DEMAND_MIN_TIME, DEMAND_MAX_TIME)

    def update(self, dt: float):
        """Update game state"""
        self.particles.update(dt)
        self.water_offset += dt * 2

        # Tree gentle sway
        self.tree_sway_speed += dt * 0.01
        self.tree_angle = math.sin(self.water_offset * self.tree_sway_speed) * 3.0

        # Tree shake decay
        if abs(self.tree_angle) > 3.0:
            self.tree_angle *= (1 - dt * 4)

        # Demand timer (speeded up for gameplay: divide by 10 so 30-50s instead of 300-500s)
        # Actually keep the real times as specified
        if self.game_state in ('idle', 'demand'):
            self.demand_timer += dt

            if self.demand_timer >= self.demand_interval:
                self._generate_demand()

        elif self.game_state == 'reward':
            self.reward_timer += dt
            if self.reward_timer >= 5.0:
                self.game_state = 'done'

    def draw(self, surface: pygame.Surface):
        """Draw the money tree game"""
        # Background - earthy green
        self._draw_background(surface)

        # Tree
        self._draw_tree(surface)

        # Demand UI
        if self.game_state == 'demand':
            self._draw_demand_ui(surface)
        elif self.game_state == 'idle':
            self._draw_idle_ui(surface)
        elif self.game_state == 'reward':
            self._draw_reward_ui(surface)

        self.particles.draw(surface)

    def _draw_background(self, surface: pygame.Surface):
        """Draw sky and ground background"""
        # Sky gradient
        sky_top = hex_to_rgb('#87CEEB')
        sky_bottom = hex_to_rgb('#B0E0E6')
        for y in range(self.tree_base_y):
            progress = y / self.tree_base_y
            r = int(sky_top[0] + (sky_bottom[0] - sky_top[0]) * progress)
            g = int(sky_top[1] + (sky_bottom[1] - sky_top[1]) * progress)
            b = int(sky_top[2] + (sky_bottom[2] - sky_top[2]) * progress)
            pygame.draw.line(surface, (r, g, b), (0, y), (WINDOW_WIDTH, y))

        # Ground
        ground_y = self.tree_base_y
        for y in range(ground_y, WINDOW_HEIGHT):
            progress = (y - ground_y) / (WINDOW_HEIGHT - ground_y)
            r = int(50 + progress * 20)
            g = int(100 + progress * 30)
            b = int(30 + progress * 15)
            pygame.draw.line(surface, (r, g, b), (0, y), (WINDOW_WIDTH, y))

        # Grass tufts
        for x in range(0, WINDOW_WIDTH, 40):
            grass_h = 10 + int(5 * math.sin(self.water_offset + x * 0.1))
            pygame.draw.line(surface, (34, 139, 34), (x, ground_y), (x, ground_y - grass_h), 2)

    def _draw_tree(self, surface: pygame.Surface):
        """Draw the money tree with refined details"""
        cx = self.tree_x
        base_y = self.tree_base_y

        green_val = int(80 + self.leaf_health * 80)
        leaf_color = (25, green_val, 18)
        light_color = (48, green_val + 38, 38)
        trunk_color = (95, 65, 35)
        trunk_light = (125, 90, 50)

        trunk_height = int(120 * self.tree_height)
        trunk_width = int(20 * self.tree_height)
        trunk_top = base_y - trunk_height

        pygame.draw.rect(surface, trunk_color,
                        (cx - trunk_width // 2, trunk_top, trunk_width, trunk_height),
                        border_radius=5)
        hw = max(3, trunk_width // 3)
        pygame.draw.rect(surface, trunk_light,
                        (cx - hw, trunk_top + 4, hw * 2, trunk_height - 8),
                        border_radius=3)

        for side in [-1, 1]:
            root_end_x = cx + side * 35
            root_end_y = base_y + 12
            pygame.draw.line(surface, trunk_color,
                           (cx, base_y), (root_end_x, root_end_y), 5)
            pygame.draw.line(surface, trunk_light,
                           (cx + side * 3, base_y), (root_end_x - side * 3, root_end_y - 3), 2)

        canopy_layers = [
            (int(140 * self.tree_height), trunk_top + int(30 * self.tree_height), 0.8),
            (int(160 * self.tree_height), trunk_top + int(10 * self.tree_height), 1.0),
            (int(120 * self.tree_height), trunk_top - int(10 * self.tree_height), 1.1),
        ]

        for width, y, depth in canopy_layers:
            ox = self.tree_angle * depth
            c_rect = pygame.Rect(cx - width // 2 + ox, y, width, int(80 * self.tree_height))
            pygame.draw.ellipse(surface, leaf_color, c_rect)
            h_rect = pygame.Rect(cx - width // 4 + ox, y + 10,
                                width // 2, int(30 * self.tree_height))
            pygame.draw.ellipse(surface, light_color, h_rect)

        if self.leaf_health > 0.3:
            coin_count = int(self.leaf_health * 5)
            for i in range(coin_count):
                angle = i * 2.4 + self.water_offset * 0.3
                coin_x = cx + int(50 * self.tree_height * math.sin(angle))
                coin_y = trunk_top + int(40 * self.tree_height) + int(20 * abs(math.cos(angle)))
                coin_r = int(6 + self.leaf_health * 3)
                ax = int(coin_x + self.tree_angle)
                ay = int(coin_y)
                pygame.draw.circle(surface, hex_to_rgb(COLORS['gold_dark']), (ax, ay + 1), coin_r + 1)
                pygame.draw.circle(surface, hex_to_rgb(COLORS['gold']), (ax, ay), coin_r)
                pygame.draw.circle(surface, hex_to_rgb('#FFF3B0'), (ax - 1, ay - 2), max(2, coin_r // 3))

        shadow_t = self.font_title.render('摇钱树培养', True, (25, 20, 10))
        surface.blit(shadow_t, shadow_t.get_rect(center=(cx + 2, 37)))
        title_surf = self.font_title.render('摇钱树培养', True, hex_to_rgb(COLORS['gold']))
        surface.blit(title_surf, title_surf.get_rect(center=(cx, 35)))

    def _draw_idle_ui(self, surface: pygame.Surface):
        """Draw idle state UI - waiting for demand"""
        # Exit button
        self._draw_exit_button(surface)

        # Draw action buttons (enabled - can always try)
        self._draw_action_buttons(surface, disabled=False)

        # Quick-catalyze button
        btn_w, btn_h = 140, 40
        btn_x = WINDOW_WIDTH // 2
        btn_y = self.tree_base_y + 30
        self.quick_btn_rect = pygame.Rect(btn_x - btn_w // 2, btn_y, btn_w, btn_h)

        mouse_pos = get_mouse_pos()
        can_afford = self.wallet.can_afford(QUICK_DEMAND_MIN)
        is_hover = self.quick_btn_rect.collidepoint(mouse_pos)

        if is_hover and can_afford:
            bg_color = hex_to_rgb(COLORS['gold'])
        else:
            bg_color = hex_to_rgb(COLORS['gold_dark'])

        pygame.draw.rect(surface, bg_color, self.quick_btn_rect, border_radius=8)
        pygame.draw.rect(surface, hex_to_rgb(COLORS['gold']), self.quick_btn_rect, 2, border_radius=8)

        quick_surf = self.font_small.render(f' 速催需求 (¥{QUICK_DEMAND_MIN}~{QUICK_DEMAND_MAX})', True,
                                            hex_to_rgb(COLORS['bg_primary']))
        surface.blit(quick_surf, quick_surf.get_rect(center=(btn_x, btn_y + btn_h // 2)))

        # Progress bar showing time until next demand
        progress = clamp(self.demand_timer / self.demand_interval, 0, 1)
        bar_w = 200
        bar_h = 10
        bar_x = (WINDOW_WIDTH - bar_w) // 2
        bar_y = btn_y + btn_h + 15

        pygame.draw.rect(surface, (40, 40, 40), (bar_x, bar_y, bar_w, bar_h), border_radius=5)

        fill_w = int(bar_w * progress)
        if fill_w > 0:
            if progress < 0.7:
                color = hex_to_rgb(COLORS['success'])
            elif progress < 0.9:
                color = hex_to_rgb('#FFA500')
            else:
                color = hex_to_rgb('#FF4444')
            pygame.draw.rect(surface, color, (bar_x + 2, bar_y + 2, fill_w - 4, bar_h - 4), border_radius=4)

        remaining = max(0, int(self.demand_interval - self.demand_timer))
        time_surf = self.font_small.render(f'等待中... {remaining}秒', True, hex_to_rgb(COLORS['text_secondary']))
        surface.blit(time_surf, time_surf.get_rect(center=(WINDOW_WIDTH // 2, bar_y + bar_h + 15)))

    def _draw_demand_ui(self, surface: pygame.Surface):
        """Draw demand state UI - tree wants something"""
        # Exit button
        self._draw_exit_button(surface)

        # Draw action buttons (enabled)
        self._draw_action_buttons(surface, disabled=False)

        # Demand text
        if self.current_demand:
            action = next(a for a in ACTIONS if a['key'] == self.current_demand)
            demand_text = f'树想要: {action["icon"]} {action["name"]} (¥{action["cost"]})'
            demand_surf = self.font_info.render(demand_text, True, hex_to_rgb(action['color']))
            surface.blit(demand_surf, demand_surf.get_rect(center=(WINDOW_WIDTH // 2, self.tree_base_y + 30)))

            # Pulse the tree
            pulse = 0.5 + 0.5 * math.sin(self.water_offset * 4)
            attention_surf = self.font_small.render('👆 点击满足需求', True, hex_to_rgb(COLORS['text_primary']))
            attention_surf.set_alpha(int(150 + 100 * pulse))
            surface.blit(attention_surf, attention_surf.get_rect(center=(WINDOW_WIDTH // 2, self.tree_base_y + 55)))

    def _draw_reward_ui(self, surface: pygame.Surface):
        """Draw reward overlay"""
        if self.reward_timer < 0.2:
            return

        progress = clamp(self.reward_timer / 0.6, 0, 1)
        eased = ease_out_quad(progress)

        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, int(180 * eased)))
        surface.blit(overlay, (0, 0))

        # Reward text
        if self.reward_type == 'nothing':
            text_color = hex_to_rgb(COLORS['text_secondary'])
        elif self.reward_type == 'scratch':
            text_color = hex_to_rgb(COLORS['gold'])
        elif self.reward_type == 'money':
            text_color = hex_to_rgb(COLORS['gold'])
        elif self.reward_type == 'wrong':
            text_color = hex_to_rgb('#FF6B6B')

        reward_surf = self.font_big.render(self.reward_message, True, text_color)
        surface.blit(reward_surf, reward_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 20)))

        if self.reward_timer >= 2.0:
            back_surf = self.font_small.render('点击任意位置返回', True, hex_to_rgb(COLORS['text_secondary']))
            back_surf.set_alpha(int(150 + 100 * math.sin(self.water_offset * 4)))
            surface.blit(back_surf, back_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 50)))

    def _draw_exit_button(self, surface: pygame.Surface):
        """Draw exit button (top-left corner)"""
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

    def _draw_action_buttons(self, surface: pygame.Surface, disabled: bool = False):
        """Draw cultivation action buttons"""
        mouse_pos = get_mouse_pos()

        for action in ACTIONS:
            rect = self._get_action_rect(action)
            is_hover = rect.collidepoint(mouse_pos) and not disabled

            if disabled:
                bg_color = tuple(int(c * 0.4) for c in hex_to_rgb(action['color']))
            elif is_hover:
                bg_color = hex_to_rgb(action['color'])
            else:
                bg_color = tuple(int(c * 0.7) for c in hex_to_rgb(action['color']))

            pygame.draw.rect(surface, bg_color, rect, border_radius=10)
            border = hex_to_rgb(COLORS['gold']) if not disabled else hex_to_rgb(COLORS['gold_dark'])
            pygame.draw.rect(surface, border, rect, 2, border_radius=10)

            # Action name and cost
            name_surf = self.font_action.render(f'{action["icon"]} {action["name"]}', True, (255, 255, 255))
            surface.blit(name_surf, name_surf.get_rect(center=(rect.centerx, rect.centery - 8)))

            cost_surf = self.font_small.render(f'¥{action["cost"]}', True, hex_to_rgb(COLORS['gold']))
            surface.blit(cost_surf, cost_surf.get_rect(center=(rect.centerx, rect.centery + 16)))
