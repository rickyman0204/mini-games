"""Trash Collection Game - collect trash within 5 seconds"""
import random
import math
import pygame

from src.settings import (
    WINDOW_WIDTH, WINDOW_HEIGHT, COLORS,
    TRASH_ENTRY_COST, TRASH_TIME_LIMIT, TRASH_COUNT,
)
from src.utils import s, get_font, hex_to_rgb, draw_button, draw_text_with_shadow, draw_exit_button, draw_game_border, draw_breathing_hint, draw_result_overlay, draw_progress_bar, ease_out_quad, clamp, get_mouse_pos
from src.particles import ParticleEmitter

TRASH_TYPES = {
    'apple': {
        'name': '啃完的苹果',
        'value_range': (1, 10),
        'color': '#8B4513',
        'emoji': '🍎',
        'pickup_base': (0.1, 0.75),
        'pickup_extra': (0.1, 0.3),
    },
    'can': {
        'name': '易拉罐',
        'value_range': (10, 20),
        'color': '#C0C0C0',
        'emoji': '🥫',
        'pickup_base': (0.1, 0.75),
        'pickup_extra': (0.1, 0.3),
    },
    'bottle': {
        'name': '空瓶子',
        'value_range': (20, 50),
        'color': '#2ECC71',
        'emoji': '🧴',
        'pickup_base': (0.1, 0.75),
        'pickup_extra': (0.1, 0.3),
    },
}

AREA_COLS = 5
AREA_ROWS = 4
ITEM_SPACING = s(65)
AREA_START_X = (WINDOW_WIDTH - (AREA_COLS - 1) * ITEM_SPACING) // 2
AREA_START_Y = s(140)


class TrashItem:

    def __init__(self, x, y, trash_type):
        self.x = x
        self.y = y
        self.type = trash_type
        self.collected = False
        self.picking_up = False
        self.pickup_timer = 0.0
        self.pickup_duration = 0.0
        self.pickup_delayed = False
        self.damaged = random.random() < 0.02
        self.rotten = (trash_type == 'apple') and (random.random() < 0.20)
        self.dented = (trash_type == 'can') and (random.random() < 0.10)
        self.bob_timer = random.uniform(0, math.pi * 2)

    def start_pickup(self):
        if self.picking_up or self.collected:
            return
        self.picking_up = True
        self.pickup_timer = 0.0
        self.pickup_delayed = False
        base_lo, base_hi = TRASH_TYPES[self.type]['pickup_base']
        extra_lo, extra_hi = TRASH_TYPES[self.type]['pickup_extra']
        base_time = random.uniform(base_lo, base_hi)
        extra_time = random.uniform(extra_lo, extra_hi)
        self.pickup_duration = base_time + extra_time

        if random.random() < 0.10:
            self.pickup_delayed = True
            self.pickup_duration += random.uniform(1.0, 2.0)

    @property
    def value(self):
        lo, hi = TRASH_TYPES[self.type]['value_range']
        return random.randint(lo, hi)

    @property
    def pickup_progress(self):
        if not self.picking_up:
            return 0.0
        return min(self.pickup_timer / self.pickup_duration, 1.0)

    def draw(self, surface, dt, font_item, font_value):
        if self.collected:
            return

        self.bob_timer += dt * 2
        bob_y = math.sin(self.bob_timer) * s(3)

        cx = self.x
        cy = self.y + bob_y

        if self.picking_up:
            progress = self.pickup_progress
            alpha = int(255 * (1 - progress * 0.6))
            scale = 1.0 + progress * 0.3
            surface.set_clip(None)
            ring_color = (255, 80, 80, int(120 * (1 - progress))) if self.pickup_delayed else (255, 215, 0, int(100 * (1 - progress)))
            ring_r = int(s(22) * scale)
            ring_surf = pygame.Surface((ring_r * 2, ring_r * 2), pygame.SRCALPHA)
            pygame.draw.circle(ring_surf, ring_color, (ring_r, ring_r), ring_r - s(2), s(3))
            surface.blit(ring_surf, (cx - ring_r, cy - ring_r))

        shadow_surf = pygame.Surface((s(40), s(10)), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surf, (0, 0, 0, 40), (0, 0, s(40), s(10)))
        surface.blit(shadow_surf, (cx - s(20), self.y + s(18)))

        if self.type == 'apple':
            self._draw_apple(surface, cx, cy)
        elif self.type == 'can':
            self._draw_can(surface, cx, cy)
        elif self.type == 'bottle':
            self._draw_bottle(surface, cx, cy)

        if self.damaged and not self.picking_up:
            x_surf = font_value.render('✗', True, hex_to_rgb('#FF4444'))
            surface.blit(x_surf, x_surf.get_rect(center=(cx + s(22), cy - s(15))))

        if self.rotten and not self.picking_up:
            x_surf = font_value.render('☠', True, hex_to_rgb('#6B4226'))
            surface.blit(x_surf, x_surf.get_rect(center=(cx + s(22), cy - s(15))))

        if self.dented and not self.picking_up:
            x_surf = font_value.render('⚙', True, hex_to_rgb('#808090'))
            surface.blit(x_surf, x_surf.get_rect(center=(cx + s(22), cy - s(15))))

        if self.picking_up:
            progress = self.pickup_progress
            bar_w, bar_h = s(30), s(6)
            bar_x, bar_y = cx - bar_w // 2, cy - s(30)
            pygame.draw.rect(surface, (50, 50, 70), (bar_x, bar_y, bar_w, bar_h), border_radius=s(2))
            pygame.draw.rect(surface, hex_to_rgb(COLORS['gold']), (bar_x, bar_y, bar_w * progress, bar_h), border_radius=s(2))

        lo, hi = TRASH_TYPES[self.type]['value_range']
        val_text = font_value.render(f'¥{lo}-{hi}', True, hex_to_rgb(COLORS['gold']))
        surface.blit(val_text, val_text.get_rect(center=(cx, cy + s(28))))

    def _draw_apple(self, surface, cx, cy):
        r = s(15)
        pygame.draw.circle(surface, hex_to_rgb('#A0522D'), (cx, cy), r)
        pygame.draw.circle(surface, hex_to_rgb('#DEB887'), (cx + s(8), cy - s(5)), s(8))
        pygame.draw.line(surface, hex_to_rgb('#5C3317'), (cx, cy - r), (cx + s(2), cy - r - s(6)), s(2))
        pygame.draw.ellipse(surface, hex_to_rgb('#228B22'), (cx + s(2), cy - r - s(8), s(8), s(4)))

    def _draw_can(self, surface, cx, cy):
        w, h = s(20), s(28)
        pygame.draw.rect(surface, hex_to_rgb('#A8A8A8'), (cx - w // 2, cy - h // 2, w, h), border_radius=s(3))
        pygame.draw.rect(surface, hex_to_rgb('#C0C0C0'), (cx - w // 2 + s(2), cy - h // 2, w - s(4), s(4)), border_radius=s(2))
        pygame.draw.rect(surface, hex_to_rgb('#E74C3C'), (cx - w // 2, cy - s(4), w, s(8)))
        pygame.draw.line(surface, hex_to_rgb('#808080'), (cx - s(5), cy - s(6)), (cx + s(3), cy + s(2)), s(1))

    def _draw_bottle(self, surface, cx, cy):
        pygame.draw.rect(surface, hex_to_rgb('#27AE60'), (cx - s(10), cy - s(8), s(20), s(24)), border_radius=s(4))
        pygame.draw.rect(surface, hex_to_rgb('#27AE60'), (cx - s(5), cy - s(18), s(10), s(12)), border_radius=s(2))
        pygame.draw.rect(surface, hex_to_rgb('#E74C3C'), (cx - s(5), cy - s(20), s(10), s(4)), border_radius=s(1))
        pygame.draw.rect(surface, hex_to_rgb('#FFFFFF'), (cx - s(8), cy, s(16), s(10)), border_radius=s(1))


class TrashGame:

    def __init__(self, wallet):
        self.wallet = wallet
        self.particles = ParticleEmitter()

        self.game_state = 'idle'

        self.items = []
        self.total_value = 0
        self.collected_count = 0

        self.timer = 0.0
        self.time_limit = random.uniform(5.0, 10.0)

        self.result_timer = 0.0
        self.shake_intensity = 0.0
        self.water_offset = 0.0

        self.start_btn_rect = pygame.Rect(0, 0, 0, 0)
        self.exit_btn_rect = pygame.Rect(0, 0, 0, 0)

        self.font_title = get_font(58, bold=True)
        self.font_big = get_font(77, bold=True)
        self.font_info = get_font(32)
        self.font_small = get_font(26)
        self.font_btn = get_font(38, bold=True)
        self.font_timer = get_font(51, bold=True)
        self.font_item = get_font(32)
        self.font_value = get_font(s(19))

        self._generate_items()

    def _generate_items(self):
        self.items = []
        trash_keys = list(TRASH_TYPES.keys())
        for row in range(AREA_ROWS):
            for col in range(AREA_COLS):
                x = AREA_START_X + col * ITEM_SPACING
                y = AREA_START_Y + row * ITEM_SPACING
                r = random.random()
                if r < 0.35:
                    t = 'apple'
                elif r < 0.70:
                    t = 'can'
                else:
                    t = 'bottle'
                self.items.append(TrashItem(x, y, t))

    def reset(self):
        self.game_state = 'idle'
        self.timer = 0.0
        self.total_value = 0
        self.collected_count = 0
        self.result_timer = 0.0
        self.shake_intensity = 0.0
        self.water_offset = 0.0
        self.particles.clear()
        self._generate_items()
        for item in self.items:
            item.collected = False
            item.picking_up = False
            item.pickup_timer = 0.0

    def handle_click(self, mouse_pos: tuple):
        if self.exit_btn_rect.collidepoint(mouse_pos):
            self.game_state = 'done'
            return

        if self.game_state == 'idle':
            if self.start_btn_rect.collidepoint(mouse_pos):
                self._start_game()
        elif self.game_state == 'playing':
            for item in self.items:
                if not item.collected and not item.picking_up:
                    dx = mouse_pos[0] - item.x
                    dy = mouse_pos[1] - item.y
                    if math.sqrt(dx * dx + dy * dy) < s(25):
                        item.start_pickup()
        elif self.game_state == 'result' and self.result_timer >= 0.5:
            self.game_state = 'done'

    def _start_game(self):
        self.game_state = 'playing'
        self.timer = 0.0
        self.time_limit = random.uniform(5.0, 10.0)
        self.total_value = 0
        self.collected_count = 0
        self.wallet.subtract(TRASH_ENTRY_COST)
        for item in self.items:
            item.collected = False
            item.picking_up = False
            item.pickup_timer = 0.0
            item.pickup_delayed = False

    def update(self, dt: float):
        self.particles.update(dt)
        self.water_offset += dt * 2
        self.shake_intensity *= (1 - dt * 6)

        if self.game_state == 'playing':
            self.timer += dt

            for item in self.items:
                if item.picking_up and not item.collected:
                    item.pickup_timer += dt
                    if item.pickup_timer >= item.pickup_duration:
                        item.collected = True
                        item.picking_up = False
                        if item.damaged:
                            self.wallet.subtract(1)
                            self.particles.emit_burst(
                                (item.x, item.y),
                                5, hex_to_rgb('#FF4444'),
                                speed_range=(30, 60), lifetime=0.5, size=2
                            )
                        elif item.rotten:
                            self.wallet.subtract(10)
                            self.particles.emit_burst(
                                (item.x, item.y),
                                8, hex_to_rgb('#6B4226'),
                                speed_range=(30, 80), lifetime=0.6, size=3
                            )
                        elif item.dented:
                            self.wallet.subtract(5)
                            self.particles.emit_burst(
                                (item.x, item.y),
                                6, hex_to_rgb('#808090'),
                                speed_range=(30, 70), lifetime=0.5, size=2
                            )
                        else:
                            val = item.value
                            self.total_value += val
                        self.collected_count += 1
                        self.particles.emit_burst(
                            (item.x, item.y),
                            8, hex_to_rgb(TRASH_TYPES[item.type]['color']),
                            speed_range=(40, 100), lifetime=0.6, size=3
                        )

            if self.timer >= self.time_limit:
                self.timer = self.time_limit
                self.game_state = 'result'
                self.result_timer = 0.0
                self.shake_intensity = 5.0
                self.wallet.add(self.total_value)
                if self.total_value > 0:
                    self.particles.emit_confetti(
                        (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2),
                        40, ['#FFD700', '#2ECC71', '#FFFFFF'], lifetime=2.0
                    )

        elif self.game_state == 'result':
            self.result_timer += dt

    def draw(self, surface: pygame.Surface):
        surface.fill(hex_to_rgb(COLORS['bg_primary']))

        ox, oy = 0, 0
        if self.shake_intensity > 0.5:
            ox = random.uniform(-self.shake_intensity, self.shake_intensity)
            oy = random.uniform(-self.shake_intensity, self.shake_intensity)

        self._draw_border(surface)
        self._draw_title(surface)
        self._draw_ground(surface)
        self._draw_items(surface)

        if self.game_state == 'idle':
            self._draw_start_button(surface)
        elif self.game_state == 'playing':
            self._draw_timer(surface, ox, oy)
            self._draw_hud(surface)

        if self.game_state == 'result':
            self._draw_result_overlay(surface)

        self._draw_exit_button(surface)
        self.particles.draw(surface)

    def _draw_border(self, surface: pygame.Surface):
        pygame.draw.rect(surface, hex_to_rgb(COLORS['red_primary']),
                         (s(4), s(4), WINDOW_WIDTH - s(8), WINDOW_HEIGHT - s(8)), s(2))

    def _draw_title(self, surface: pygame.Surface):
        title_surf = self.font_title.render('捡垃圾', True, hex_to_rgb(COLORS['gold']))
        surface.blit(title_surf, title_surf.get_rect(center=(WINDOW_WIDTH // 2, s(24))))

    def _draw_ground(self, surface: pygame.Surface):
        ground_w = AREA_COLS * ITEM_SPACING + s(64)
        ground_h = AREA_ROWS * ITEM_SPACING + s(60)
        ground_x = AREA_START_X - s(30)
        ground_y = AREA_START_Y - s(30)

        pygame.draw.rect(surface, hex_to_rgb('#2a1f15'),
                         (ground_x, ground_y, ground_w, ground_h), border_radius=s(12))
        pygame.draw.rect(surface, hex_to_rgb('#4a3525'),
                         (ground_x, ground_y, ground_w, ground_h), s(2), border_radius=s(12))

        for i in range(12):
            gx = ground_x + s(15) + i * (ground_w - s(30)) // 11
            gy = ground_y + ground_h - s(10)
            pygame.draw.line(surface, hex_to_rgb('#3a5a2a'), (gx, gy), (gx - s(3), gy - s(8)), s(2))
            pygame.draw.line(surface, hex_to_rgb('#4a6a3a'), (gx, gy), (gx + s(2), gy - s(10)), s(2))

    def _draw_items(self, surface: pygame.Surface):
        dt = 0.016
        for item in self.items:
            item.draw(surface, dt, self.font_item, self.font_value)

    def _draw_timer(self, surface: pygame.Surface, ox: float, oy: float):
        remaining = max(0, self.time_limit - self.timer)
        timer_color = hex_to_rgb(COLORS['gold']) if remaining > 2 else hex_to_rgb('#FF4444')

        timer_surf = self.font_timer.render(f'{remaining:.1f}s', True, timer_color)
        surface.blit(timer_surf, timer_surf.get_rect(center=(WINDOW_WIDTH // 2, s(97))))

        bar_w = s(200)
        bar_h = s(6)
        bar_x = WINDOW_WIDTH // 2 - bar_w // 2
        bar_y = s(123)
        progress = clamp(remaining / self.time_limit, 0, 1)
        pygame.draw.rect(surface, (40, 40, 60), (bar_x, bar_y, bar_w, bar_h), border_radius=s(3))
        pygame.draw.rect(surface, timer_color, (bar_x, bar_y, bar_w * progress, bar_h), border_radius=s(3))

    def _draw_hud(self, surface: pygame.Surface):
        hud_text = f'已收集: {self.collected_count} | 累计: ¥{self.total_value}'
        hud_surf = self.font_info.render(hud_text, True, hex_to_rgb(COLORS['text_secondary']))
        surface.blit(hud_surf, hud_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - s(45))))

    def _draw_start_button(self, surface: pygame.Surface):
        btn_w, btn_h = s(200), s(55)
        btn_x = WINDOW_WIDTH // 2
        btn_y = AREA_START_Y + AREA_ROWS * ITEM_SPACING + s(52)
        self.start_btn_rect = pygame.Rect(btn_x - btn_w // 2, btn_y, btn_w, btn_h)

        mouse_pos = get_mouse_pos()
        is_hover = self.start_btn_rect.collidepoint(mouse_pos)

        bg_color = hex_to_rgb(COLORS['success']) if is_hover else tuple(int(c * 0.8) for c in hex_to_rgb(COLORS['success']))
        pygame.draw.rect(surface, bg_color, self.start_btn_rect, border_radius=s(12))
        pygame.draw.rect(surface, hex_to_rgb(COLORS['gold_light']), self.start_btn_rect, s(2), border_radius=s(12))

        btn_surf = self.font_btn.render(f'开始捡垃圾 ¥{TRASH_ENTRY_COST}', True, hex_to_rgb('#1a3a1a'))
        surface.blit(btn_surf, btn_surf.get_rect(center=(btn_x, btn_y + btn_h // 2)))

    def _draw_exit_button(self, surface: pygame.Surface):
        btn_w, btn_h = s(70), s(32)
        btn_x, btn_y = s(15), s(10)
        self.exit_btn_rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)

        mouse_pos = get_mouse_pos()
        is_hover = self.exit_btn_rect.collidepoint(mouse_pos)

        bg_color = hex_to_rgb('#FF4444') if is_hover else hex_to_rgb(COLORS['red_primary'])
        pygame.draw.rect(surface, bg_color, self.exit_btn_rect, border_radius=s(6))
        pygame.draw.rect(surface, hex_to_rgb(COLORS['gold_dark']), self.exit_btn_rect, s(2), border_radius=s(6))

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

        if self.total_value > 0:
            result_text = f'收集了 {self.collected_count} 件垃圾 → +¥{self.total_value}'
            color = hex_to_rgb(COLORS['gold'])
        else:
            result_text = '时间到！什么都没捡到...'
            color = hex_to_rgb(COLORS['text_secondary'])

        result_surf = self.font_big.render(result_text, True, color)
        surface.blit(result_surf, result_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - s(20))))

        if self.result_timer >= 0.5:
            draw_breathing_hint(surface, '点击任意位置返回', self.font_small,
                               COLORS['text_secondary'],
                               (WINDOW_WIDTH // 2, WINDOW_HEIGHT - s(50)),
                               self.water_offset, speed=4)
