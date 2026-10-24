import pytest

from app.services.winding.calculator import WindingCalculator


def create_calculator() -> WindingCalculator:
    return WindingCalculator(
        core_diameter_mm=200,
        material_thickness_mm=0.8,
    )


def test_initial_diameter():
    calculator = create_calculator()

    assert calculator.current_diameter_mm == pytest.approx(200)


def test_diameter_increases_after_turns():
    calculator = create_calculator()

    initial_diameter = calculator.current_diameter_mm

    calculator.add_turns(1)

    assert calculator.current_diameter_mm > initial_diameter


def test_diameter_after_one_turn():
    calculator = create_calculator()

    calculator.add_turns(1)

    expected_diameter_mm = 200 + 2 * 0.8

    assert calculator.current_diameter_mm == pytest.approx(expected_diameter_mm)


def test_length_after_one_turn():
    calculator = create_calculator()

    length = calculator.length_for_turns(1)

    expected = 3.141592653589793 * 0.2 + 3.141592653589793 * 0.0008

    assert length == pytest.approx(expected)


def test_turns_and_length_are_inverse():
    calculator = create_calculator()

    turns = 20

    length = calculator.length_for_turns(turns)
    result_turns = calculator.turns_for_length(length)

    assert result_turns == pytest.approx(turns)


def test_add_turns():
    calculator = create_calculator()

    calculator.add_turns(10)

    assert calculator.wound_turns == pytest.approx(10)

    expected_length = calculator.length_for_turns(10)

    assert calculator.wound_length_m == pytest.approx(expected_length)


def test_add_length():
    calculator = create_calculator()

    length = calculator.length_for_turns(10)

    calculator.add_length(length)

    assert calculator.wound_length_m == pytest.approx(length)
    assert calculator.wound_turns == pytest.approx(10)


def test_roller_rpm_at_initial_diameter():
    calculator = create_calculator()

    assert calculator.roller_rpm(100) == pytest.approx(9.05)


def test_frequency_at_initial_diameter():
    calculator = create_calculator()

    assert calculator.frequency_hz(100) == pytest.approx(50)


def test_frequency_decreases_after_winding():
    calculator = create_calculator()

    initial_frequency = calculator.frequency_hz(100)

    calculator.add_turns(20)

    new_frequency = calculator.frequency_hz(100)

    assert new_frequency < initial_frequency


def test_speed_percent_scales_frequency():
    calculator = create_calculator()

    frequency_100 = calculator.frequency_hz(100)
    frequency_75 = calculator.frequency_hz(75)

    assert frequency_75 == pytest.approx(frequency_100 * 0.75)


def test_reset():
    calculator = create_calculator()

    calculator.add_turns(20)

    calculator.reset()

    assert calculator.wound_turns == 0
    assert calculator.wound_length_m == 0
    assert calculator.current_diameter_mm == pytest.approx(200)


def test_negative_turns():
    calculator = create_calculator()

    with pytest.raises(ValueError):
        calculator.add_turns(-1)


def test_negative_length():
    calculator = create_calculator()

    with pytest.raises(ValueError):
        calculator.add_length(-1)


def test_invalid_speed_percent_zero():
    calculator = create_calculator()

    with pytest.raises(ValueError):
        calculator.frequency_hz(0)


def test_invalid_speed_percent_above_100():
    calculator = create_calculator()

    with pytest.raises(ValueError):
        calculator.frequency_hz(101)
