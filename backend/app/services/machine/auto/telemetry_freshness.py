"""Validate timing of read-only REAL AUTO diagnostics before using them for motion.

A connected sensor with unchanged pulse count can be a stationary roller;
that is not by itself evidence of stale communication.
"""
from dataclasses import dataclass
import math
from typing import Callable

from app.services.machine.auto.real_diagnostics import RealAutoDiagnostics, read_real_auto_diagnostics


@dataclass(frozen=True)
class TimedAutoDiagnostics:
    diagnostics: RealAutoDiagnostics
    started_at: float
    completed_at: float

    def validate(self, *, now: float, max_age_seconds: float, max_read_seconds: float) -> None:
        values = (self.started_at, self.completed_at, now, max_age_seconds, max_read_seconds)
        if any(not isinstance(x, (int, float)) or isinstance(x, bool) or not math.isfinite(x) for x in values):
            raise ValueError("Diagnostic timing values must be finite numbers")
        if max_age_seconds <= 0 or max_read_seconds <= 0:
            raise ValueError("Diagnostic timing limits must be positive")
        if not self.started_at <= self.completed_at <= now:
            raise RuntimeError("Invalid diagnostic timestamp order")
        if self.completed_at - self.started_at > max_read_seconds:
            raise RuntimeError("Diagnostic read took too long")
        # Age from the start, since drive, sensor and IO are sampled sequentially.
        if now - self.started_at > max_age_seconds:
            raise RuntimeError("Diagnostic snapshot is stale")


def read_timed_auto_diagnostics(*, roller_drive, roller_sensor, io_controller, clock: Callable[[], float]) -> TimedAutoDiagnostics:
    """Read devices without writing outputs; caller validates timing before use."""
    started_at = clock()
    diagnostics = read_real_auto_diagnostics(
        roller_drive=roller_drive, roller_sensor=roller_sensor, io_controller=io_controller
    )
    completed_at = clock()
    return TimedAutoDiagnostics(diagnostics, started_at, completed_at)
