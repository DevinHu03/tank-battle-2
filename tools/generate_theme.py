"""Generate the original low-fi arcade theme used by the game."""
from __future__ import annotations

from array import array
import math
from pathlib import Path
import random
import wave


RATE = 22050
TEMPO = 132
BEAT = 60 / TEMPO
DURATION = BEAT * 4 * 8
ROOTS = (82.41, 82.41, 98.00, 110.00, 73.42, 73.42, 87.31, 98.00)
LEAD = (329.63, 392.00, 493.88, 587.33, 493.88, 392.00, 329.63, 293.66)


def square(phase: float) -> float:
    return 1.0 if phase % 1.0 < 0.5 else -1.0


def make_theme() -> array:
    rng = random.Random(1984)
    samples = array("h")
    for index in range(int(RATE * DURATION)):
        time = index / RATE
        beat_index = int(time / BEAT)
        eighth_index = int(time / (BEAT / 2))
        bar = beat_index // 4
        within_beat = time % BEAT
        value = 0.0

        # Pulsing square-wave bass, alternating roots for a defensive march.
        bass = ROOTS[bar % len(ROOTS)]
        value += square(time * bass) * 0.16
        value += square(time * bass * 2) * 0.055

        # Short arpeggio with a deliberately crunchy envelope.
        note = LEAD[eighth_index % len(LEAD)]
        envelope = max(0.0, 1.0 - (time % (BEAT / 2)) / (BEAT / 2))
        value += square(time * note) * 0.13 * envelope

        # Kick on every quarter note, snare on beats 2 and 4, hats on eighths.
        if within_beat < 0.16:
            value += math.sin(2 * math.pi * (95 - 48 * within_beat / 0.16) * time) * (0.34 * (1 - within_beat / 0.16))
        if beat_index % 4 in (1, 3) and within_beat < 0.13:
            value += (rng.random() * 2 - 1) * (0.22 * (1 - within_beat / 0.13))
        if eighth_index % 2 == 1 and time % (BEAT / 2) < 0.035:
            value += (rng.random() * 2 - 1) * 0.055

        value = max(-0.92, min(0.92, value))
        samples.append(int(value * 32767))
    return samples


def main() -> None:
    output = Path(__file__).resolve().parent.parent / "assets" / "music" / "steel_frontline_theme.wav"
    output.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output), "wb") as stream:
        stream.setnchannels(1); stream.setsampwidth(2); stream.setframerate(RATE)
        stream.writeframes(make_theme().tobytes())


if __name__ == "__main__": main()
