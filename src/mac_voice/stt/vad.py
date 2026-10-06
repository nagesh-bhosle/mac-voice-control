"""Simple energy-based VAD stub with a stable interface for hold/PTT modes."""

from __future__ import annotations

import math
import struct


class VadSegment:
    def __init__(self, start: float, end: float) -> None:
        self.start = start
        self.end = end


def frame_energy(frame: bytes, sample_width: int = 2) -> float:
    if not frame:
        return 0.0
    if sample_width == 2:
        count = len(frame) // 2
        samples = struct.unpack("<" + "h" * count, frame[: count * 2])
        if not samples:
            return 0.0
        return math.sqrt(sum(s * s for s in samples) / len(samples)) / 32768.0
    return sum(frame) / (len(frame) * 255.0)


class EnergyVad:
    def __init__(self, threshold: float = 0.02, sample_rate: int = 16000) -> None:
        self.threshold = threshold
        self.sample_rate = sample_rate

    def is_speech(self, frame: bytes) -> bool:
        return frame_energy(frame) > self.threshold

    def segments(self, frames: list[bytes], frame_ms: int = 30) -> list[VadSegment]:
        out: list[VadSegment] = []
        start: int | None = None
        for i, frame in enumerate(frames):
            speech = self.is_speech(frame)
            if speech and start is None:
                start = i
            elif not speech and start is not None:
                out.append(VadSegment(start * frame_ms / 1000.0, i * frame_ms / 1000.0))
                start = None
        if start is not None:
            out.append(VadSegment(start * frame_ms / 1000.0, len(frames) * frame_ms / 1000.0))
        return out
