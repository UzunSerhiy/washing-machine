import pytest

from app.services.machine.calibration.data import CalibrationData
from app.services.speed.curve import SpeedCurve, SpeedCurvePoint
from app.services.speed.material_profile import MaterialSpeedProfile


@pytest.fixture
def calibration() -> CalibrationData:
    return CalibrationData(
        machine_id=1,
        material_profile_id=3,
        washing_stop_turns=5.0,
        material_start_turns=12.0,
        material_end_turns=40.0,
    )


@pytest.fixture
def curve() -> SpeedCurve:
    return SpeedCurve(
        [
            SpeedCurvePoint(
                progress=0.0,
                speed_percent=20.0,
            ),
            SpeedCurvePoint(
                progress=0.5,
                speed_percent=80.0,
            ),
            SpeedCurvePoint(
                progress=1.0,
                speed_percent=40.0,
            ),
        ]
    )


@pytest.fixture
def profile(
    calibration: CalibrationData,
    curve: SpeedCurve,
) -> MaterialSpeedProfile:
    return MaterialSpeedProfile(
        calibration=calibration,
        curve=curve,
    )


def test_speed_at_material_start(
    profile: MaterialSpeedProfile,
) -> None:
    assert profile.speed_at_position(12.0) == pytest.approx(20.0)


def test_speed_at_material_middle(
    profile: MaterialSpeedProfile,
) -> None:
    assert profile.speed_at_position(26.0) == pytest.approx(80.0)


def test_speed_at_material_end(
    profile: MaterialSpeedProfile,
) -> None:
    assert profile.speed_at_position(40.0) == pytest.approx(40.0)


def test_speed_is_interpolated_from_material_position(
    profile: MaterialSpeedProfile,
) -> None:
    # position 19:
    #
    # material_start = 12
    # material_end   = 40
    #
    # (19 - 12) / 28 = 0.25
    #
    # curve:
    # 0.0 -> 20%
    # 0.5 -> 80%
    #
    # therefore 0.25 -> 50%

    assert profile.speed_at_position(19.0) == pytest.approx(50.0)


def test_position_before_material_start_uses_curve_start(
    profile: MaterialSpeedProfile,
) -> None:
    assert profile.speed_at_position(5.0) == pytest.approx(20.0)


def test_position_after_material_end_uses_curve_end(
    profile: MaterialSpeedProfile,
) -> None:
    assert profile.speed_at_position(50.0) == pytest.approx(40.0)


def test_progress_at_position(
    profile: MaterialSpeedProfile,
) -> None:
    assert profile.progress_at_position(26.0) == pytest.approx(0.5)


def test_profile_exposes_material_profile_id(
    profile: MaterialSpeedProfile,
) -> None:
    assert profile.material_profile_id == 3
