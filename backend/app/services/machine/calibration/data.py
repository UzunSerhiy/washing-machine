from dataclasses import dataclass


@dataclass(frozen=True)
class CalibrationData:
    machine_id: int
    material_profile_id: int

    washing_stop_turns: float
    material_start_turns: float
    material_end_turns: float
    water_start_turns: float | None = None

    def __post_init__(self) -> None:
        if not (
            0
            <= self.washing_stop_turns
            < self.material_start_turns
            < self.material_end_turns
        ):
            raise ValueError("Calibration points must be ordered")

        if self.water_start_turns is not None and not (
            self.material_start_turns < self.water_start_turns < self.material_end_turns
        ):
            raise ValueError("Water start must be between material start and material end")

    @property
    def material_length_turns(self) -> float:
        return self.material_end_turns - self.material_start_turns

    @property
    def washing_length_turns(self) -> float:
        return self.material_start_turns - self.washing_stop_turns

    def material_progress(self, position_turns: float) -> float:
        progress = (
            position_turns - self.material_start_turns
        ) / self.material_length_turns

        return self._clamp_progress(progress)

    def washing_progress(self, position_turns: float) -> float:
        progress = (
            position_turns - self.washing_stop_turns
        ) / self.washing_length_turns

        return self._clamp_progress(progress)

    @staticmethod
    def _clamp_progress(value: float) -> float:
        return max(0.0, min(1.0, value))
