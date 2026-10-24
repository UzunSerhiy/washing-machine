from app.services.machine.calibration.data import CalibrationData
from app.services.speed.curve import SpeedCurve


class MaterialSpeedProfile:
    def __init__(
        self,
        calibration: CalibrationData,
        curve: SpeedCurve,
    ):
        self.calibration = calibration
        self.curve = curve

    @property
    def material_profile_id(self) -> int:
        return self.calibration.material_profile_id

    def progress_at_position(
        self,
        position_turns: float,
    ) -> float:
        return self.calibration.material_progress(position_turns)

    def speed_at_position(
        self,
        position_turns: float,
    ) -> float:
        progress = self.progress_at_position(position_turns)

        return self.curve.speed_at(progress)
