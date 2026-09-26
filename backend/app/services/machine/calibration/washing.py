from app.services.machine.calibration.points import CalibrationPoint
from app.services.machine.calibration.store import CalibrationPointStore


class WashingCalibration:
    """
    Calibration fata for the WASHING mode.

    All positions are expressed as physical roller revolutions
    along the washing trajectory
    """

    def __init__(self, store: CalibrationPointStore | None = None):
        self.store = store or CalibrationPointStore()

        self._material_reaches_brushes_turns: float | None = None
        self._material_end_turns: float | None = None
        self._belt_safe_turns: float | None = None

    @property
    def material_reaches_brushes_turns(self) -> float | None:
        return self._material_reaches_brushes_turns

    @property
    def material_end_turns(self) -> float | None:
        return self._material_end_turns

    @property
    def belt_safe_turns(self) -> float | None:
        return self._belt_safe_turns

    def set_material_reaches_brushes(self, turns: float) -> None:
        self._validate_turns(turns)
        self._material_reaches_brushes_turns = turns
        self.store.set(CalibrationPoint.WASHING_MATERIAL_REACHES_BRUSHES, turns)

    def set_material_end(self, turns: float) -> None:
        self._validate_turns(turns)
        self._material_end_turns = turns
        self.store.set(CalibrationPoint.WASHING_MATERIAL_END, turns)

    def set_belt_safe(self, turns: float) -> None:
        self._validate_turns(turns)
        self._belt_safe_turns = turns
        self.store.set(CalibrationPoint.WASHING_BELT_SAFE, turns)

    def is_complete(self) -> bool:
        return (
            self._material_reaches_brushes_turns is not None
            and self._material_end_turns is not None
            and self._belt_safe_turns is not None
        )

    def validate(self) -> None:
        if self._material_reaches_brushes_turns is None:
            raise ValueError("Material reaches brushes point is not calibrated")

        if self._material_end_turns is None:
            raise ValueError("Material end point is not calibrated")

        if self._belt_safe_turns is None:
            raise ValueError("Belt safe point is not calibrated")

        if not (
            self._material_reaches_brushes_turns
            > self._material_end_turns
            > self._belt_safe_turns
        ):
            raise ValueError("Washing calibration points must be in reverse order")

    def set_point(
        self,
        point: CalibrationPoint,
        turns: float,
    ) -> None:
        if point == CalibrationPoint.WASHING_MATERIAL_REACHES_BRUSHES:
            self.set_material_reaches_brushes(turns)
            return
        if point == CalibrationPoint.WASHING_MATERIAL_END:
            self.set_material_end(turns)
            return
        if point == CalibrationPoint.WASHING_BELT_SAFE:
            self.set_belt_safe(turns)
            return
        raise ValueError("Point does not belong to washing calibration")

    @staticmethod
    def _validate_turns(turns: float) -> None:
        if turns < 0:
            raise ValueError("Turns cannot be negative")
