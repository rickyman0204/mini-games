"""Particle system for celebration and scratch effects"""
import random
import math
import pygame
from pygame.math import Vector2
from src.utils import clamp, hex_to_rgb


class Particle(pygame.sprite.Sprite):
    """Single particle with velocity, gravity, and fade-out"""

    def __init__(self, pos: tuple, velocity: Vector2, color: tuple,
                 lifetime: float, size: int = 4, gravity: float = 200):
        super().__init__()
        self.image = pygame.Surface((size, size), pygame.SRCALPHA)
        self.image.fill((*color, 255))
        self.rect = self.image.get_rect(center=pos)
        self.velocity = velocity
        self.lifetime = lifetime
        self.age = 0
        self.gravity = gravity

    def update(self, dt: float):
        self.age += dt
        self.velocity.y += self.gravity * dt
        self.rect.x += self.velocity.x * dt * 60
        self.rect.y += self.velocity.y * dt * 60

        alpha = max(0, int(255 * (1 - self.age / self.lifetime)))
        self.image.set_alpha(alpha)

        if self.age >= self.lifetime:
            self.kill()


class ParticleEmitter:
    """Manages particle creation and pooling"""

    def __init__(self):
        self.particles = pygame.sprite.Group()

    def emit_burst(self, pos: tuple, count: int, color: tuple,
                   speed_range: tuple = (50, 200), angle_range: tuple = (0, 360),
                   lifetime: float = 1.0, size: int = 4, gravity: float = 200):
        """Emit a burst of particles from a point"""
        for _ in range(count):
            speed = random.uniform(*speed_range)
            angle = random.uniform(*angle_range) * math.pi / 180
            velocity = Vector2(math.cos(angle), math.sin(angle)) * speed
            particle = Particle(pos, velocity, color, lifetime, size, gravity)
            self.particles.add(particle)

    def emit_confetti(self, pos: tuple, count: int, colors: list,
                      speed_range: tuple = (100, 300), lifetime: float = 2.0):
        """Emit colorful confetti particles (upward burst)"""
        for _ in range(count):
            color = random.choice(colors)
            rgb = hex_to_rgb(color) if isinstance(color, str) else color
            speed = random.uniform(*speed_range)
            angle = random.uniform(-80, -100) * math.pi / 180
            velocity = Vector2(random.uniform(-2, 2), -1) * speed * 0.5
            velocity.y = -random.uniform(*speed_range)
            size = random.randint(3, 6)
            particle = Particle(pos, velocity, rgb, lifetime, size, gravity=150)
            self.particles.add(particle)

    def emit_sparkle(self, pos: tuple, count: int, color: tuple, lifetime: float = 0.8):
        """Emit sparkle particles around a point"""
        for _ in range(count):
            angle = random.uniform(0, 360) * math.pi / 180
            distance = random.uniform(10, 40)
            spawn_pos = (pos[0] + math.cos(angle) * distance,
                        pos[1] + math.sin(angle) * distance)
            velocity = Vector2(math.cos(angle) * 20, math.sin(angle) * 20)
            particle = Particle(spawn_pos, velocity, color, lifetime, size=2, gravity=0)
            self.particles.add(particle)

    def update(self, dt: float):
        self.particles.update(dt)

    def draw(self, surface: pygame.Surface):
        self.particles.draw(surface)

    def clear(self):
        self.particles.empty()
