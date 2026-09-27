from app.services.machine.calibration.points import CalibrationPoint


def test_point_0():
    assert CalibrationPoint.POINT_0.value == "point_0"


def test_material_start():
    assert CalibrationPoint.MATERIAL_START.value == "material_start"


def test_material_end():
    assert CalibrationPoint.MATERIAL_END.value == "material_end"


def test_washing_stop():
    assert CalibrationPoint.WASHING_STOP.value == "washing_stop"


def test_points_are_strings():
    assert isinstance(
        CalibrationPoint.POINT_0,
        str,
    )

    assert isinstance(
        CalibrationPoint.MATERIAL_START,
        str,
    )

    assert isinstance(
        CalibrationPoint.MATERIAL_END,
        str,
    )

    assert isinstance(
        CalibrationPoint.WASHING_STOP,
        str,
    )


def test_all_points_are_unique():
    values = [point.value for point in CalibrationPoint]

    assert len(values) == len(set(values))


def test_number_of_calibration_points():
    assert len(CalibrationPoint) == 4
