from dataclasses import dataclass


@dataclass(frozen=True)
class SpeedCurvePoint:
    progress: float
    speed_percent: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.progress <= 1.0:
            raise ValueError("Progress must be between 0 and 1")

        if not 0.0 <= self.speed_percent <= 100.0:
            raise ValueError("Speed percent must be between 0 and 100")


class SpeedCurve:
    def __init__(self, points: list[SpeedCurvePoint]):
        if len(points) < 2:
            raise ValueError("Speed curve requires at least two points")

        progress_values = [point.progress for point in points]

        if len(progress_values) != len(set(progress_values)):
            raise ValueError("Speed curve progress values must be unique")

        self._points = sorted(
            points,
            key=lambda point: point.progress,
        )

    @property
    def points(self) -> tuple[SpeedCurvePoint, ...]:
        return tuple(self._points)

    def speed_at(self, progress: float) -> float:
        if progress <= self._points[0].progress:
            return self._points[0].speed_percent

        if progress >= self._points[-1].progress:
            return self._points[-1].speed_percent

        for left, right in zip(
            self._points,
            self._points[1:],
        ):
            if left.progress <= progress <= right.progress:
                return self._interpolate(
                    left=left,
                    right=right,
                    progress=progress,
                )

        raise RuntimeError("Unable to interpolate speed curve")

    @staticmethod
    def _interpolate(
        left: SpeedCurvePoint,
        right: SpeedCurvePoint,
        progress: float,
    ) -> float:
        segment_progress = (progress - left.progress) / (right.progress - left.progress)

        return (
            left.speed_percent
            + (right.speed_percent - left.speed_percent) * segment_progress
        )
