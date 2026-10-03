import pytest

from app.services.machine.calibration.points import CalibrationPoint
from app.services.machine.calibration.session import CalibrationSession
from app.services.winding.rotation import RollerRotationCalculator


class FakeMachine:
    def start_roller_forward(self, frequency_hz: float) -> None:
        pass

    def start_roller_reverse(self, frequency_hz: float) -> None:
        pass

    def stop_roller(self) -> None:
        pass


def create_session() -> CalibrationSession:
    return CalibrationSession(
        machine=FakeMachine(),
        rotation_calculator=RollerRotationCalculator(
            motor_rpm_at_50hz=905,
            gear_ratio=100,
        ),
        material_profile_id=1,
    )


def test_session_starts_at_point_zero() -> None:
    session = create_session()

    assert session.position_turns == 0.0


def test_session_uses_selected_material() -> None:
    session = create_session()

    assert session.material_profile_id == 1


def test_set_machine_calibration_points() -> None:
    session = create_session()

    session.position_tracker.set_position(3.0)
    session.set_point(CalibrationPoint.WASHING_STOP)

    session.position_tracker.set_position(10.0)
    session.set_point(CalibrationPoint.MATERIAL_START)

    assert session.machine_calibration.washing_stop_turns == 3.0
    assert session.machine_calibration.material_start_turns == 10.0


def test_set_material_end_point() -> None:
    session = create_session()

    session.position_tracker.set_position(35.0)
    session.set_point(CalibrationPoint.MATERIAL_END)

    assert session.winding_calibration.material_end_turns == 35.0


def test_complete_calibration() -> None:
    session = create_session()

    session.position_tracker.set_position(3.0)
    session.set_point(CalibrationPoint.WASHING_STOP)

    session.position_tracker.set_position(10.0)
    session.set_point(CalibrationPoint.MATERIAL_START)

    session.position_tracker.set_position(35.0)
    session.set_point(CalibrationPoint.MATERIAL_END)

    assert session.is_complete() is True

    session.validate()


def test_incomplete_calibration_is_not_complete() -> None:
    session = create_session()

    session.position_tracker.set_position(3.0)
    session.set_point(CalibrationPoint.WASHING_STOP)

    assert session.is_complete() is False


def test_point_zero_cannot_be_saved_as_calibration_point() -> None:
    session = create_session()

    with pytest.raises(
        ValueError,
        match="Unsupported calibration point",
    ):
        session.set_point(CalibrationPoint.POINT_0)
