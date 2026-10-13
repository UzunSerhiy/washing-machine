from dataclasses import dataclass


@dataclass(frozen=True)
class DriveStatus:
    connected: bool
    faulted: bool
    running: bool
    frequency_hz: float


@dataclass(frozen=True)
class MachineDrivesStatus:
    roller: DriveStatus
    brushes: DriveStatus
