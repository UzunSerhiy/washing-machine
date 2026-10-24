import pytest

from app.services.machine.calibration.data import CalibrationData
from app.services.winding.thickness import MaterialThicknessCalculator


def create_calibration() -> CalibrationData:
    return CalibrationData(
        machine_id=1,
        material_profile_id=3,
        washing_stop_turns=5.0,
        material_start_turns=12.0,
        material_end_turns=40.0,
    )


def test_calculates_material_turns_from_calibration() -> None:
    calibration = create_calibration()

    assert calibration.material_length_turns == pytest.approx(28.0)


def test_calculates_effective_material_thickness() -> None:
    calibration = create_calibration()

    calculator = MaterialThicknessCalculator(
        core_diameter_mm=200.0,
    )

    thickness_mm = calculator.calculate(
        final_diameter_mm=228.0,
        turns=calibration.material_length_turns,
    )

    assert thickness_mm == pytest.approx(0.5)


def test_larger_final_diameter_produces_larger_thickness() -> None:
    calibration = create_calibration()

    calculator = MaterialThicknessCalculator(
        core_diameter_mm=200.0,
    )

    thin = calculator.calculate(
        final_diameter_mm=228.0,
        turns=calibration.material_length_turns,
    )

    thick = calculator.calculate(
        final_diameter_mm=256.0,
        turns=calibration.material_length_turns,
    )

    assert thick > thin


def test_final_diameter_must_be_larger_than_core() -> None:
    calculator = MaterialThicknessCalculator(
        core_diameter_mm=200.0,
    )

    with pytest.raises(
        ValueError,
        match="Final diameter must be greater than core diameter",
    ):
        calculator.calculate(
            final_diameter_mm=200.0,
            turns=28.0,
        )


def test_material_turns_must_be_positive() -> None:
    calculator = MaterialThicknessCalculator(
        core_diameter_mm=200.0,
    )

    with pytest.raises(
        ValueError,
        match="Turns must be greate than zero",
    ):
        calculator.calculate(
            final_diameter_mm=228.0,
            turns=0.0,
        )
