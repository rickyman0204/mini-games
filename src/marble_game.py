"""Marble Game - drop marbles with realistic physics bouncing through pegs"""
import math
import random
import pygame

from src.settings import (
    WINDOW_WIDTH, WINDOW_HEIGHT, COLORS,
    MARBLE_ENTRY_COST, MARBLE_COUNT,
)
from src.utils import (
    s, get_font, hex_to_rgb, get_mouse_pos, clamp, ease_out_quad,
    draw_button, draw_text_with_shadow, draw_exit_button,
    draw_breathing_hint, draw_result_overlay,
)
from src.particles import ParticleEmitter

MACHINE_X = s(60)
MACHINE_Y = s(70)
MACHINE_W = WINDOW_WIDTH - s(120)
MACHINE_H = WINDOW_HEIGHT - s(150)

PEG_START_Y = MACHINE_Y + s(55)
PEG_ROWS = 8
PEG_SPACING_Y = s(36)
PEG_SPACING_X = s(60)
PEG_RADIUS = s(6)

FUNNEL_Y = MACHINE_Y + s(8)
FUNNEL_W = s(40)
FUNNEL_H = s(45)

TRAY_Y = PEG_START_Y + PEG_ROWS * PEG_SPACING_Y + s(8)
TRAY_H = s(55)
TRAY_DIV_H = s(22)

SLOT_W = (MACHINE_W - s(20)) // 7
SLOT_H = TRAY_H

GRAVITY = 580.0
BOUNCE_RESTITUTION = 0.55
MARBLE_RADIUS = s(9)
RANDOM_DEFLECTION = 0.45
MAX_DROP_TIME = 8.0

LANDING_SPOTS = [
    {'value': 2, 'color': '#C0C0C0'},
    {'value': 6, 'color': '#FFA500'},
    {'value': 10, 'color': '#FFD700'},
    {'value': 8, 'color': '#4CAF50'},
    {'value': 10, 'color': '#FFD700'},
    {'value': 6, 'color': '#FFA500'},
    {'value': 2, 'color': '#C0C0C0'},
]


class MarbleGame:

    def __init__(self, wallet):
        self.wallet = wallet
        self.particles = ParticleEmitter()

        self.game_state = 'idle'

        self.marbles_dropped = 0
        self.total_won = 0
        self.landing_history = []

        self.current_marble_x = 0.0
        self.current_marble_y = 0.0
        self.marble_vx = 0.0
        self.marble_vy = 0.0
        self.collided_pegs = set()
        self.drop_timer = 0.0

        self._settling = False
        self._settle_timer = 0.0
        self._current_landing = 3

        self.result_timer = 0.0
        self.shake_intensity = 0.0
        self.water_offset = 0.0
        self.particle_emitted = False

        self._calc_layout()

        self.font_title = get_font(42, bold=True)
        self.font_big = get_font(58, bold=True)
        self.font_info = get_font(28)
        self.font_small = get_font(22)
        self.font_btn = get_font(32, bold=True)
        self.font_value = get_font(28, bold=True)

        self.drop_btn_rect = pygame.Rect(0, 0, 0, 0)
        self.exit_btn_rect = pygame.Rect(0, 0, 0, 0)

    def _calc_layout(self):
        self.pegs = []
        for row in range(PEG_ROWS):
            for col in range(row + 1):
                px = WINDOW_WIDTH // 2 + (col - row / 2) * PEG_SPACING_X
                py = PEG_START_Y + row * PEG_SPACING_Y
                self.pegs.append((px, py))

        self.slot_centers = []
        for i in range(7):
            x = WINDOW_WIDTH // 2 + (i - 3) * SLOT_W
            self.slot_centers.append(x)

    def reset(self):
        self.game_state = 'idle'
        self.marbles_dropped = 0
        self.total_won = 0
        self.landing_history = []
        self.current_marble_x = 0.0
        self.current_marble_y = 0.0
        self.marble_vx = 0.0
        self.marble_vy = 0.0
        self.collided_pegs = set()
        self.drop_timer = 0.0
        self._settling = False
        self._settle_timer = 0.0
        self._current_landing = 3
        self.result_timer = 0.0
        self.shake_intensity = 0.0
        self.water_offset = 0.0
        self.particle_emitted = False
        self.particles.clear()

    def _determine_landing_slot(self):
        min_dist = float('inf')
        closest = 3
        for i, cx in enumerate(self.slot_centers):
            dist = abs(self.current_marble_x - cx)
            if dist < min_dist:
                min_dist = dist
                closest = i
        return closest

    def handle_click(self, mouse_pos: tuple):
        if self.exit_btn_rect.collidepoint(mouse_pos):
            self.game_state = 'done'
            return

        if self.game_state == 'idle':
            if self.drop_btn_rect.collidepoint(mouse_pos):
                self._drop_marble()
        elif self.game_state == 'result' and self.result_timer >= 0.5:
            self.game_state = 'done'

    def _drop_marble(self):
        self.marbles_dropped += 1
        self.current_marble_x = float(WINDOW_WIDTH // 2)
        self.current_marble_y = float(FUNNEL_Y + s(5))
        self.marble_vx = random.uniform(-20, 20)
        self.marble_vy = 30.0
        self.collided_pegs = set()
        self.drop_timer = 0.0
        self._settling = False
        self._settle_timer = 0.0
        self.game_state = 'dropping'

    def update(self, dt: float):
        self.particles.update(dt)
        self.water_offset += dt * 2
        self.shake_intensity *= (1 - dt * 6)

        if self.game_state == 'dropping':
            self.drop_timer += dt

            if self._settling:
                self._settle_timer += dt
                target_x = self.slot_centers[self._current_landing]
                target_y = TRAY_Y + TRAY_H // 2
                lerp_factor = min(1.0, self._settle_timer / 0.3)
                self.current_marble_x += (target_x - self.current_marble_x) * lerp_factor * 0.3
                self.current_marble_y += (target_y - self.current_marble_y) * lerp_factor * 0.3

                if self._settle_timer >= 0.3:
                    landing_value = LANDING_SPOTS[self._current_landing]['value']
                    self.total_won += landing_value
                    self.landing_history.append(self._current_landing)
                    self.shake_intensity = 5.0

                    slot_color = LANDING_SPOTS[self._current_landing]['color']
                    self.particles.emit_burst(
                        (self.current_marble_x, TRAY_Y),
                        15, hex_to_rgb(slot_color),
                        speed_range=(50, 150), lifetime=1.0, size=3
                    )

                    if self.marbles_dropped >= MARBLE_COUNT:
                        self.wallet.add(self.total_won)
                        self.game_state = 'result'
                        self.result_timer = 0.0

                        if self.total_won > 0:
                            self.particles.emit_confetti(
                                (WINDOW_WIDTH // 2, TRAY_Y),
                                40, ['#FFD700', '#FF9800', '#FFFFFF'], lifetime=2.0
                            )
                    else:
                        self.game_state = 'idle'
            else:
                sub_steps = 4
                sub_dt = dt / sub_steps

                for _ in range(sub_steps):
                    self.marble_vy += GRAVITY * sub_dt

                    self.current_marble_x += self.marble_vx * sub_dt
                    self.current_marble_y += self.marble_vy * sub_dt

                    for i, (px, py) in enumerate(self.pegs):
                        if i in self.collided_pegs:
                            continue

                        dx = self.current_marble_x - px
                        dy = self.current_marble_y - py
                        dist_sq = dx * dx + dy * dy
                        min_dist = MARBLE_RADIUS + PEG_RADIUS

                        if dist_sq < min_dist * min_dist:
                            dist = math.sqrt(dist_sq) if dist_sq > 0 else 0.001
                            nx = dx / dist
                            ny = dy / dist

                            overlap = min_dist - dist
                            self.current_marble_x += nx * overlap * 1.15
                            self.current_marble_y += ny * overlap * 1.15

                            vn = self.marble_vx * nx + self.marble_vy * ny
                            if vn < 0:
                                vt_x = self.marble_vx - vn * nx
                                vt_y = self.marble_vy - vn * ny

                                self.marble_vx = vt_x * 0.92 - BOUNCE_RESTITUTION * vn * nx
                                self.marble_vy = vt_y * 0.92 - BOUNCE_RESTITUTION * vn * ny

                                speed = math.sqrt(self.marble_vx ** 2 + self.marble_vy ** 2)
                                random_force = random.uniform(-1, 1) * RANDOM_DEFLECTION * speed
                                self.marble_vx += random_force

                            self.collided_pegs.add(i)
                            self.shake_intensity = 3.0

                    left_wall = MACHINE_X + MARBLE_RADIUS + s(5)
                    right_wall = MACHINE_X + MACHINE_W - MARBLE_RADIUS - s(5)
                    if self.current_marble_x < left_wall:
                        self.current_marble_x = left_wall
                        self.marble_vx = abs(self.marble_vx) * 0.5
                    elif self.current_marble_x > right_wall:
                        self.current_marble_x = right_wall
                        self.marble_vx = -abs(self.marble_vx) * 0.5

                    max_speed = 900.0
                    speed = math.sqrt(self.marble_vx ** 2 + self.marble_vy ** 2)
                    if speed > max_speed:
                        self.marble_vx *= max_speed / speed
                        self.marble_vy *= max_speed / speed

                if self.current_marble_y >= TRAY_Y:
                    self._current_landing = self._determine_landing_slot()
                    self._settling = True
                    self._settle_timer = 0.0

                if self.drop_timer > MAX_DROP_TIME:
                    self._current_landing = self._determine_landing_slot()
                    self._settling = True
                    self._settle_timer = 0.0

    def draw(self, surface: pygame.Surface):
        surface.fill(hex_to_rgb(COLORS['bg_primary']))

        ox, oy = 0, 0
        if self.shake_intensity > 0.5:
            ox = random.uniform(-self.shake_intensity, self.shake_intensity)
            oy = random.uniform(-self.shake_intensity, self.shake_intensity)

        self._draw_machine(surface, ox, oy)
        self._draw_title(surface)
        self._draw_info(surface)

        if self.game_state == 'dropping':
            self._draw_marble(surface)

        if self.game_state == 'idle':
            self._draw_drop_button(surface)

        mouse_pos = get_mouse_pos()
        self.exit_btn_rect = draw_exit_button(surface, mouse_pos, font_size=s(26))

        if self.game_state == 'result':
            self._draw_result_overlay(surface)

        self.particles.draw(surface)

    def _draw_machine(self, surface: pygame.Surface, ox: float, oy: float):
        machine_rect = pygame.Rect(MACHINE_X + ox, MACHINE_Y + oy, MACHINE_W, MACHINE_H)
        frame_pad = s(8)
        outer_rect = machine_rect.inflate(frame_pad * 2, frame_pad * 2)

        shadow_surf = pygame.Surface((outer_rect.width + s(6), outer_rect.height + s(6)), pygame.SRCALPHA)
        shadow_surf.fill((0, 0, 0, 40))
        surface.blit(shadow_surf, (outer_rect.x + s(3), outer_rect.y + s(3)))

        pygame.draw.rect(surface, hex_to_rgb('#5C3317'), outer_rect, border_radius=s(12))
        pygame.draw.rect(surface, hex_to_rgb('#8B5E3C'), outer_rect, s(3), border_radius=s(12))

        board_surf = pygame.Surface((MACHINE_W, MACHINE_H))
        for y in range(MACHINE_H):
            ratio = y / MACHINE_H
            r = int(20 + ratio * 10)
            g = int(20 + ratio * 15)
            b = int(40 + ratio * 10)
            pygame.draw.line(board_surf, (r, g, b), (0, y), (MACHINE_W, y))
        surface.blit(board_surf, (MACHINE_X + ox, MACHINE_Y + oy))

        self._draw_funnel(surface, ox, oy)
        self._draw_pegs(surface, ox, oy)
        self._draw_channels(surface, ox, oy)
        self._draw_tray(surface, ox, oy)

        pygame.draw.rect(surface, hex_to_rgb('#C0A060'),
                         (MACHINE_X + ox, MACHINE_Y + oy, MACHINE_W, MACHINE_H),
                         s(2), border_radius=s(4))

    def _draw_funnel(self, surface: pygame.Surface, ox: float, oy: float):
        cx = WINDOW_WIDTH // 2 + ox
        top_y = MACHINE_Y + oy + s(3)
        bottom_y = PEG_START_Y + oy - s(5)
        funnel_w = s(30)

        left_points = [(cx - funnel_w, top_y), (cx - s(8), bottom_y), (cx - s(8), top_y)]
        right_points = [(cx + funnel_w, top_y), (cx + s(8), bottom_y), (cx + s(8), top_y)]

        for points in [left_points, right_points]:
            pygame.draw.polygon(surface, hex_to_rgb('#C0A060'), points)
            pygame.draw.polygon(surface, hex_to_rgb('#E8D5A0'), points, s(1))

        pulse = 0.5 + 0.5 * math.sin(self.water_offset * 3)
        indicator_alpha = int(100 + 155 * pulse)
        indicator_size = s(16)
        indicator_surf = pygame.Surface((indicator_size, indicator_size), pygame.SRCALPHA)
        indicator_surf.set_alpha(indicator_alpha)
        pygame.draw.circle(indicator_surf, hex_to_rgb('#FFD700'),
                          (indicator_size // 2, indicator_size // 2), s(7))
        surface.blit(indicator_surf, (cx - indicator_size // 2, top_y - s(2)))

        arrow_surf = self.font_small.render('\u25bc', True, hex_to_rgb('#FFD700'))
        arrow_surf.set_alpha(indicator_alpha)
        surface.blit(arrow_surf, arrow_surf.get_rect(center=(cx, top_y + s(14))))

    def _draw_pegs(self, surface: pygame.Surface, ox: float, oy: float):
        for i, (px, py) in enumerate(self.pegs):
            x, y = int(px + ox), int(py + oy)
            hit = i in self.collided_pegs and self.game_state == 'dropping'

            pygame.draw.circle(surface, (30, 30, 50), (x + s(1), y + s(2)), PEG_RADIUS)

            if hit:
                pygame.draw.circle(surface, (160, 140, 100), (x, y), PEG_RADIUS + s(1))
                pygame.draw.circle(surface, (200, 180, 130), (x, y), PEG_RADIUS)
            else:
                pygame.draw.circle(surface, (80, 80, 100), (x, y), PEG_RADIUS)

            pygame.draw.circle(surface, (140, 140, 170), (x - s(1), y - s(1)), s(2))

    def _draw_channels(self, surface: pygame.Surface, ox: float, oy: float):
        row = PEG_ROWS - 1
        num_pegs_bottom = row + 1
        for col in range(num_pegs_bottom):
            peg_x = WINDOW_WIDTH // 2 + (col - row / 2) * PEG_SPACING_X
            peg_y = PEG_START_Y + row * PEG_SPACING_Y

            mapped_slot = int(col * 6 / PEG_ROWS)
            mapped_slot = max(0, min(6, mapped_slot))
            slot_x = self.slot_centers[mapped_slot]
            slot_top = TRAY_Y + oy

            pygame.draw.line(surface, (40, 40, 70),
                           (int(peg_x + ox), int(peg_y + oy)),
                           (int(slot_x + ox), int(slot_top)), s(2))

    def _draw_tray(self, surface: pygame.Surface, ox: float, oy: float):
        tray_top = TRAY_Y + oy

        pygame.draw.rect(surface, (15, 15, 30),
                         (MACHINE_X + ox, tray_top, MACHINE_W, TRAY_H),
                         border_radius=s(4))

        pygame.draw.line(surface, hex_to_rgb('#C0A060'),
                         (MACHINE_X + ox, tray_top),
                         (MACHINE_X + MACHINE_W + ox, tray_top), s(2))

        for i in range(7):
            x = self.slot_centers[i] + ox
            slot_color = LANDING_SPOTS[i]['color']
            color_rgb = hex_to_rgb(slot_color)

            if i > 0:
                div_x = x - SLOT_W // 2 + ox
                pygame.draw.rect(surface, (20, 20, 40),
                               (div_x - s(1), tray_top, s(4), TRAY_DIV_H))
                pygame.draw.rect(surface, hex_to_rgb('#C0A060'),
                               (div_x, tray_top, s(2), TRAY_DIV_H))

            slot_rect = pygame.Rect(x - SLOT_W // 2 + s(2), tray_top + s(4),
                                    SLOT_W - s(4), TRAY_H - s(8))

            slot_bg = pygame.Surface((slot_rect.width, slot_rect.height), pygame.SRCALPHA)
            slot_bg.fill((color_rgb[0], color_rgb[1], color_rgb[2], 25))
            surface.blit(slot_bg, slot_rect)

            pygame.draw.rect(surface, color_rgb, slot_rect, s(2), border_radius=s(6))

            val_surf = self.font_value.render(f'\xa5{LANDING_SPOTS[i]["value"]}', True, color_rgb)
            surface.blit(val_surf, val_surf.get_rect(center=(x, tray_top + TRAY_H // 2)))

        dot_y = tray_top + TRAY_H - s(6)
        for i, landing in enumerate(self.landing_history[-5:]):
            dx = self.slot_centers[landing] + (i - 2) * s(8) + ox
            pygame.draw.circle(surface, hex_to_rgb(COLORS['gold']),
                             (int(dx), int(dot_y)), s(3))

    def _draw_title(self, surface: pygame.Surface):
        draw_text_with_shadow(surface, '弹珠游戏', self.font_title,
                             COLORS['gold'], (WINDOW_WIDTH // 2, s(20)))

    def _draw_info(self, surface: pygame.Surface):
        info_text = f'剩余弹珠: {MARBLE_COUNT - self.marbles_dropped}/{MARBLE_COUNT}  |  已赢: \xa5{self.total_won}'
        info_surf = self.font_small.render(info_text, True, hex_to_rgb(COLORS['text_secondary']))
        surface.blit(info_surf, info_surf.get_rect(center=(WINDOW_WIDTH // 2, s(48))))

    def _draw_marble(self, surface: pygame.Surface):
        x, y = int(self.current_marble_x), int(self.current_marble_y)
        marble_r = MARBLE_RADIUS

        pygame.draw.circle(surface, (0, 0, 0, 40), (x + s(2), y + s(2)), marble_r)

        pygame.draw.circle(surface, '#CC3333', (x, y), marble_r)
        pygame.draw.circle(surface, hex_to_rgb('#FF6B6B'), (x, y), marble_r - s(1))

        pygame.draw.circle(surface, (255, 255, 255, 180), (x - s(3), y - s(3)), s(4))
        pygame.draw.circle(surface, (255, 255, 255, 80), (x - s(2), y - s(2)), s(2))

    def _draw_drop_button(self, surface: pygame.Surface):
        btn_w, btn_h = s(140), s(42)
        btn_x = WINDOW_WIDTH // 2
        btn_y = TRAY_Y + TRAY_H + s(12)
        self.drop_btn_rect = pygame.Rect(btn_x - btn_w // 2, btn_y, btn_w, btn_h)

        mouse_pos = get_mouse_pos()
        is_hover = self.drop_btn_rect.collidepoint(mouse_pos)

        if is_hover:
            bg_color = hex_to_rgb('#38B000')
        else:
            bg_color = hex_to_rgb('#2E9900')

        shadow_rect = pygame.Rect(btn_x - btn_w // 2, btn_y + s(3), btn_w, btn_h)
        shadow = pygame.Surface((shadow_rect.width, shadow_rect.height), pygame.SRCALPHA)
        shadow.fill((0, 0, 0, 50))
        surface.blit(shadow, shadow_rect)

        pygame.draw.rect(surface, bg_color, self.drop_btn_rect, border_radius=s(10))
        pygame.draw.rect(surface, hex_to_rgb(COLORS['gold']), self.drop_btn_rect, s(2), border_radius=s(10))

        btn_text = f'投弹珠 ({self.marbles_dropped}/{MARBLE_COUNT})'
        btn_surf = self.font_btn.render(btn_text, True, hex_to_rgb(COLORS['text_primary']))
        surface.blit(btn_surf, btn_surf.get_rect(center=(btn_x, btn_y + btn_h // 2)))

    def _draw_result_overlay(self, surface: pygame.Surface):
        if self.result_timer < 0.3:
            return

        progress = clamp((self.result_timer - 0.3) / 0.6, 0, 1)
        eased = ease_out_quad(progress)

        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, int(160 * eased)))
        surface.blit(overlay, (0, 0))

        if self.total_won > 0:
            result_text = f'弹珠收获: +\xa5{self.total_won}!'
            color = hex_to_rgb(COLORS['gold'])
        else:
            result_text = '没有收获...'
            color = hex_to_rgb(COLORS['text_secondary'])

        result_surf = self.font_big.render(result_text, True, color)
        surface.blit(result_surf, result_surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - s(20))))

        if self.result_timer >= 0.5:
            draw_breathing_hint(surface, '点击任意位置返回',
                               self.font_small, COLORS['text_secondary'],
                               (WINDOW_WIDTH // 2, WINDOW_HEIGHT - s(50)),
                               self.water_offset, speed=4)