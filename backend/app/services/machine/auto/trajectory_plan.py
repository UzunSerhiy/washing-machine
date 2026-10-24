"""Pure AUTO stage geometry and position-dependent roller speed planning.

This module does not command drives or water outputs. In particular, the
caller remains responsible for real position feedback, deceleration and stops.
"""
from dataclasses import dataclass

from app.services.machine.operation import AutoStage
from app.services.speed.layer import SpeedLayer
from app.services.winding.calculator import WindingCalculator


@dataclass(frozen=True)
class AutoGeometry:
    washing_stop: float
    material_start: float
    water_start: float
    material_end: float

    def __post_init__(self):
        if not (0 <= self.washing_stop < self.material_start < self.water_start < self.material_end):
            raise ValueError("Invalid AUTO calibration point order")


@dataclass(frozen=True)
class AutoStagePlan:
    stage: AutoStage
    start_turns: float
    stop_turns: float
    direction: int

    @property
    def forward(self) -> bool:
        return self.direction == 1

    def reached_end(self, position_turns: float) -> bool:
        return position_turns >= self.stop_turns if self.forward else position_turns <= self.stop_turns


def stage_plan(stage: AutoStage, geometry: AutoGeometry) -> AutoStagePlan:
    bounds = {
        AutoStage.WINDING: (0.0, geometry.material_end, 1),
        AutoStage.WASHING: (geometry.material_end, geometry.washing_stop, -1),
        AutoStage.DRYING: (geometry.washing_stop, geometry.material_end, 1),
        AutoStage.UNWINDING: (geometry.material_end, 0.0, -1),
    }
    return AutoStagePlan(stage, *bounds[stage])


def frequency_at_position(
    position_turns: float,
    speed_percent: float,
    geometry: AutoGeometry,
    calculator: WindingCalculator,
    speed_layer: SpeedLayer,
) -> float:
    """Operator speed outside material; scaled winding curve inside.

    The winding calculator is stateful, so use a stage-local instance.
    """
    if not 0 < speed_percent <= 100:
        raise ValueError("Speed percent must be greater than 0 and no more than 100")
    if position_turns < 0 or position_turns > geometry.material_end:
        raise ValueError("Position outside calibrated AUTO travel")
    if position_turns <= geometry.material_start:
        return speed_layer.belt_frequency(speed_percent)
    calculator.set_turns(position_turns - geometry.material_start)
    return calculator.frequency_hz(speed_percent)


def water_required(stage: AutoStage, position_turns: float, geometry: AutoGeometry) -> bool:
    """Desired water state *while running*; caller forces OFF otherwise."""
    if stage == AutoStage.WASHING:
        return position_turns > geometry.washing_stop
    if stage == AutoStage.DRYING:
        return position_turns < geometry.water_start
    return False
