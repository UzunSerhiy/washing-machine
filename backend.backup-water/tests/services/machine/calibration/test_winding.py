import pytest

from app.services.machine.calibration.points import CalibrationPoint
from app.services.machine.calibration.store import CalibrationPointStore
from app.services.machine.calibration.winding import WindingCalibration


def test_new_calibration_is_empty():
    calibration = WindingCalibration()

    assert calibration.material_end_turns is None
    assert calibration.is_complete() is False


def test_set_material_end():
    calibration = WindingCalibration()

    calibration.set_material_end(42.7)

    assert calibration.material_end_turns == 42.7


def test_calibration_is_complete():
    calibration = WindingCalibration()

    calibration.set_material_end(42.7)

    assert calibration.is_complete() is True


def test_validate_complete_calibration():
    calibration = WindingCalibration()

    calibration.set_material_end(42.7)

    calibration.validate()


def test_validate_requires_material_end():
    calibration = WindingCalibration()

    with pytest.raises(
        ValueError,
        match="Material end point is not calibrated",
    ):
        calibration.validate()


def test_negative_material_end_is_invalid():
    calibration = WindingCalibration()

    with pytest.raises(
        ValueError,
        match="Turns cannot be negative",
    ):
        calibration.set_material_end(-1.0)


def test_winding_calibration_accepts_material_end():
    calibration = WindingCalibration()

    calibration.set_point(
        CalibrationPoint.MATERIAL_END,
        30.0,
    )

    assert calibration.material_end_turns == 30.0


def test_winding_calibration_rejects_machine_point():
    calibration = WindingCalibration()

    with pytest.raises(
        ValueError,
        match="Point does not belong to winding calibration",
    ):
        calibration.set_point(
            CalibrationPoint.MATERIAL_START,
            20.0,
        )


def test_winding_calibration_rejects_washing_point():
    calibration = WindingCalibration()

    with pytest.raises(
        ValueError,
        match="Point does not belong to winding calibration",
    ):
        calibration.set_point(
            CalibrationPoint.WASHING_STOP,
            20.0,
        )


def test_setting_winding_point_updates_store():
    calibration = WindingCalibration()

    calibration.set_point(
        CalibrationPoint.MATERIAL_END,
        30.0,
    )

    assert calibration.store.get(CalibrationPoint.MATERIAL_END) == 30.0


def test_winding_calibration_uses_provided_store():
    store = CalibrationPointStore()
    calibration = WindingCalibration(store)

    calibration.set_material_end(30.0)

    assert store.get(CalibrationPoint.MATERIAL_END) == 30.0
