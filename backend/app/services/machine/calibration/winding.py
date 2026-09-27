from app.services.machine.calibration.points import CalibrationPoint
from app.services.machine.calibration.store import CalibrationPointStore


class WindingCalibration:
    def __init__(self, store: CalibrationPointStore | None = None):
        self.store = store or CalibrationPointStore()
        self._material_end_turns: float | None = None

    @property
    def material_end_turns(self) -> float | None:
        return self._material_end_turns

    def set_material_end(self, turns: float) -> None:
        self._validate_turns(turns)
        self._material_end_turns = turns
        self.store.set(CalibrationPoint.MATERIAL_END, turns)

    def set_point(self, point: CalibrationPoint, turns: float) -> None:
        if point == CalibrationPoint.MATERIAL_END:
            self.set_material_end(turns)
            return

        raise ValueError("Point does not belong to winding calibration")

    def is_complete(self) -> bool:
        return self._material_end_turns is not None

    def validate(self) -> None:
        if self._material_end_turns is None:
            raise ValueError("Material end point is not calibrated")

    @staticmethod
    def _validate_turns(turns: float) -> None:
        if turns < 0:
            raise ValueError("Turns cannot be negative")
