"""Read-only diagnostic snapshot for REAL AUTO integration."""
from dataclasses import dataclass
from typing import Any

from app.services.machine.auto.drive_motion import RollerDriveSample, read_roller_drive_sample
from app.services.machine.sensors.roller_reference import RollerReferenceState


@dataclass(frozen=True)
class RealAutoDiagnostics:
    roller: RollerDriveSample
    reference: RollerReferenceState
    io: dict[str, Any]


def read_real_auto_diagnostics(*, roller_drive, roller_sensor, io_controller) -> RealAutoDiagnostics:
    """Observe devices only; never change drive commands or relay outputs."""
    roller = read_roller_drive_sample(roller_drive)
    reference = roller_sensor.get_state()
    if not isinstance(reference, RollerReferenceState) or not reference.connected:
        raise RuntimeError("Roller reference sensor unavailable")
    io = io_controller.status()
    if not isinstance(io, dict):
        raise RuntimeError("Invalid IO diagnostic response")
    return RealAutoDiagnostics(roller=roller, reference=reference, io=dict(io))
