from app.services.machine.calibration.points import CalibrationPoint


def test_winding_points():
    assert CalibrationPoint.WINDING_BELT_START.value == ("winding_belt_start")

    assert CalibrationPoint.WINDING_MATERIAL_WOUND.value == ("winding_material_wound")


def test_washing_points():
    assert CalibrationPoint.WASHING_MATERIAL_REACHES_BRUSHES.value == (
        "washing_material_reaches_brushes"
    )

    assert CalibrationPoint.WASHING_MATERIAL_END.value == ("washing_material_end")

    assert CalibrationPoint.WASHING_BELT_SAFE.value == ("washing_belt_safe")


def test_points_are_strings():
    assert isinstance(
        CalibrationPoint.WINDING_BELT_START,
        str,
    )

    assert isinstance(
        CalibrationPoint.WASHING_BELT_SAFE,
        str,
    )


def test_all_points_are_unique():
    values = [point.value for point in CalibrationPoint]

    assert len(values) == len(set(values))


def test_number_of_calibration_points():
    assert len(CalibrationPoint) == 5
