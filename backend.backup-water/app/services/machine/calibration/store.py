from app.services.machine.calibration.points import CalibrationPoint


class CalibrationPointStore:
    def __init__(self):
        self._points: dict[CalibrationPoint, float] = {}

    def set(self, point: CalibrationPoint, turns: float) -> None:
        if turns < 0:
            raise ValueError("Turns cannot be negative")

        self._points[point] = turns

    def get(self, point: CalibrationPoint) -> float | None:
        return self._points.get(point)

    def has(self, point: CalibrationPoint) -> bool:
        return point in self._points

    def clear(self, point: CalibrationPoint) -> None:
        self._points.pop(point, None)

    def clear_all(self) -> None:
        self._points.clear()

    def is_empty(self) -> bool:
        return not self._points
