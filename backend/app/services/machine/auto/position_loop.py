"""Pure orchestration of pulse-corrected position and AUTO stage planning.

No drive/water outputs. The caller supplies the frequency and direction actually
applied during the *elapsed* interval, not the next requested frequency.
"""
from dataclasses import dataclass

from app.services.machine.auto.stage_controller import AutoStageController
from app.services.machine.position.roller_position_service import (
    RollerPositionService, RollerPositionSnapshot,
)
from app.services.machine.sensors.roller_reference import RollerReferenceState


@dataclass(frozen=True)
class AppliedRollerMotion:
    """Observed inputs for the interval that has already elapsed.

    frequency_hz is the applied (not requested) frequency. Direction is
    +1 forward, -1 reverse, or 0 stopped. Sensor is a fresh counter reading.
    """

    elapsed_seconds: float
    frequency_hz: float
    direction: int
    sensor: RollerReferenceState


@dataclass(frozen=True)
class AutoPositionTick:
    position: RollerPositionSnapshot
    next_frequency_hz: float
    completed: bool
    water_requested: bool


class AutoPositionLoop:
    def __init__(self, position: RollerPositionService, stage: AutoStageController):
        if not position.snapshot.valid:
            raise RuntimeError("Position must be HOME referenced")
        if abs(position.snapshot.position_turns - stage.position_turns) > 1e-6:
            raise ValueError("AUTO stage and position estimator disagree")
        self.position = position
        self.stage = stage

    def tick_applied_motion(self, motion: AppliedRollerMotion) -> AutoPositionTick:
        """Consume one completed interval; never infer applied Hz from a setpoint."""
        return self.tick(
            elapsed_seconds=motion.elapsed_seconds,
            applied_frequency_hz=motion.frequency_hz,
            applied_direction=motion.direction,
            sensor=motion.sensor,
        )

    def tick(self, *, elapsed_seconds: float, applied_frequency_hz: float,
             applied_direction: int, sensor: RollerReferenceState) -> AutoPositionTick:
        # Update position exactly once. Never call stage.advance() in this path.
        snapshot = self.position.advance(
            elapsed_seconds=elapsed_seconds,
            frequency_hz=applied_frequency_hz,
            direction=applied_direction,
            sensor=sensor,
        )
        try:
            self.stage.observe_position(snapshot.position_turns)
        except (ValueError, RuntimeError):
            # A rejected coordinate cannot be trusted for subsequent AUTO ticks.
            self.position.invalidate()
            raise
        return AutoPositionTick(
            position=snapshot,
            next_frequency_hz=0.0 if self.stage.completed else self.stage.frequency_hz,
            completed=self.stage.completed,
            water_requested=self.stage.water_on,
        )
