from app.services.machine.calibration.points import CalibrationPoint
from app.services.machine.calibration.store import CalibrationPointStore


class MachineCalibration:
    def __init__(self, store: CalibrationPointStore | None = None):
        self.store = store or CalibrationPointStore()
        self._material_start_turns: float | None = None
        self._washing_stop_turns: float | None = None
        self._water_start_turns: float | None = None

    @property
    def material_start_turns(self) -> float | None:
        return self._material_start_turns

    @property
    def washing_stop_turns(self) -> float | None:
        return self._washing_stop_turns

    @property
    def water_start_turns(self) -> float | None:
        return self._water_start_turns

    def set_water_start(self, turns: float) -> None:
        self._validate_turns(turns)
        self._water_start_turns = turns
        self.store.set(CalibrationPoint.WATER_START, turns)

    def set_material_start(self, turns: float) -> None:
        self._validate_turns(turns)
        self._material_start_turns = turns
        self.store.set(CalibrationPoint.MATERIAL_START, turns)

    def set_washing_stop(self, turns: float) -> None:
        self._validate_turns(turns)
        self._washing_stop_turns = turns
        self.store.set(CalibrationPoint.WASHING_STOP, turns)

    def set_point(self, point: CalibrationPoint, turns: float) -> None:
        if point == CalibrationPoint.MATERIAL_START:
            self.set_material_start(turns)
            return

        if point == CalibrationPoint.WASHING_STOP:
            self.set_washing_stop(turns)
            return

        if point == CalibrationPoint.WATER_START:
            self.set_water_start(turns)
            return

        raise ValueError("Point does not belong to machine calibration")

    def is_complete(self) -> bool:
        return (
            self._material_start_turns is not None
            and self._washing_stop_turns is not None
            and self._water_start_turns is not None
        )

    def validate(self) -> None:
        if self._material_start_turns is None:
            raise ValueError("Material start point is not calibrated")

        if self._washing_stop_turns is None:
            raise ValueError("Washing stop point is not calibrated")

        if self._washing_stop_turns <= 0:
            raise ValueError("Washing stop point must be after POINT_0")

        if self._material_start_turns <= self._washing_stop_turns:
            raise ValueError("Material start point must be after washing stop point")

        if self._water_start_turns is None:
            raise ValueError("Water start point is not calibrated")

        if not (self._material_start_turns < self._water_start_turns):
            raise ValueError("Water start must be after material start")

    @staticmethod
    def _validate_turns(turns: float) -> None:
        if turns < 0:
            raise ValueError("Turns cannot be negative")
