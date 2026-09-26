from enum import Enum

from app.services.machine.calibration.winding import WindingCalibration
from app.services.machine.calibration.points import CalibrationPoint


class WindingPhase(str, Enum):
    BELTS = "belts"
    MATERIAL = "material"
    MATERIAL_WOUND = "material_wound"


class WindingTrajectory:
    def __init__(self, calibration: WindingCalibration):
        self.calibration = calibration

    def phase_at(self, position_turns: float) -> WindingPhase:
        self.calibration.validate()

        if position_turns < self._require_calibration_value(
            self.calibration.belt_start_turns
        ):
            return WindingPhase.BELTS

        if position_turns < self._require_calibration_value(
            self.calibration.material_wound_turns
        ):
            return WindingPhase.MATERIAL

        return WindingPhase.MATERIAL_WOUND

    def next_point_at(
        self,
        position_turns: float,
    ) -> CalibrationPoint | None:
        self.calibration.validate()

        if position_turns < self._require_calibration_value(
            self.calibration.belt_start_turns
        ):
            return CalibrationPoint.WINDING_BELT_START

        if position_turns < self._require_calibration_value(
            self.calibration.material_wound_turns
        ):
            return CalibrationPoint.WINDING_MATERIAL_WOUND

        return None

    @staticmethod
    def _require_calibration_value(calibration: float | None) -> float:
        if calibration is None:
            raise RuntimeError("Winding calibration is incomplete")

        return calibration
