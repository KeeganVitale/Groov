from __future__ import annotations

from collections import deque

from PySide6.QtCore import QObject, Signal


class SpectrumAnalyzer(QObject):
    spectrum_ready = Signal(list)

    def __init__(self, bands: int = 128) -> None:
        super().__init__()
        self._bands = bands
        self._gain = 1.9
        self._noise_floor = 0.09
        self._curve = 2.35
        self._history: deque[list[float]] = deque(maxlen=3)

    @property
    def bands(self) -> int:
        return self._bands

    def update_from_magnitudes(self, magnitudes: list[float]) -> None:
        if not magnitudes:
            values = [0.0] * self._bands
        elif len(magnitudes) == self._bands:
            values = [self._apply_gain_shape(self._db_to_norm(v)) for v in magnitudes]
        else:
            values = self._resample(magnitudes, self._bands)

        self._history.append(values)
        smoothed = [sum(col) / len(col) for col in zip(*self._history)]
        self.spectrum_ready.emit(smoothed)

    @staticmethod
    def _db_to_norm(db_val: float) -> float:
        # Clamp typical spectrum range into [0..1]
        if db_val <= -90.0:
            return 0.0
        if db_val >= 0.0:
            return 1.0
        return (db_val + 90.0) / 90.0

    def _resample(self, values: list[float], target: int) -> list[float]:
        if not values:
            return [0.0] * target

        out: list[float] = []
        n = len(values)
        for i in range(target):
            idx = int((i / max(target - 1, 1)) * (n - 1))
            out.append(self._apply_gain_shape(self._db_to_norm(values[idx])))
        return out

    def _apply_gain_shape(self, level: float) -> float:
        level = max(0.0, min(1.0, level))
        # Keep very low-level noise near zero so bars start lower.
        level = max(0.0, (level - self._noise_floor) / (1.0 - self._noise_floor))
        level = level ** self._curve
        return max(0.0, min(1.0, level * self._gain))
