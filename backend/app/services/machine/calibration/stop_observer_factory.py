"""Read-only roller drive telemetry adapter for homing stop confirmation."""
from collections.abc import Callable

from app.services.machine.calibration.stop_confirmation import (
    StopObservation,
    observe_drive_stop,
)
from app.services.machine.machine import Machine


def make_roller_stop_observer(machine: Machine) -> Callable[[], StopObservation]:
    """Use the same physical roller drive instance as machine motion commands."""
    drive = machine.roller.drive

    def observe() -> StopObservation:
        return observe_drive_stop(drive)

    return observe


def make_roller_fault_observer(machine: Machine) -> Callable[[], int]:
    """Read the physical roller VFD fault register during active HOME."""
    drive = machine.roller.drive
    return drive.get_fault
