"""Position-based AUTO stage controller (no hardware outputs).

Position is estimated from commanded frequency, not measured encoder feedback.
The caller must handle stop ramps, physical interlocks and water output.
"""
from app.services.machine.auto.trajectory_plan import (
    AutoGeometry, frequency_at_position, stage_plan, water_required,
)
from app.services.machine.operation import AutoStage
from app.services.speed.layer import SpeedLayer
from app.services.winding.calculator import WindingCalculator
from app.services.winding.rotation import RollerRotationCalculator


class AutoStageController:
    def __init__(self, stage: AutoStage, geometry: AutoGeometry,
                 speed_percent: float, position_turns: float,
                 winding_calculator: WindingCalculator,
                 rotation_calculator: RollerRotationCalculator,
                 speed_layer: SpeedLayer):
        self.plan = stage_plan(stage, geometry)
        if not 0 < speed_percent <= 100:
            raise ValueError('Invalid AUTO speed percent')
        if not 0 <= position_turns <= geometry.material_end:
            raise ValueError('Position outside calibrated travel')
        if abs(position_turns - self.plan.start_turns) > 1e-6:
            raise ValueError('Stage start does not match current position')
        self.geometry = geometry
        self.speed_percent = speed_percent
        self.position_turns = position_turns
        self.winding_calculator = winding_calculator
        self.rotation_calculator = rotation_calculator
        self.speed_layer = speed_layer
        self.completed = False

    @property
    def stage(self) -> AutoStage:
        return self.plan.stage

    @property
    def frequency_hz(self) -> float:
        return frequency_at_position(self.position_turns, self.speed_percent,
                                     self.geometry, self.winding_calculator,
                                     self.speed_layer)

    @property
    def water_on(self) -> bool:
        return not self.completed and water_required(self.stage, self.position_turns, self.geometry)

    def observe_position(self, position_turns: float) -> None:
        """Update stage progress from an external position estimator.

        Unlike advance(), this does not integrate commanded frequency. The
        observed position is not clamped to the stage target: any overshoot
        remains visible to the caller for diagnostics and safety handling.
        Completion means the target was crossed in the expected direction,
        NOT that the physical roller has stopped.
        """
        from math import isfinite

        if not isfinite(position_turns):
            raise ValueError("Observed position must be finite")
        if not 0 <= position_turns <= self.geometry.material_end:
            raise ValueError("Observed position outside calibrated travel")
        if self.completed:
            # Do not silently accept motion after completion.
            if abs(position_turns - self.position_turns) > 1e-6:
                raise RuntimeError("Roller moved after stage completion")
            return
        self.position_turns = position_turns
        if self.plan.reached_end(position_turns):
            self.completed = True

    def advance(self, elapsed_seconds: float) -> None:
        if elapsed_seconds < 0:
            raise ValueError('Elapsed time cannot be negative')
        if self.completed or elapsed_seconds == 0:
            return
        delta = self.rotation_calculator.revolutions_for_time(
            self.frequency_hz, elapsed_seconds)
        target = self.plan.stop_turns
        next_position = self.position_turns + self.plan.direction * delta
        if self.plan.forward:
            self.position_turns = min(next_position, target)
        else:
            self.position_turns = max(next_position, target)
        if self.plan.reached_end(self.position_turns):
            self.position_turns = target
            self.completed = True
