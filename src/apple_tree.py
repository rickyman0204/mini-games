"""Apple Tree - shake to catch falling items"""
import math
import random
import pygame

from src.settings import (
    WINDOW_WIDTH, WINDOW_HEIGHT, COLORS,
    TREE_SHAKE_COST, MAX_SHAKES,
    TREE_SHAKE_ANIM_DURATION, TREE_DROP_FALL_DURATION,
    TREE_DROPS
)
from src.utils import clamp, ease_out_quad, hex_to_rgb
from src.particles import ParticleEmitter


class AppleTree:
    """Shake the apple tree, catch falling items"""

    def __init__(self, wallet):
        self.wallet = wallet
        self.particles = ParticleEmitter()

        # Game state: 'idle', 'shaking', 'dropping', 'catching', 'result', 'done'
        self.game_state = 'idle'

        # Shake tracking
        self.shakes_left = MAX_SHAKES
        self.shake_anim = 0.0
        self.shake_intensity = 0.0
        self.accumulated = 0

        # Drop
        self.current_drop = None
        self.drop_x = 0
        self.drop_y = 0
        self.drop_vy = 0
        self.drop_gravity = 0
        self.drop_anim = 0.0
        self.drop_caught = False

        # Result
        self.result_timer = 0.0
        self.result_text = ''
        self.result_color = COLORS['gold']

        # Tree visual
        self.tree_x = WINDOW_WIDTH // 2
        self.tree_base_y = 400
        self.tree_sway = 0.0
        self.time = 0.0

        # Fonts
        self.font_title = pygame.font.SysFont('microsoftyahei', 36, bold=True)
        self.font_big = pygame.font.SysFont('microsoftyahei', 48, bold=True)
        self.font_info = pygame.font.SysFont('microsoftyahei', 20)
        self.font_small = pygame.font.SysFont('microsoftyahei', 16)
        self.font_item = pygame.font.SysFont('microsoftyahei', 22, bold=True)

        self.tree_rect = pygame.Rect(0, 0, 0, 0)

    def reset(self):
        self.game_state = 'idle'
        self.shakes_left = MAX_SHAKES
        self.shake_anim = 0.0
        self.shake_intensity = 0.0
        self.accumulated = 0
        self.current_drop = None
        self.drop_x = 0
        self.drop_y = 0
        self.drop_vy = 0
        self.drop_anim = 0.0
        self.drop_caught = False
        self.result_timer = 0.0
        self.result_text = ''
        self.result_color = COLORS['gold']
        self.tree_sway = 0.0
        self.time = 0.0
        self.particles.clear()

    def handle_click(self, mouse_pos: tuple):
        if self.game_state == 'idle':
            if self.tree_rect.collidepoint(mouse_pos) and self.shakes_left > 0:
                self._shake_tree()
        elif self.game_state == 'shaking':
            if self.tree_rect.collidepoint(mouse_pos) and self.shakes_left > 0:
                self._shake_tree()
        elif self.game_state == 'catching':
            if self.result_timer >= 1.5:
                self._next_round()
        elif self.game_state == 'done':
            pass

    def _shake_tree(self):
        self.shakes_left -= 1
        self.shake_anim = TREE_SHAKE_ANIM_DURATION
        self.shake_intensity = 10.0
        self.game_state = 'shaking'
        self.time = 0.0

    def _start_drop(self):
        # Determine what falls
        roll = random.random()
        cumulative = 0.0
        for key, drop_data in TREE_DROPS.items():
            cumulative += drop_data['probability']
            if roll < cumulative:
                self.current_drop = key
                self._item_data = drop_data
                break

        # Position
        offset = random.uniform(-60, 60)
        self.drop_x = self.tree_x + offset
        self.drop_y = self.tree_base_y - 200
        self.drop_vy = 100
        self.drop_gravity = 400
        self.drop_anim = 0.0
        self.drop_caught = False
        self.game_state = 'dropping'

    def _next_round(self):
        if self.shakes_left > 0:
            self.game_state = 'idle'
            self.current_drop = None
        else:
            self._show_result()

    def _show_result(self):
        if self.accumulated > 0:
            self.result_text = f'苹果树收获: +¥{self.accumulated}!'
            self.result_color = COLORS['gold']
        elif self.accumulated == 0:
            self.result_text = '什么也没拿到...'
            self.result_color = COLORS['text_secondary']
        self.game_state = 'done'
        self.result_timer = 0.0

    def update(self, dt: float):
        self.particles.update(dt)
        self.time += dt
        self.tree_sway = math.sin(self.time * 2) * 3.0

        if self.game_state == 'shaking':
            self.shake_anim -= dt
            self.shake_intensity *= (1 - dt * 8)
            if self.shake_anim <= 0:
                self._start_drop()

        elif self.game_state == 'dropping':
            self.drop_anim += dt
            self.drop_vy += self.drop_gravity * dt
            self.drop_y += self.drop_vy * dt

            if self.drop_y >= self.tree_base_y + 40:
                self._process_drop()

        elif self.game_state == 'catching':
            self.result_timer += dt

        elif self.game_state == 'done':
            self.result_timer += dt

    def _process_drop(self):
        key = self.current_drop
        data = self._item_data

        if key == 'bug':
            self.accumulated = 0
            self.result_text = f'{data["icon"]} 虫子来了！积蓄清零！'
            self.result_color = '#FF4444'
            self.particles.emit_burst(
                (self.drop_x, self.drop_y), 20,
                hex_to_rgb('#800080'),
                speed_range=(50, 200), lifetime=1.0, size=3
            )
        elif key == 'bee':
            self.result_text = f'{data["icon"]} 蜜蜂飞走了，摇树结束！'
            self.result_color = COLORS['gold']
            self.particles.emit_burst(
                (self.drop_x, self.drop_y), 15,
                hex_to_rgb('#FFA500'),
                speed_range=(80, 250), lifetime=1.5, size=3
            )
            self._show_result()
            return
        else:
            self.accumulated += data['value']
            self.result_text = f'{data["icon"]} {data["name"]} +¥{data["value"]}！'
            self.result_color = data['color']
            self.particles.emit_burst(
                (self.drop_x, self.drop_y), 15,
                hex_to_rgb(data['color']),
                speed_range=(50, 150), lifetime=1.0, size=3
            )

        if self.shakes_left > 0:
            self.game_state = 'catching'
            self.result_timer = 0.0
        else:
            self._show_result()

    def draw(self, surface: pygame.Surface):
        self._draw_sky(surface)
        self._draw_ground(surface)

        self._draw_tree(surface)

        if self.current_drop and self.game_state in ('dropping', 'catching', 'done'):
            self._draw_falling_item(surface)

        self._draw_hud(surface)

        if self.game_state == 'catching':
            self._draw_catch_text(surface)
        elif self.game_state == 'done':
            self._draw_done(surface)

        self.particles.draw(surface)

    def _draw_sky(self, surface: pygame.Surface):
        for y in range(self.tree_base_y):
            ratio = y / max(1, self.tree_base_y)
            r = int(95 + ratio * 40)
            g = int(170 + ratio * 60)
            b = int(220 - ratio * 80)
            pygame.draw.line(surface, (r, g, b), (0, y), (WINDOW_WIDTH, y))

    def _draw_ground(self, surface: pygame.Surface):
        for y in range(self.tree_base_y, WINDOW_HEIGHT):
            progress = (y - self.tree_base_y) / (WINDOW_HEIGHT - self.tree_base_y)
            r = int(35 + progress * 25)
            g = int(105 + progress * 35)
            b = int(25 + progress * 20)
            pygame.draw.line(surface, (r, g, b), (0, y), (WINDOW_WIDTH, y))

        for x in range(0, WINDOW_WIDTH, 30):
            h = 10 + int(5 * math.sin(self.time + x * 0.12))
            sway = int(3 * math.cos(self.time * 0.7 + x * 0.05))
            tip_x = x + sway
            g1, g2 = (45, 150, 35), (60, 180, 50)
            pygame.draw.line(surface, g1, (tip_x, self.tree_base_y), (tip_x, self.tree_base_y - h), 2)
            if h > 6:
                pygame.draw.line(surface, g2, (tip_x - 1, self.tree_base_y), (tip_x - 1, self.tree_base_y - h + 2), 1)

    def _draw_tree(self, surface: pygame.Surface):
        cx = self.tree_x
        base_y = self.tree_base_y

        if self.shake_intensity > 0.5:
            shake_x = random.uniform(-self.shake_intensity, self.shake_intensity)
            shake_y = random.uniform(-self.shake_intensity, self.shake_intensity)
        else:
            shake_x = self.tree_sway
            shake_y = 0

        self.tree_rect = pygame.Rect(cx - 80, base_y - 280, 160, 280)

        trunk_color = (100, 70, 40)
        trunk_light = (130, 95, 55)
        trunk_h = 150
        pygame.draw.rect(surface, trunk_color,
                        (cx - 12 + shake_x, base_y - trunk_h + shake_y, 24, trunk_h),
                        border_radius=4)
        pygame.draw.rect(surface, trunk_light,
                        (cx - 6 + shake_x, base_y - trunk_h + shake_y, 6, trunk_h),
                        border_radius=2)

        for side in [-1, 1]:
            pygame.draw.line(surface, trunk_color,
                           (cx + shake_x, base_y + shake_y),
                           (cx + side * 30 + shake_x, base_y + 12 + shake_y), 5)
            pygame.draw.line(surface, trunk_light,
                           (cx + shake_x, base_y + shake_y),
                           (cx + side * 20 + shake_x, base_y + 8 + shake_y), 2)

        canopy_color = (30, 110, 18)
        canopy_hl = (50, 150, 30)
        canopy_layers = [
            (145, base_y - 205, 0.8),
            (165, base_y - 182, 1.0),
            (125, base_y - 152, 1.1),
        ]

        for width, y, depth in canopy_layers:
            ox = shake_x * depth + shake_y * 0.1
            c_rect = pygame.Rect(cx - width // 2 + ox, y + shake_y, width, 82)
            pygame.draw.ellipse(surface, canopy_color, c_rect)
            c_rect2 = pygame.Rect(cx - width // 3 + ox, y + 8 + shake_y, width // 2 + 10, 28)
            pygame.draw.ellipse(surface, canopy_hl, c_rect2)

        for i in range(8):
            angle = i * 0.785 + self.time * 0.2
            ax = cx + int(50 * math.sin(angle)) + int(shake_x)
            ay = base_y - 170 + int(30 * abs(math.cos(angle))) + int(shake_y)
            pygame.draw.circle(surface, '#CC1A1A', (ax, ay), 7)
            pygame.draw.circle(surface, '#FF4040', (ax - 1, ay - 1), 4)
            pygame.draw.circle(surface, '#FF8888', (ax - 2, ay - 3), 2)

        title_surf = self.font_title.render('苹果树', True, hex_to_rgb(COLORS['gold']))
        shadow_t = self.font_title.render('苹果树', True, (30, 25, 15))
        surface.blit(shadow_t, shadow_t.get_rect(center=(cx + 2, 37)))
        surface.blit(title_surf, title_surf.get_rect(center=(cx, 35)))

    def _draw_falling_item(self, surface: pygame.Surface):
        data = self._item_data
        color = hex_to_rgb(data['color'])
        dx, dy = int(self.drop_x), int(self.drop_y)

        if self.current_drop == 'bug':
            shadow = (20, 20, 20, 80)
            pygame.draw.ellipse(surface, shadow,
                              (dx - 9, dy - 5, 18, 12))
            pygame.draw.circle(surface, color, (dx, dy), 10)
            pygame.draw.circle(surface, (160, 60, 160), (dx - 1, dy - 2), 5)
            for leg_dx in [-6, 0, 6]:
                pygame.draw.line(surface, color, (dx + leg_dx, dy),
                               (dx + leg_dx + 4, dy + 7), 2)
            pygame.draw.circle(surface, (255, 255, 255, 150), (dx - 2, dy - 2), 2)
        elif self.current_drop == 'bee':
            shadow = (20, 20, 20, 80)
            pygame.draw.ellipse(surface, shadow,
                              (dx - 9, dy - 5, 18, 12))
            pygame.draw.ellipse(surface, color,
                              (dx - 10, dy - 8, 20, 16))
            pygame.draw.ellipse(surface, (255, 200, 60), (dx - 4, dy - 4, 8, 8))
            pygame.draw.line(surface, '#000000',
                           (dx - 10, dy), (dx - 18, dy - 5), 2)
            pygame.draw.circle(surface, (255, 255, 255, 150), (dx - 3, dy - 3), 2)
        else:
            if self.current_drop == 'money_bag':
                shadow = (20, 20, 20, 80)
                pygame.draw.ellipse(surface, shadow,
                                  (dx - 9, dy + 2, 18, 10))
                pygame.draw.polygon(surface, color, [
                    (dx, dy - 12), (dx - 10, dy + 5), (dx + 10, dy + 5),
                ])
                pygame.draw.circle(surface, color, (dx, dy + 8), 8)
                pygame.draw.circle(surface, hex_to_rgb('#FFF3B0'), (dx - 1, dy + 6), 2)
                pygame.draw.circle(surface, hex_to_rgb(COLORS['gold_dark']), (dx, dy + 2), 4, 1)
            else:
                coin_r = 9
                shadow = (20, 20, 20, 80)
                pygame.draw.ellipse(surface, shadow,
                                  (dx - coin_r - 1, dy + 3, coin_r * 2 + 2, 8))
                pygame.draw.circle(surface, hex_to_rgb(COLORS['gold_dark']), (dx, dy + 1), coin_r + 1)
                pygame.draw.circle(surface, color, (dx, dy), coin_r)
                hl = hex_to_rgb('#FFF3B0') if self.current_drop == 'money_bag' else (255, 255, 255, 120)
                pygame.draw.circle(surface, hl, (dx - 2, dy - 3), 3)

    def _draw_hud(self, surface: pygame.Surface):
        cx = self.tree_x

        shakes_surf = self.font_info.render(
            f'剩余摇动: {self.shakes_left}/{MAX_SHAKES} 次',
            True, hex_to_rgb(COLORS['gold']))
        shadow = self.font_info.render(f'剩余摇动: {self.shakes_left}/{MAX_SHAKES} 次', True, (30, 25, 10))
        surface.blit(shadow, shadow.get_rect(center=(cx + 1, 76)))
        surface.blit(shakes_surf, shakes_surf.get_rect(center=(cx, 75)))

        if self.accumulated > 0:
            acc_surf = self.font_info.render(f'已收获: ¥{self.accumulated}',
                                            True, hex_to_rgb(COLORS['success']))
            surface.blit(acc_surf, acc_surf.get_rect(center=(cx, 100)))

        if self.game_state == 'idle' and self.shakes_left > 0:
            pulse = 0.5 + 0.5 * math.sin(self.time * 3)
            hx = cx - 90
            hy = self.tree_base_y + 38
            hint_bg = pygame.Rect(hx, hy, 180, 36)
            hint_s = pygame.Surface((hint_bg.width, hint_bg.height), pygame.SRCALPHA)
            hint_s.fill((255, 200, 100, 6))
            surface.blit(hint_s, hint_bg)
            pygame.draw.rect(surface, hex_to_rgb(COLORS['gold_dark']), hint_bg, 1, border_radius=10)

            hint_surf = self.font_small.render('点击苹果树摇动', True, hex_to_rgb(COLORS['gold']))
            hint_surf.set_alpha(int(150 + 100 * pulse))
            surface.blit(hint_surf, hint_surf.get_rect(center=(cx, hy + 18)))

    def _draw_catch_text(self, surface: pygame.Surface):
        if not self.current_drop:
            return

        data = self._item_data
        text_surf = self.font_item.render(self.result_text, True, hex_to_rgb(self.result_color))
        surface.blit(text_surf, text_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 120)))

        if self.shakes_left > 0 and self.result_timer >= 1.5:
            back_surf = self.font_small.render('点击继续摇树', True, hex_to_rgb(COLORS['text_secondary']))
            back_surf.set_alpha(int(150 + 100 * math.sin(self.time * 4)))
            surface.blit(back_surf, back_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 60)))

    def _draw_done(self, surface: pygame.Surface):
        if self.result_timer < 0.2:
            return

        progress = clamp(self.result_timer / 0.5, 0, 1)
        eased = ease_out_quad(progress)

        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, int(160 * eased)))
        surface.blit(overlay, (0, 0))

        result_surf = self.font_big.render(self.result_text, True, hex_to_rgb(self.result_color))
        surface.blit(result_surf, result_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 20)))

        if self.result_timer >= 1.0:
            back_surf = self.font_small.render('点击任意位置返回', True, hex_to_rgb(COLORS['text_secondary']))
            back_surf.set_alpha(int(150 + 100 * math.sin(self.time * 4)))
            surface.blit(back_surf, back_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 50)))
