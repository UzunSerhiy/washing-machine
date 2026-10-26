"""Read-only confirmation of a stopped roller VFD.

This module does not issue motion commands or bypass REAL-mode interlocks.
A stopped VFD output is not proof that a mechanically driven shaft is stationary.
"""
from dataclasses import dataclass
import math

from app.services.drives.base import BaseDrive


@dataclass(frozen=True)
class StopObservation:
    status: int
    frequency_hz: float
    fault: int
    confirmed: bool


def observe_drive_stop(drive: BaseDrive, *, frequency_tolerance_hz: float = 0.0) -> StopObservation:
    """Fail closed on missing, invalid, or inconsistent Modbus telemetry.

    status=3 is the existing project's stopped-status convention.
    This is only one observation; callers must also check mechanical stopping.
    """
    if not isinstance(frequency_tolerance_hz, (float, int)) or isinstance(frequency_tolerance_hz, bool) or not math.isfinite(frequency_tolerance_hz) or frequency_tolerance_hz < 0:
        raise ValueError("Invalid frequency tolerance")
    try:
        fault = drive.get_fault()
        status = drive.get_status()
        frequency = drive.get_frequency()
    except Exception as exc:
        raise RuntimeError("Roller VFD stop telemetry unavailable") from exc
    if isinstance(fault, bool) or not isinstance(fault, int) or fault < 0:
        raise RuntimeError("Invalid roller VFD fault value")
    if isinstance(status, bool) or not isinstance(status, int) or status not in (1, 2, 3):
        raise RuntimeError("Invalid roller VFD status")
    if isinstance(frequency, bool) or not isinstance(frequency, (int, float)) or not math.isfinite(frequency) or frequency < 0:
        raise RuntimeError("Invalid roller VFD frequency")
    return StopObservation(
        status=status,
        frequency_hz=float(frequency),
        fault=fault,
        confirmed=(fault == 0 and status == 3 and frequency <= frequency_tolerance_hz),
    )
