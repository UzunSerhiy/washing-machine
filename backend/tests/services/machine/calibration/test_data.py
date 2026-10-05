import pytest

from app.services.machine.calibration.data import CalibrationData


@pytest.fixture
def calibration() -> CalibrationData:
    return CalibrationData(
        machine_id=1,
        material_profile_id=3,
        washing_stop_turns=5.0,
        material_start_turns=12.0,
        material_end_turns=40.0,
    )


def test_material_length_turns(calibration: CalibrationData) -> None:
    assert calibration.material_length_turns == 28.0


def test_washing_length_turns(calibration: CalibrationData) -> None:
    assert calibration.washing_length_turns == 7.0


def test_material_progress_at_start(calibration: CalibrationData) -> None:
    assert calibration.material_progress(12.0) == pytest.approx(0.0)


def test_material_progress_in_middle(calibration: CalibrationData) -> None:
    assert calibration.material_progress(26.0) == pytest.approx(0.5)


def test_material_progress_at_end(calibration: CalibrationData) -> None:
    assert calibration.material_progress(40.0) == pytest.approx(1.0)


def test_material_progress_is_clamped_before_start(
    calibration: CalibrationData,
) -> None:
    assert calibration.material_progress(5.0) == pytest.approx(0.0)


def test_material_progress_is_clamped_after_end(
    calibration: CalibrationData,
) -> None:
    assert calibration.material_progress(50.0) == pytest.approx(1.0)


def test_washing_progress_at_washing_stop(
    calibration: CalibrationData,
) -> None:
    assert calibration.washing_progress(5.0) == pytest.approx(0.0)


def test_washing_progress_at_material_start(
    calibration: CalibrationData,
) -> None:
    assert calibration.washing_progress(12.0) == pytest.approx(1.0)


def test_washing_progress_in_middle(
    calibration: CalibrationData,
) -> None:
    assert calibration.washing_progress(8.5) == pytest.approx(0.5)


def test_invalid_calibration_order_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="Calibration points must be ordered",
    ):
        CalibrationData(
            machine_id=1,
            material_profile_id=3,
            washing_stop_turns=12.0,
            material_start_turns=5.0,
            material_end_turns=40.0,
        )
