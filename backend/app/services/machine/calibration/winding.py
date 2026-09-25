from app.services.machine.calibration.points import CalibrationPoint
from app.services.machine.calibration.store import CalibrationPointStore


class WindingCalibration:
    """
    Calibration data for the WINDING mode.

    All position are expressed as physical roller revolutions measured from POINT_0.
    """

    def __init__(self, store: CalibrationPointStore | None = None):
        self.store = store or CalibrationPointStore()

        self._belt_start_turns: float | None = None
        self._material_wound_turns: float | None = None

    @property
    def belt_start_turns(self) -> float | None:
        return self._belt_start_turns

    @property
    def material_wound_turns(self) -> float | None:
        return self._material_wound_turns

    def set_belt_start(self, turns: float) -> None:
        self._validate_turns(turns)
        self._belt_start_turns = turns
        self.store.set(CalibrationPoint.WINDING_BELT_START, turns)

    def set_material_wound(self, turns: float) -> None:
        self._validate_turns(turns)
        self._material_wound_turns = turns
        self.store.set(CalibrationPoint.WINDING_MATERIAL_WOUND, turns)

    def is_complete(self) -> bool:
        return (
            self._belt_start_turns is not None
            and self._material_wound_turns is not None
        )

    def validate(self) -> None:
        if self._belt_start_turns is None:
            raise ValueError("Belt start point is not calibrated")

        if self._material_wound_turns is None:
            raise ValueError("Material wound point is not calibrated")

        if self._belt_start_turns >= self._material_wound_turns:
            raise ValueError("Belt start point must be before material wound point")

    def set_point(self, point: CalibrationPoint, turns: float) -> None:
        if point == CalibrationPoint.WINDING_BELT_START:
            self.set_belt_start(turns)
            return

        if point == CalibrationPoint.WINDING_MATERIAL_WOUND:
            self.set_material_wound(turns)
            return
        raise ValueError("Point does not belong to winding calibration")

    @staticmethod
    def _validate_turns(turns: float) -> None:
        if turns < 0:
            raise ValueError("Turns cannot be negative")
