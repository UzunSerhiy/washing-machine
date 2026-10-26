"""Read-only adapter from a drive's telemetry to AUTO roller motion.

The caller owns sensor freshness and elapsed-time measurement. No drive commands.
"""
from dataclasses import dataclass
import math

from app.services.drives.base import BaseDrive
from app.services.machine.auto.position_loop import AppliedRollerMotion
from app.services.machine.sensors.roller_reference import RollerReferenceState


@dataclass(frozen=True)
class RollerDriveSample:
    frequency_hz: float
    direction: int

    def as_motion(self, *, elapsed_seconds: float, sensor: RollerReferenceState) -> AppliedRollerMotion:
        if not math.isfinite(elapsed_seconds) or elapsed_seconds <= 0:
            raise ValueError("Elapsed seconds must be positive and finite")
        return AppliedRollerMotion(
            elapsed_seconds=elapsed_seconds,
            frequency_hz=self.frequency_hz,
            direction=self.direction,
            sensor=sensor,
        )


def read_roller_drive_sample(drive: BaseDrive) -> RollerDriveSample:
    """Read a single sample. Unknown/failed telemetry must never imply STOP."""
    try:
        fault = drive.get_fault()
        status = drive.get_status()
        frequency = drive.get_frequency()
    except Exception as exc:
        raise RuntimeError("Roller drive telemetry unavailable") from exc

    if not isinstance(fault, int) or isinstance(fault, bool) or fault != 0:
        raise RuntimeError("Roller drive fault or invalid fault telemetry")
    if status not in (1, 2, 3) or isinstance(status, bool):
        raise RuntimeError("Unknown roller drive status")
    if isinstance(frequency, bool) or not isinstance(frequency, (int, float)) or not math.isfinite(frequency) or frequency < 0:
        raise RuntimeError("Invalid roller drive frequency")
    if status == 3 and frequency > 0:
        raise RuntimeError("Stopped drive reports nonzero output frequency")
    return RollerDriveSample(frequency_hz=float(frequency), direction={1: 1, 2: -1, 3: 0}[status])
