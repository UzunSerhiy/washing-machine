import pytest

from app.services.machine.calibration.washing import WashingCalibration
from app.services.machine.calibration.points import CalibrationPoint
from app.services.machine.calibration.store import CalibrationPointStore


def test_new_calibration_is_empty():
    calibration = WashingCalibration()

    assert calibration.material_reaches_brushes_turns is None
    assert calibration.material_end_turns is None
    assert calibration.belt_safe_turns is None
    assert calibration.is_complete() is False


def test_set_material_reaches_brushes():
    calibration = WashingCalibration()

    calibration.set_material_reaches_brushes(10.0)

    assert calibration.material_reaches_brushes_turns == 10.0


def test_set_material_end():
    calibration = WashingCalibration()

    calibration.set_material_end(20.0)

    assert calibration.material_end_turns == 20.0


def test_set_belt_safe():
    calibration = WashingCalibration()

    calibration.set_belt_safe(25.0)

    assert calibration.belt_safe_turns == 25.0


def test_calibration_is_complete():
    calibration = WashingCalibration()

    calibration.set_material_reaches_brushes(10.0)
    calibration.set_material_end(20.0)
    calibration.set_belt_safe(25.0)

    assert calibration.is_complete() is True


def test_validate_complete_calibration():
    calibration = WashingCalibration()

    calibration.set_material_reaches_brushes(10.0)
    calibration.set_material_end(20.0)
    calibration.set_belt_safe(25.0)

    calibration.validate()


def test_validate_requires_material_reaches_brushes():
    calibration = WashingCalibration()

    calibration.set_material_end(20.0)
    calibration.set_belt_safe(25.0)

    with pytest.raises(
        ValueError,
        match="Material reaches brushes point is not calibrated",
    ):
        calibration.validate()


def test_validate_requires_material_end():
    calibration = WashingCalibration()

    calibration.set_material_reaches_brushes(10.0)
    calibration.set_belt_safe(25.0)

    with pytest.raises(
        ValueError,
        match="Material end point is not calibrated",
    ):
        calibration.validate()


def test_validate_requires_belt_safe():
    calibration = WashingCalibration()

    calibration.set_material_reaches_brushes(10.0)
    calibration.set_material_end(20.0)

    with pytest.raises(
        ValueError,
        match="Belt safe point is not calibrated",
    ):
        calibration.validate()


def test_points_must_be_in_order():
    calibration = WashingCalibration()

    calibration.set_material_reaches_brushes(20.0)
    calibration.set_material_end(10.0)
    calibration.set_belt_safe(30.0)

    with pytest.raises(
        ValueError,
        match="Washing calibration points must be in order",
    ):
        calibration.validate()


def test_equal_points_are_invalid():
    calibration = WashingCalibration()

    calibration.set_material_reaches_brushes(10.0)
    calibration.set_material_end(10.0)
    calibration.set_belt_safe(20.0)

    with pytest.raises(
        ValueError,
        match="Washing calibration points must be in order",
    ):
        calibration.validate()


def test_negative_turns_are_invalid():
    calibration = WashingCalibration()

    with pytest.raises(
        ValueError,
        match="Turns cannot be negative",
    ):
        calibration.set_belt_safe(-1.0)


def test_wahing_calibration_accepts_washing_points():
    calibration = WashingCalibration()

    calibration.set_point(
        CalibrationPoint.WASHING_MATERIAL_REACHES_BRUSHES,
        10.0,
    )

    calibration.set_point(CalibrationPoint.WASHING_MATERIAL_END, 20.0)

    calibration.set_point(CalibrationPoint.WASHING_BELT_SAFE, 30.0)

    assert calibration.material_reaches_brushes_turns == 10.0
    assert calibration.material_end_turns == 20.0
    assert calibration.belt_safe_turns == 30.0


def test_washing_calibration_rejects_winding_point():
    calibration = WashingCalibration()

    with pytest.raises(
        ValueError,
        match="Point does not belong to washing calibration",
    ):
        calibration.set_point(
            CalibrationPoint.WINDING_BELT_START,
            20.0,
        )


def test_washing_calibration_uses_provided_store():
    store = CalibrationPointStore()
    calibration = WashingCalibration(store)

    calibration.set_material_reaches_brushes(10.0)
    calibration.set_material_end(20.0)
    calibration.set_belt_safe(30.0)

    assert store.get(CalibrationPoint.WASHING_MATERIAL_REACHES_BRUSHES) == 10.0

    assert store.get(CalibrationPoint.WASHING_MATERIAL_END) == 20.0

    assert store.get(CalibrationPoint.WASHING_BELT_SAFE) == 30.0
