from enum import Enum

from app.services.machine.calibration.machine import MachineCalibration
from app.services.machine.calibration.winding import WindingCalibration


class WashingPhase(str, Enum):
    MATERIAL = "material"
    BELTS = "belts"
    WASHING_STOP = "washing_stop"


class WashingTrajectory:
    def __init__(
        self,
        machine_calibration: MachineCalibration,
        winding_calibration: WindingCalibration,
    ):
        self.machine_calibration = machine_calibration
        self.winding_calibration = winding_calibration

    def phase_at(self, position_turns: float) -> WashingPhase:
        self._validate_position(position_turns)

        self.machine_calibration.validate()
        self.winding_calibration.validate()

        material_start = self.machine_calibration.material_start_turns
        washing_stop = self.machine_calibration.washing_stop_turns
        material_end = self.winding_calibration.material_end_turns

        if material_start is None:
            raise RuntimeError("Machine calibration is incomplete")

        if washing_stop is None:
            raise RuntimeError("Machine calibration is incomplete")

        if material_end is None:
            raise RuntimeError("Winding calibration is incomplete")

        if position_turns > material_start:
            return WashingPhase.MATERIAL

        if position_turns > washing_stop:
            return WashingPhase.BELTS

        return WashingPhase.WASHING_STOP

    @staticmethod
    def _validate_position(position_turns: float) -> None:
        if position_turns < 0:
            raise ValueError("Position cannot be negative")
