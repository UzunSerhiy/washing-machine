from enum import Enum

from app.services.machine.calibration.washing import WashingCalibration


class WashingPhase(str, Enum):
    MATERIAL = "material"
    BELTS = "belts"
    BELT_SAFE = "belt_safe"


class WashingTrajectory:
    def __init__(self, calibration: WashingCalibration):
        self.calibration = calibration

    def phase_at(self, position_turns: float) -> WashingPhase:
        self.calibration.validate()

        if position_turns > self._require_calibration_value(
            self.calibration.material_reaches_brushes_turns
        ):
            return WashingPhase.MATERIAL

        if position_turns > self._require_calibration_value(
            self.calibration.belt_safe_turns
        ):
            return WashingPhase.BELTS

        return WashingPhase.BELT_SAFE

    @staticmethod
    def _require_calibration_value(calibration: float | None) -> float:
        if calibration is None:
            raise RuntimeError("Washing calibration is incomplete")

        return calibration
