import pytest

from app.services.winding.thickness import MaterialThicknessCalculator


def test_calculate_material_thickness():
    calculator = MaterialThicknessCalculator(core_diameter_mm=200)

    thickness = calculator.calculate(
        final_diameter_mm=300,
        turns=40,
    )

    assert thickness == 1.25


def test_calculate_material_thickness_different_values():
    calculator = MaterialThicknessCalculator(core_diameter_mm=200)

    thickness = calculator.calculate(
        final_diameter_mm=280,
        turns=40,
    )

    assert thickness == 1.0


@pytest.mark.parametrize(
    "final_diameter_mm,turns",
    [
        (200, 40),
        (190, 40),
        (300, 0),
        (300, -1),
    ],
)
def test_invalid_calibration_values(final_diameter_mm, turns):
    calculator = MaterialThicknessCalculator(core_diameter_mm=200)

    with pytest.raises(ValueError):
        calculator.calculate(
            final_diameter_mm=final_diameter_mm,
            turns=turns,
        )


def test_invalid_core_diameter():
    with pytest.raises(ValueError):
        MaterialThicknessCalculator(core_diameter_mm=0)
