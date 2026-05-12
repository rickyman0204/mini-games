"""Audio system - generate fanfare and ambient sounds programmatically"""
import pygame
import math
import numpy as np


def generate_tone(frequency: float, duration: float, volume: float = 0.5,
                  sample_rate: int = 44100) -> pygame.mixer.Sound:
    """Generate a simple sine wave tone"""
    n_samples = int(sample_rate * duration)
    t = np.linspace(0, duration, n_samples, False)
    # Sine wave with envelope (fade in/out)
    envelope = np.ones(n_samples)
    fade_samples = int(sample_rate * 0.02)  # 20ms fade
    if fade_samples < n_samples // 2:
        envelope[:fade_samples] = np.linspace(0, 1, fade_samples)
        envelope[-fade_samples:] = np.linspace(1, 0, fade_samples)
    wave = np.sin(2 * math.pi * frequency * t) * envelope * volume
    # Convert to 16-bit int
    audio = (wave * 32767).astype(np.int16)
    buffer = audio.tobytes()
    return pygame.mixer.Sound(buffer)


def generate_chord(frequencies: list, duration: float, volume: float = 0.3,
                   sample_rate: int = 44100) -> pygame.mixer.Sound:
    """Generate a chord (multiple frequencies combined)"""
    n_samples = int(sample_rate * duration)
    t = np.linspace(0, duration, n_samples, False)
    envelope = np.ones(n_samples)
    fade_samples = int(sample_rate * 0.03)
    if fade_samples < n_samples // 2:
        envelope[:fade_samples] = np.linspace(0, 1, fade_samples)
        envelope[-fade_samples:] = np.linspace(1, 0, fade_samples)

    combined = np.zeros(n_samples)
    for freq in frequencies:
        combined += np.sin(2 * math.pi * freq * t)
    # Normalize
    max_val = np.max(np.abs(combined))
    if max_val > 0:
        combined = combined / max_val * volume
    audio = (combined * 32767).astype(np.int16)
    buffer = audio.tobytes()
    return pygame.mixer.Sound(buffer)


class Fanfare:
    """Generate a celebratory fanfare sound"""

    def __init__(self):
        self.sounds: list[pygame.mixer.Sound] = []
        self.current_channel = None

    def play(self):
        """Play the fanfare melody - "Congratulations" style"""
        # Stop any previous fanfare
        self.stop()

        # Melody notes (frequency, start_time, duration)
        # A bright ascending melody
        notes = [
            # Note 1: C5
            (523.25, 0.0, 0.3),
            # Note 2: E5
            (659.25, 0.3, 0.3),
            # Note 3: G5
            (783.99, 0.6, 0.3),
            # Note 4: C6 (high!)
            (1046.50, 0.9, 0.6),
            # Note 5: B5
            (987.77, 1.5, 0.4),
            # Note 6: C6 hold
            (1046.50, 1.9, 0.8),
        ]

        # Play each note
        self.sounds = []
        for freq, start_time, duration in notes:
            tone = generate_tone(freq, duration, volume=0.3)
            channel = pygame.mixer.find_channel(True)
            channel.play(tone, delay=int(start_time * 1000))
            self.sounds.append(tone)

        # Add a chord at the end for fullness
        chord = generate_chord([523.25, 659.25, 783.99], 1.0, volume=0.2)
        channel = pygame.mixer.find_channel(True)
        channel.play(chord, delay=int(1.9 * 1000))
        self.sounds.append(chord)

    def stop(self):
        """Stop all fanfare sounds"""
        pygame.mixer.stop()
        self.sounds.clear()


def generate_ambient_hum(duration: float = 3.0) -> pygame.mixer.Sound:
    """Generate a soft ambient background hum for the black screen transition"""
    n_samples = int(44100 * duration)
    t = np.linspace(0, duration, n_samples, False)
    # Low drone with slight modulation
    wave = (
        np.sin(2 * math.pi * 110 * t) * 0.3 +
        np.sin(2 * math.pi * 165 * t) * 0.15 +
        np.sin(2 * math.pi * 220 * t) * 0.1
    )
    # Apply envelope
    fade_samples = int(44100 * 0.5)
    envelope = np.ones(n_samples)
    if fade_samples < n_samples // 2:
        envelope[:fade_samples] = np.linspace(0, 1, fade_samples)
        envelope[-fade_samples:] = np.linspace(1, 0, fade_samples)
    wave *= envelope * 0.2

    audio = (wave * 32767).astype(np.int16)
    buffer = audio.tobytes()
    return pygame.mixer.Sound(buffer)
