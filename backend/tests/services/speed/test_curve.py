import pytest

from app.services.speed.curve import SpeedCurve, SpeedCurvePoint


def test_curve_returns_speed_at_first_point() -> None:
    curve = SpeedCurve(
        [
            SpeedCurvePoint(progress=0.0, speed_percent=20.0),
            SpeedCurvePoint(progress=1.0, speed_percent=80.0),
        ]
    )

    assert curve.speed_at(0.0) == pytest.approx(20.0)


def test_curve_returns_speed_at_last_point() -> None:
    curve = SpeedCurve(
        [
            SpeedCurvePoint(progress=0.0, speed_percent=20.0),
            SpeedCurvePoint(progress=1.0, speed_percent=80.0),
        ]
    )

    assert curve.speed_at(1.0) == pytest.approx(80.0)


def test_curve_interpolates_between_two_points() -> None:
    curve = SpeedCurve(
        [
            SpeedCurvePoint(progress=0.0, speed_percent=20.0),
            SpeedCurvePoint(progress=1.0, speed_percent=80.0),
        ]
    )

    assert curve.speed_at(0.5) == pytest.approx(50.0)


def test_curve_interpolates_between_multiple_points() -> None:
    curve = SpeedCurve(
        [
            SpeedCurvePoint(progress=0.0, speed_percent=20.0),
            SpeedCurvePoint(progress=0.25, speed_percent=40.0),
            SpeedCurvePoint(progress=0.50, speed_percent=80.0),
            SpeedCurvePoint(progress=1.0, speed_percent=30.0),
        ]
    )

    assert curve.speed_at(0.125) == pytest.approx(30.0)
    assert curve.speed_at(0.375) == pytest.approx(60.0)
    assert curve.speed_at(0.75) == pytest.approx(55.0)


def test_curve_returns_exact_intermediate_point() -> None:
    curve = SpeedCurve(
        [
            SpeedCurvePoint(progress=0.0, speed_percent=20.0),
            SpeedCurvePoint(progress=0.4, speed_percent=70.0),
            SpeedCurvePoint(progress=1.0, speed_percent=30.0),
        ]
    )

    assert curve.speed_at(0.4) == pytest.approx(70.0)


def test_progress_before_zero_is_clamped() -> None:
    curve = SpeedCurve(
        [
            SpeedCurvePoint(progress=0.0, speed_percent=20.0),
            SpeedCurvePoint(progress=1.0, speed_percent=80.0),
        ]
    )

    assert curve.speed_at(-0.5) == pytest.approx(20.0)


def test_progress_after_one_is_clamped() -> None:
    curve = SpeedCurve(
        [
            SpeedCurvePoint(progress=0.0, speed_percent=20.0),
            SpeedCurvePoint(progress=1.0, speed_percent=80.0),
        ]
    )

    assert curve.speed_at(1.5) == pytest.approx(80.0)


def test_curve_requires_at_least_two_points() -> None:
    with pytest.raises(
        ValueError,
        match="Speed curve requires at least two points",
    ):
        SpeedCurve(
            [
                SpeedCurvePoint(
                    progress=0.0,
                    speed_percent=20.0,
                )
            ]
        )


@pytest.mark.parametrize(
    "progress",
    [-0.1, 1.1],
)
def test_curve_point_progress_must_be_between_zero_and_one(
    progress: float,
) -> None:
    with pytest.raises(
        ValueError,
        match="Progress must be between 0 and 1",
    ):
        SpeedCurvePoint(
            progress=progress,
            speed_percent=50.0,
        )


@pytest.mark.parametrize(
    "speed_percent",
    [-1.0, 101.0],
)
def test_curve_point_speed_must_be_between_zero_and_100(
    speed_percent: float,
) -> None:
    with pytest.raises(
        ValueError,
        match="Speed percent must be between 0 and 100",
    ):
        SpeedCurvePoint(
            progress=0.5,
            speed_percent=speed_percent,
        )


def test_curve_points_must_have_unique_progress() -> None:
    with pytest.raises(
        ValueError,
        match="Speed curve progress values must be unique",
    ):
        SpeedCurve(
            [
                SpeedCurvePoint(progress=0.0, speed_percent=20.0),
                SpeedCurvePoint(progress=0.5, speed_percent=50.0),
                SpeedCurvePoint(progress=0.5, speed_percent=70.0),
                SpeedCurvePoint(progress=1.0, speed_percent=30.0),
            ]
        )


def test_curve_sorts_points_by_progress() -> None:
    curve = SpeedCurve(
        [
            SpeedCurvePoint(progress=1.0, speed_percent=80.0),
            SpeedCurvePoint(progress=0.0, speed_percent=20.0),
        ]
    )

    assert curve.speed_at(0.5) == pytest.approx(50.0)
