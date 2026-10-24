"""Estimated roller position, corrected by one physical pulse per revolution.

Pure calculation only: no motor commands and no hardware safety guarantee.
Call ``home`` only after successful physical HOME, then ``advance`` once per
control tick with a fresh sensor state and the applied motor frequency.
"""
from dataclasses import dataclass
from math import isfinite

from app.services.machine.sensors.roller_reference import RollerReferenceState
from app.services.winding.rotation import RollerRotationCalculator


@dataclass(frozen=True)
class RollerPositionSnapshot:
    position_turns: float
    estimated_rpm: float
    pulse_count_since_home: int
    valid: bool


class RollerPositionService:
    def __init__(self, rotation: RollerRotationCalculator) -> None:
        self._rotation = rotation
        self._valid = False
        self._position = 0.0
        self._rpm = 0.0
        self._pulse_count = 0
        self._last_pulses = 0
        self._generation = 0

    def home(self, sensor: RollerReferenceState) -> None:
        """Anchor the position at Point 0 after homing is verified elsewhere."""
        if not sensor.connected or not sensor.triggered:
            raise RuntimeError("HOME requires an active connected reference sensor")
        self._position = 0.0
        self._rpm = 0.0
        self._pulse_count = 0
        self._last_pulses = sensor.pulses
        self._generation = sensor.generation
        self._valid = True

    def invalidate(self) -> None:
        self._valid = False
        self._rpm = 0.0

    @property
    def snapshot(self) -> RollerPositionSnapshot:
        return RollerPositionSnapshot(
            position_turns=self._position,
            estimated_rpm=self._rpm,
            pulse_count_since_home=self._pulse_count,
            valid=self._valid,
        )

    def advance(
        self,
        *,
        elapsed_seconds: float,
        frequency_hz: float,
        direction: int,
        sensor: RollerReferenceState,
    ) -> RollerPositionSnapshot:
        """Direction: +1 forward, -1 reverse, 0 stopped.

        A pulse fixes the position to an integer turn relative to the HOME
        reference. Polling latency and acceleration can introduce error.
        """
        if not isfinite(elapsed_seconds) or elapsed_seconds < 0:
            raise ValueError("elapsed_seconds must be finite and nonnegative")
        if not isfinite(frequency_hz) or frequency_hz < 0:
            raise ValueError("frequency_hz must be finite and nonnegative")
        if direction not in (-1, 0, 1):
            raise ValueError("direction must be -1, 0, or 1")
        if not self._valid:
            raise RuntimeError("Roller position is not referenced; HOME required")
        if (not sensor.connected or sensor.generation != self._generation
                or sensor.pulses < self._last_pulses):
            self.invalidate()
            raise RuntimeError("Sensor disconnected, rebooted, or counter reset; HOME required")

        delta_pulses = sensor.pulses - self._last_pulses
        rpm = self._rotation.roller_rpm(frequency_hz) if direction else 0.0
        estimated = self._position + direction * rpm * elapsed_seconds / 60.0

        if delta_pulses:
            if direction == 0 or frequency_hz == 0:
                self.invalidate()
                raise RuntimeError("Pulse while drive is reported stopped; position uncertain")
            # Count all observed pulses, including those between poll cycles.
            self._pulse_count += direction * delta_pulses
            self._position = float(self._pulse_count)
        else:
            self._position = estimated

        self._last_pulses = sensor.pulses
        self._rpm = direction * rpm
        return self.snapshot
