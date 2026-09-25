import pytest

from app.services.machine.calibration.winding import WindingCalibration
from app.services.machine.calibration.points import CalibrationPoint
from app.services.machine.calibration.store import CalibrationPointStore


def test_new_calibration_is_empty():
    calibration = WindingCalibration()

    assert calibration.belt_start_turns is None
    assert calibration.material_wound_turns is None
    assert calibration.is_complete() is False


def test_set_belt_start():
    calibration = WindingCalibration()

    calibration.set_belt_start(8.5)

    assert calibration.belt_start_turns == 8.5


def test_set_material_wound():
    calibration = WindingCalibration()

    calibration.set_material_wound(42.7)

    assert calibration.material_wound_turns == 42.7


def test_calibration_is_complete():
    calibration = WindingCalibration()

    calibration.set_belt_start(8.5)
    calibration.set_material_wound(42.7)

    assert calibration.is_complete() is True


def test_validate_complete_calibration():
    calibration = WindingCalibration()

    calibration.set_belt_start(8.5)
    calibration.set_material_wound(42.7)

    calibration.validate()


def test_validate_requires_belt_start():
    calibration = WindingCalibration()

    calibration.set_material_wound(42.7)

    with pytest.raises(
        ValueError,
        match="Belt start point is not calibrated",
    ):
        calibration.validate()


def test_validate_requires_material_wound():
    calibration = WindingCalibration()

    calibration.set_belt_start(8.5)

    with pytest.raises(
        ValueError,
        match="Material wound point is not calibrated",
    ):
        calibration.validate()


def test_material_wound_must_be_after_belt_start():
    calibration = WindingCalibration()

    calibration.set_belt_start(20.0)
    calibration.set_material_wound(10.0)

    with pytest.raises(
        ValueError,
        match="Belt start point must be before material wound point",
    ):
        calibration.validate()


def test_equal_points_are_invalid():
    calibration = WindingCalibration()

    calibration.set_belt_start(20.0)
    calibration.set_material_wound(20.0)

    with pytest.raises(
        ValueError,
        match="Belt start point must be before material wound point",
    ):
        calibration.validate()


def test_negative_belt_start_is_invalid():
    calibration = WindingCalibration()

    with pytest.raises(
        ValueError,
        match="Turns cannot be negative",
    ):
        calibration.set_belt_start(-1.0)


def test_negative_material_wound_is_invalid():
    calibration = WindingCalibration()

    with pytest.raises(
        ValueError,
        match="Turns cannot be negative",
    ):
        calibration.set_material_wound(-1.0)


def test_winding_calibration_accepts_winding_points():
    calibration = WindingCalibration()

    calibration.set_point(
        CalibrationPoint.WINDING_BELT_START,
        10.0,
    )
    calibration.set_point(
        CalibrationPoint.WINDING_MATERIAL_WOUND,
        30.0,
    )

    assert calibration.belt_start_turns == 10.0
    assert calibration.material_wound_turns == 30.0


def test_winding_calibration_rejects_washing_point():
    calibration = WindingCalibration()

    with pytest.raises(
        ValueError,
        match="Point does not belong to winding calibration",
    ):
        calibration.set_point(
            CalibrationPoint.WASHING_BELT_SAFE,
            20.0,
        )


def test_setting_winding_point_update_store():
    calibration = WindingCalibration()

    calibration.set_point(CalibrationPoint.WINDING_BELT_START, 10.0)

    calibration.set_point(CalibrationPoint.WINDING_MATERIAL_WOUND, 30.0)

    assert calibration.store.get(CalibrationPoint.WINDING_BELT_START) == 10.0

    assert calibration.store.get(CalibrationPoint.WINDING_MATERIAL_WOUND) == 30.0


def test_winding_calibration_uses_provided_store():
    store = CalibrationPointStore()
    calibration = WindingCalibration(store)

    calibration.set_belt_start(10.0)
    calibration.set_material_wound(30.0)

    assert store.get(CalibrationPoint.WINDING_BELT_START) == 10.0

    assert store.get(CalibrationPoint.WINDING_MATERIAL_WOUND) == 30.0
