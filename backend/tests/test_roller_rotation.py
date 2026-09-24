import pytest

from app.services.winding.rotation import RollerRotationCalculator


def create_calculator() -> RollerRotationCalculator:
    return RollerRotationCalculator(
        motor_rpm_at_50hz=905,
        gear_ratio=100,
    )


def test_motor_rpm_at_50hz():
    calculator = create_calculator()

    assert calculator.motor_rpm(50) == pytest.approx(905)


def test_motor_rpm_at_25hz():
    calculator = create_calculator()

    assert calculator.motor_rpm(25) == pytest.approx(452.5)


def test_roller_rpm_at_50hz():
    calculator = create_calculator()

    assert calculator.roller_rpm(50) == pytest.approx(9.05)


def test_roller_rpm_at_30hz():
    calculator = create_calculator()

    assert calculator.roller_rpm(30) == pytest.approx(5.43)


def test_revolutions_at_50hz_for_one_minute():
    calculator = create_calculator()

    revolutions = calculator.revolutions_for_time(
        frequency_hz=50,
        elapsed_seconds=60,
    )

    assert revolutions == pytest.approx(9.05)


def test_revolutions_at_30hz_for_one_minute():
    calculator = create_calculator()

    revolutions = calculator.revolutions_for_time(
        frequency_hz=30,
        elapsed_seconds=60,
    )

    assert revolutions == pytest.approx(5.43)


def test_revolutions_for_half_minute():
    calculator = create_calculator()

    revolutions = calculator.revolutions_for_time(
        frequency_hz=50,
        elapsed_seconds=30,
    )

    assert revolutions == pytest.approx(4.525)


def test_negative_frequency():
    calculator = create_calculator()

    with pytest.raises(ValueError):
        calculator.motor_rpm(-1)


def test_negative_elapsed_time():
    calculator = create_calculator()

    with pytest.raises(ValueError):
        calculator.revolutions_for_time(
            frequency_hz=50,
            elapsed_seconds=-1,
        )


def test_zero_frequency():
    calculator = create_calculator()

    assert calculator.motor_rpm(0) == 0
    assert calculator.roller_rpm(0) == 0
    assert (
        calculator.revolutions_for_time(
            frequency_hz=0,
            elapsed_seconds=60,
        )
        == 0
    )


def test_invalid_motor_rpm():
    with pytest.raises(ValueError):
        RollerRotationCalculator(
            motor_rpm_at_50hz=0,
            gear_ratio=100,
        )


def test_invalid_gear_ratio():
    with pytest.raises(ValueError):
        RollerRotationCalculator(
            motor_rpm_at_50hz=905,
            gear_ratio=0,
        )
