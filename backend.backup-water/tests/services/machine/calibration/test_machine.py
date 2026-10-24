import pytest

from app.services.machine.calibration.machine import MachineCalibration
from app.services.machine.calibration.points import CalibrationPoint
from app.services.machine.calibration.store import CalibrationPointStore


def test_new_calibration_is_empty():
    calibration = MachineCalibration()

    assert calibration.material_start_turns is None
    assert calibration.washing_stop_turns is None
    assert calibration.is_complete() is False


def test_set_material_start():
    calibration = MachineCalibration()

    calibration.set_material_start(10.0)

    assert calibration.material_start_turns == 10.0


def test_set_washing_stop():
    calibration = MachineCalibration()

    calibration.set_washing_stop(3.0)

    assert calibration.washing_stop_turns == 3.0


def test_calibration_is_complete():
    calibration = MachineCalibration()

    calibration.set_material_start(10.0)
    calibration.set_washing_stop(3.0)

    assert calibration.is_complete() is True


def test_validate_complete_calibration():
    calibration = MachineCalibration()

    calibration.set_material_start(10.0)
    calibration.set_washing_stop(3.0)

    calibration.validate()


def test_validate_requires_material_start():
    calibration = MachineCalibration()

    calibration.set_washing_stop(3.0)

    with pytest.raises(
        ValueError,
        match="Material start point is not calibrated",
    ):
        calibration.validate()


def test_validate_requires_washing_stop():
    calibration = MachineCalibration()

    calibration.set_material_start(10.0)

    with pytest.raises(
        ValueError,
        match="Washing stop point is not calibrated",
    ):
        calibration.validate()


def test_material_start_must_be_after_washing_stop():
    calibration = MachineCalibration()

    calibration.set_material_start(3.0)
    calibration.set_washing_stop(10.0)

    with pytest.raises(
        ValueError,
        match="Material start point must be after washing stop point",
    ):
        calibration.validate()


def test_equal_points_are_invalid():
    calibration = MachineCalibration()

    calibration.set_material_start(10.0)
    calibration.set_washing_stop(10.0)

    with pytest.raises(
        ValueError,
        match="Material start point must be after washing stop point",
    ):
        calibration.validate()


def test_negative_material_start_is_invalid():
    calibration = MachineCalibration()

    with pytest.raises(
        ValueError,
        match="Turns cannot be negative",
    ):
        calibration.set_material_start(-1.0)


def test_negative_washing_stop_is_invalid():
    calibration = MachineCalibration()

    with pytest.raises(
        ValueError,
        match="Turns cannot be negative",
    ):
        calibration.set_washing_stop(-1.0)


def test_machine_calibration_accepts_machine_points():
    calibration = MachineCalibration()

    calibration.set_point(CalibrationPoint.MATERIAL_START, 10.0)
    calibration.set_point(CalibrationPoint.WASHING_STOP, 3.0)

    assert calibration.material_start_turns == 10.0
    assert calibration.washing_stop_turns == 3.0


def test_machine_calibration_rejects_material_end():
    calibration = MachineCalibration()

    with pytest.raises(
        ValueError,
        match="Point does not belong to machine calibration",
    ):
        calibration.set_point(
            CalibrationPoint.MATERIAL_END,
            30.0,
        )


def test_setting_machine_point_updates_store():
    calibration = MachineCalibration()

    calibration.set_point(CalibrationPoint.MATERIAL_START, 10.0)
    calibration.set_point(CalibrationPoint.WASHING_STOP, 3.0)

    assert calibration.store.get(CalibrationPoint.MATERIAL_START) == 10.0
    assert calibration.store.get(CalibrationPoint.WASHING_STOP) == 3.0


def test_machine_calibration_uses_provided_store():
    store = CalibrationPointStore()
    calibration = MachineCalibration(store)

    calibration.set_material_start(10.0)
    calibration.set_washing_stop(3.0)

    assert store.get(CalibrationPoint.MATERIAL_START) == 10.0
    assert store.get(CalibrationPoint.WASHING_STOP) == 3.0


def test_washing_stop_must_be_after_point_zero():
    calibration = MachineCalibration()

    calibration.set_material_start(10.0)
    calibration.set_washing_stop(0.0)

    with pytest.raises(
        ValueError,
        match="Washing stop point must be after POINT_0",
    ):
        calibration.validate()


def test_machine_calibration_rejects_point_zero():
    calibration = MachineCalibration()

    with pytest.raises(
        ValueError,
        match="Point does not belong to machine calibration",
    ):
        calibration.set_point(
            CalibrationPoint.POINT_0,
            0.0,
        )
