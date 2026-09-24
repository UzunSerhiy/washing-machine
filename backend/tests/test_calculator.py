import math

import pytest

from app.services.winding.calculator import WindingCalculator


def create_calculator() -> WindingCalculator:
    return WindingCalculator(
        core_diameter_mm=200,
        material_thickness_mm=0.5,
        motor_rpm_at_max_frequency=905,
        max_frequency_hz=50,
        gear_ratio=100,
    )


def test_max_roller_rpm():
    calculator = create_calculator()

    assert calculator.max_roller_rpm == pytest.approx(9.05)


def test_base_linear_speed():
    calculator = create_calculator()

    expected = math.pi * 0.2 * 9.05

    assert calculator.base_linear_speed_m_min == pytest.approx(expected)


def test_initial_speed_at_100_percent():
    calculator = create_calculator()

    assert calculator.roller_rpm(100) == pytest.approx(9.05)
    assert calculator.motor_rpm(100) == pytest.approx(905)
    assert calculator.frequency_hz(100) == pytest.approx(50)


def test_initial_speed_at_75_percent():
    calculator = create_calculator()

    assert calculator.roller_rpm(75) == pytest.approx(9.05 * 0.75)
    assert calculator.motor_rpm(75) == pytest.approx(905 * 0.75)
    assert calculator.frequency_hz(75) == pytest.approx(37.5)


def test_frequency_scales_with_speed_percent():
    calculator = create_calculator()

    frequency_100 = calculator.frequency_hz(100)
    frequency_75 = calculator.frequency_hz(75)
    frequency_50 = calculator.frequency_hz(50)

    assert frequency_75 == pytest.approx(frequency_100 * 0.75)
    assert frequency_50 == pytest.approx(frequency_100 * 0.50)


def test_diameter_increases_after_winding():
    calculator = create_calculator()

    initial_diameter = calculator.current_diameter_mm

    calculator.add_turns(10)

    assert calculator.current_diameter_mm > initial_diameter


def test_frequency_decreases_as_diameter_increases():
    calculator = create_calculator()

    initial_frequency = calculator.frequency_hz(100)

    calculator.add_turns(10)

    frequency_after_winding = calculator.frequency_hz(100)

    assert frequency_after_winding < initial_frequency


def test_speed_percent_does_not_change_curve_shape():
    calculator = create_calculator()

    calculator.add_turns(20)

    frequency_100 = calculator.frequency_hz(100)
    frequency_75 = calculator.frequency_hz(75)

    assert frequency_75 == pytest.approx(frequency_100 * 0.75)


def test_length_for_one_turn():
    calculator = create_calculator()

    length = calculator.length_for_turns(1)

    expected = math.pi * 0.2 + math.pi * 0.0005

    assert length == pytest.approx(expected)


def test_turns_and_length_are_inverse_operations():
    calculator = create_calculator()

    turns = 25.0

    length = calculator.length_for_turns(turns)
    calculated_turns = calculator.turns_for_length(length)

    assert calculated_turns == pytest.approx(turns)


def test_add_turns_updates_length():
    calculator = create_calculator()

    calculator.add_turns(10)

    expected_length = calculator.length_for_turns(10)

    assert calculator.wound_turns == pytest.approx(10)
    assert calculator.wound_length_m == pytest.approx(expected_length)


def test_add_length_updates_turns():
    calculator = create_calculator()

    length = calculator.length_for_turns(10)

    calculator.add_length(length)

    assert calculator.wound_length_m == pytest.approx(length)
    assert calculator.wound_turns == pytest.approx(10)


def test_current_diameter_matches_turns():
    calculator = create_calculator()

    turns = 20

    calculator.add_turns(turns)

    expected_diameter = (
        calculator.core_diameter_m + 2 * calculator.material_thickness_m * turns
    )

    assert calculator.current_diameter_m == pytest.approx(expected_diameter)


def test_initial_turn_time_at_100_percent():
    calculator = create_calculator()

    rpm = calculator.roller_rpm(100)

    turn_time_seconds = 60 / rpm

    assert turn_time_seconds == pytest.approx(60 / 9.05)


def test_initial_turn_time_at_75_percent():
    calculator = create_calculator()

    rpm = calculator.roller_rpm(75)

    turn_time_seconds = 60 / rpm

    assert turn_time_seconds == pytest.approx(60 / (9.05 * 0.75))


def test_reset():
    calculator = create_calculator()

    calculator.add_turns(20)

    calculator.reset()

    assert calculator.wound_turns == 0
    assert calculator.wound_length_m == 0
    assert calculator.current_diameter_mm == pytest.approx(200)


def test_invalid_core_diameter():
    with pytest.raises(ValueError):
        WindingCalculator(
            core_diameter_mm=0,
            material_thickness_mm=0.5,
        )


def test_invalid_material_thickness():
    with pytest.raises(ValueError):
        WindingCalculator(
            core_diameter_mm=200,
            material_thickness_mm=0,
        )


def test_invalid_speed_percent():
    calculator = create_calculator()

    with pytest.raises(ValueError):
        calculator.frequency_hz(0)

    with pytest.raises(ValueError):
        calculator.frequency_hz(101)


def test_negative_turns_are_rejected():
    calculator = create_calculator()

    with pytest.raises(ValueError):
        calculator.add_turns(-1)


def test_negative_length_is_rejected():
    calculator = create_calculator()

    with pytest.raises(ValueError):
        calculator.add_length(-1)


def test_negative_turns_conversion_is_rejected():
    calculator = create_calculator()

    with pytest.raises(ValueError):
        calculator.length_for_turns(-1)


def test_negative_length_conversion_is_rejected():
    calculator = create_calculator()

    with pytest.raises(ValueError):
        calculator.turns_for_length(-1)
