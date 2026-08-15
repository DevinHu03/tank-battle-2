"""Synthesised arcade sounds with a silent fallback for unsupported devices."""

from __future__ import annotations

from array import array
import math

import pygame


class AudioManager:
    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self.sounds: dict[str, pygame.mixer.Sound] = {}
        self.music: pygame.mixer.Sound | None = None
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=22050, size=-16, channels=1)
            self.sounds = {
                "fire": self._tone(440, 0.06, 0.28), "hit": self._tone(180, 0.08, 0.22),
                "explode": self._tone(90, 0.18, 0.35), "pickup": self._tone(780, 0.12, 0.25),
                "wave": self._tone(520, 0.16, 0.25), "victory": self._tone(880, 0.22, 0.3),
                "defeat": self._tone(120, 0.25, 0.28), "warning": self._tone(300, 0.09, 0.25),
            }
            self.music = self._music_loop()
        except pygame.error:
            self.enabled = False

    def _tone(self, frequency: float, seconds: float, volume: float) -> pygame.mixer.Sound:
        rate = 22050
        samples = array("h", (int(32767 * volume * math.sin(2 * math.pi * frequency * i / rate) * (1 - i / (rate * seconds))) for i in range(int(rate * seconds))))
        return pygame.mixer.Sound(buffer=samples.tobytes())

    def _music_loop(self) -> pygame.mixer.Sound:
        """A restrained looping two-note pulse beneath the effects."""
        rate, seconds = 22050, 4
        notes = (110, 146.83, 98, 130.81)
        samples = array("h")
        for index in range(rate * seconds):
            phase = index / rate
            note = notes[min(3, int(phase))]
            pulse = 0.5 + 0.5 * math.sin(2 * math.pi * 2 * phase)
            value = math.sin(2 * math.pi * note * phase) * 0.06 * pulse
            samples.append(int(32767 * value))
        return pygame.mixer.Sound(buffer=samples.tobytes())

    def start_music(self) -> None:
        if self.enabled and self.music:
            self.music.play(loops=-1)

    def play(self, name: str) -> None:
        if self.enabled and name in self.sounds:
            self.sounds[name].play()

    def toggle(self) -> bool:
        self.enabled = not self.enabled
        if self.enabled:
            pygame.mixer.unpause()
        else:
            pygame.mixer.pause()
        return self.enabled
