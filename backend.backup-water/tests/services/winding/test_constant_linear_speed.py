import math

import pytest

from app.services.winding.calculator import WindingCalculator


@pytest.fixture
def calculator() -> WindingCalculator:
    return WindingCalculator(
        core_diameter_mm=200.0,
        material_thickness_mm=1.0,
        motor_rpm_at_max_frequency=905.0,
        max_frequency_hz=50.0,
        gear_ratio=100.0,
    )


def linear_speed_m_min(
    calculator: WindingCalculator,
    speed_percent: float,
) -> float:
    rpm = calculator.roller_rpm(speed_percent)

    return math.pi * calculator.current_diameter_m * rpm


def test_linear_speed_is_constant_while_diameter_grows(
    calculator: WindingCalculator,
) -> None:
    calculator.set_turns(0.0)
    speed_at_start = linear_speed_m_min(
        calculator,
        speed_percent=100.0,
    )

    calculator.set_turns(50.0)
    speed_in_middle = linear_speed_m_min(
        calculator,
        speed_percent=100.0,
    )

    calculator.set_turns(100.0)
    speed_at_end = linear_speed_m_min(
        calculator,
        speed_percent=100.0,
    )

    assert speed_in_middle == pytest.approx(speed_at_start)
    assert speed_at_end == pytest.approx(speed_at_start)


def test_frequency_decreases_as_roll_diameter_grows(
    calculator: WindingCalculator,
) -> None:
    calculator.set_turns(0.0)
    start_frequency = calculator.frequency_hz(100.0)

    calculator.set_turns(50.0)
    middle_frequency = calculator.frequency_hz(100.0)

    calculator.set_turns(100.0)
    end_frequency = calculator.frequency_hz(100.0)

    assert start_frequency > middle_frequency > end_frequency


def test_operator_percent_scales_linear_speed(
    calculator: WindingCalculator,
) -> None:
    calculator.set_turns(50.0)

    speed_100 = linear_speed_m_min(
        calculator,
        speed_percent=100.0,
    )

    speed_75 = linear_speed_m_min(
        calculator,
        speed_percent=75.0,
    )

    speed_50 = linear_speed_m_min(
        calculator,
        speed_percent=50.0,
    )

    assert speed_75 == pytest.approx(speed_100 * 0.75)
    assert speed_50 == pytest.approx(speed_100 * 0.50)


def test_operator_percent_scales_curve_without_changing_its_shape(
    calculator: WindingCalculator,
) -> None:
    calculator.set_turns(0.0)
    start_100 = calculator.frequency_hz(100.0)
    start_50 = calculator.frequency_hz(50.0)

    calculator.set_turns(100.0)
    end_100 = calculator.frequency_hz(100.0)
    end_50 = calculator.frequency_hz(50.0)

    assert start_50 == pytest.approx(start_100 * 0.5)
    assert end_50 == pytest.approx(end_100 * 0.5)

    ratio_100 = end_100 / start_100
    ratio_50 = end_50 / start_50

    assert ratio_50 == pytest.approx(ratio_100)


def test_reverse_path_uses_same_physical_curve(
    calculator: WindingCalculator,
) -> None:
    calculator.set_turns(100.0)
    frequency_at_material_end = calculator.frequency_hz(100.0)

    calculator.set_turns(50.0)
    frequency_in_middle = calculator.frequency_hz(100.0)

    calculator.set_turns(0.0)
    frequency_at_material_start = calculator.frequency_hz(100.0)

    assert frequency_at_material_end < frequency_in_middle < frequency_at_material_start
