import math

from app.services.winding.calculator import WindingCalculator


def text_initial_diameter():
    calculator = WindingCalculator(
        core_diameter_mm=200,
        material_thickness_mm=0.8,
    )

    assert calculator.current_diameter_mm == 200


def test_diameter_increases_after_rotation():
    calculator = WindingCalculator(
        core_diameter_mm=200,
        material_thickness_mm=0.8,
    )

    initial_diameter = calculator.current_diameter_mm

    calculator.add_rotation(2 * math.pi)

    assert calculator.current_diameter_mm > initial_diameter


def test_reset():
    calculator = WindingCalculator(core_diameter_mm=200, material_thickness_mm=0.8)

    calculator.add_rotation(2 * math.pi)

    calculator.reset()

    assert calculator.wound_length_m == 0
    assert calculator.current_diameter_mm == 200


def test_roller_rpm():
    calculator = WindingCalculator(
        core_diameter_mm=200,
        material_thickness_mm=0.8,
    )

    rpm = calculator.roller_rpm(
        linear_speed_m_min=10,
    )

    expected = 10 / (math.pi * 0.2)

    assert rpm == expected
