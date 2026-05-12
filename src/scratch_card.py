"""Scratch card component with scratch detection and reveal animation"""
import pygame
from src.settings import (
    COLORS, CARD_WIDTH, CARD_HEIGHT, SCRATCH_THRESHOLD,
    ANIMATION_DURATION, PRIZES
)
from src.utils import ease_out_back, clamp


class ScratchCard:
    """A single scratch card that the player can scratch with mouse"""

    def __init__(self, x: int, y: int, prize_key: str, index: int = 0):
        self.rect = pygame.Rect(x, y, CARD_WIDTH, CARD_HEIGHT)
        self.prize_key = prize_key
        self.index = index
        self.prize_data = PRIZES[prize_key]

        # Scratch state
        self.scratched = False
        self.reveal_scale = 0.0
        self.is_revealing = False
        self.reveal_timer = 0.0
        self.is_scratching = False

        # Scratch mask (track which pixels are scratched)
        self.mask_surface = pygame.Surface((CARD_WIDTH, CARD_HEIGHT), pygame.SRCALPHA)
        self.mask_surface.fill((255, 255, 255, 255))  # Fully white = not scratched

        # Pre-built surfaces
        self.card_surface = self._create_card_surface()
        self.scratch_surface = self._create_scratch_layer()

        # For scratch ratio caching
        self.last_ratio_check = 0
        self.ratio_check_interval = 5  # frames between ratio checks
        self.frame_count = 0

    def _create_card_surface(self) -> pygame.Surface:
        """Create the base card with prize drawn on it"""
        surface = pygame.Surface((CARD_WIDTH, CARD_HEIGHT), pygame.SRCALPHA)

        # Card background
        surface.fill(hex_to_rgb(COLORS['card_bg']))

        # Card border
        pygame.draw.rect(surface, hex_to_rgb(COLORS['card_border']),
                        surface.get_rect(), width=3, border_radius=12)

        # Inner background
        inner_rect = surface.get_rect().inflate(-6, -6)
        pygame.draw.rect(surface, (20, 10, 10), inner_rect, border_radius=8)

        # Draw prize icon
        prize_center = (CARD_WIDTH // 2, CARD_HEIGHT // 2 - 10)
        self._draw_prize_icon(surface, prize_center)

        # Prize name
        font = pygame.font.SysFont('microsoftyahei', 28, bold=True)
        name_text = self.prize_data['name']
        name_color = hex_to_rgb(self.prize_data['color'])
        name_surf = font.render(name_text, True, name_color)
        name_rect = name_surf.get_rect(center=(CARD_WIDTH // 2, CARD_HEIGHT - 50))
        surface.blit(name_surf, name_rect)

        return surface

    def _draw_prize_icon(self, surface: pygame.Surface, center: tuple):
        """Draw the prize icon based on prize type"""
        color = hex_to_rgb(self.prize_data['color'])
        accent = hex_to_rgb(self.prize_data['accent_color'])
        card_bg = hex_to_rgb(COLORS['card_bg'])

        if self.prize_key == 'gold':
            # Gold coin - large circle with shine
            pygame.draw.circle(surface, color, center, 40)
            pygame.draw.circle(surface, accent, center, 35, 3)
            # Shine highlight
            pygame.draw.circle(surface, (255, 255, 200), (center[0] - 12, center[1] - 12), 8)
            # Inner decorative circle
            pygame.draw.circle(surface, accent, center, 25, 2)
            # Character
            font = pygame.font.SysFont('microsoftyahei', 24, bold=True)
            char = font.render('金', True, accent)
            surface.blit(char, char.get_rect(center=center))

        elif self.prize_key == 'banknote':
            # Banknote - green rectangle
            rect_w, rect_h = 100, 50
            rect = pygame.Rect(center[0] - rect_w // 2, center[1] - rect_h // 2, rect_w, rect_h)
            pygame.draw.rect(surface, color, rect, border_radius=6)
            pygame.draw.rect(surface, accent, rect, width=2, border_radius=6)
            # Inner border
            inner = rect.inflate(-8, -8)
            pygame.draw.rect(surface, accent, inner, width=1, border_radius=4)
            # Corner decorations
            pygame.draw.circle(surface, accent, (rect.left + 10, rect.top + 10), 5, 1)
            pygame.draw.circle(surface, accent, (rect.right - 10, rect.bottom - 10), 5, 1)
            # Character
            font = pygame.font.SysFont('microsoftyahei', 20, bold=True)
            char = font.render('钱币', True, accent)
            surface.blit(char, char.get_rect(center=center))

        elif self.prize_key == 'coin':
            # Silver coin
            pygame.draw.circle(surface, color, center, 35)
            pygame.draw.circle(surface, accent, center, 30, 3)
            # Shine highlight
            pygame.draw.circle(surface, (200, 200, 220), (center[0] - 10, center[1] - 10), 6)
            # Inner circle with hole (like ancient Chinese coin)
            pygame.draw.circle(surface, accent, center, 20, 2)
            pygame.draw.circle(surface, card_bg, center, 10)
            # Character
            font = pygame.font.SysFont('microsoftyahei', 18, bold=True)
            char = font.render('硬', True, accent)
            surface.blit(char, char.get_rect(center=center))

    def _create_scratch_layer(self) -> pygame.Surface:
        """Create the scratch-off layer with decorative pattern"""
        surface = pygame.Surface((CARD_WIDTH, CARD_HEIGHT), pygame.SRCALPHA)

        # Gold scratch layer
        surface.fill(hex_to_rgb(COLORS['scratch_layer']))

        # Decorative diamond pattern
        pattern_color = (180, 140, 80, 60)
        for y in range(0, CARD_HEIGHT, 20):
            for x in range(0, CARD_WIDTH, 20):
                offset_x = 10 if (y // 20) % 2 else 0
                pygame.draw.circle(surface, pattern_color,
                                 (x + offset_x, y), 3)

        # "刮这里" text
        font = pygame.font.SysFont('microsoftyahei', 24, bold=True)
        text = font.render('刮这里', True, (200, 170, 120))
        text_rect = text.get_rect(center=(CARD_WIDTH // 2, CARD_HEIGHT // 2))
        surface.blit(text, text_rect)

        # Border
        pygame.draw.rect(surface, hex_to_rgb(COLORS['gold_dark']),
                        surface.get_rect(), width=2, border_radius=12)

        return surface

    def handle_mouse(self, mouse_pos: tuple, mouse_pressed: bool):
        """Handle mouse input for scratching"""
        if self.scratched or not mouse_pressed:
            return

        # Check if mouse is over card
        local_x = mouse_pos[0] - self.rect.x
        local_y = mouse_pos[1] - self.rect.y

        if 0 <= local_x <= CARD_WIDTH and 0 <= local_y <= CARD_HEIGHT:
            self.is_scratching = True
            radius = 20
            # Draw transparent circles to "erase" the scratch layer
            pygame.draw.circle(self.mask_surface, (0, 0, 0, 0), (local_x, local_y), radius)
        else:
            self.is_scratching = False

    def get_scratch_ratio(self) -> float:
        """Calculate how much of the card has been scratched by sampling pixels"""
        total = 0
        scratched = 0
        step = 4

        for y in range(0, CARD_HEIGHT, step):
            for x in range(0, CARD_WIDTH, step):
                total += 1
                pixel = self.mask_surface.get_at((x, y))
                if pixel[3] < 128:
                    scratched += 1

        return scratched / total if total > 0 else 0

    def update(self, dt: float):
        """Update card state"""
        self.frame_count += 1

        # Check if enough has been scratched
        if not self.scratched and not self.is_revealing:
            if self.frame_count % self.ratio_check_interval == 0:
                ratio = self.get_scratch_ratio()
                if ratio >= SCRATCH_THRESHOLD:
                    self.is_revealing = True
                    self.reveal_timer = 0.0

        # Reveal animation
        if self.is_revealing:
            self.reveal_timer += dt
            progress = clamp(self.reveal_timer / ANIMATION_DURATION, 0, 1)
            self.reveal_scale = ease_out_back(progress)

            if progress >= 1.0:
                self.is_revealing = False
                self.scratched = True
                self.reveal_scale = 1.0

    def draw(self, surface: pygame.Surface):
        """Draw the card with refined visuals"""
        if self.scratched:
            shadow = pygame.Surface((self.rect.width + 6, self.rect.height + 6), pygame.SRCALPHA)
            shadow.fill((0, 0, 0, 60))
            surface.blit(shadow, (self.rect.x - 3, self.rect.y + 3))
            surface.blit(self.card_surface, self.rect)
        elif self.is_revealing:
            composite = self.scratch_surface.copy()
            composite.blit(self.mask_surface, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            surface.blit(composite, self.rect)
            prize_alpha = int(255 * self.reveal_scale)
            prize_copy = self.card_surface.copy()
            prize_copy.set_alpha(prize_alpha)
            surface.blit(prize_copy, self.rect)
        else:
            composite = self.scratch_surface.copy()
            composite.blit(self.mask_surface, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            composite_rect = composite.get_rect(topleft=self.rect.topleft)
            shadow = pygame.Surface((composite_rect.width + 6, composite_rect.height + 6), pygame.SRCALPHA)
            shadow.fill((0, 0, 0, 40))
            surface.blit(shadow, (composite_rect.x - 3, composite_rect.y + 3))
            surface.blit(composite, composite_rect)


def hex_to_rgb(hex_color: str) -> tuple:
    return (int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16))
