import pytest

from app.services.winding.rotation import RollerRotationCalculator

from app.services.winding.rotation_counter import RollerRotationCounter


def create_counter() -> RollerRotationCounter:
    calculator = RollerRotationCalculator(
        motor_rpm_at_50hz=905,
        gear_ratio=100,
    )

    return RollerRotationCounter(
        calculator=calculator,
    )


def test_first_update_does_not_add_revolutions():
    counter = create_counter()

    revolutions = counter.update(
        frequency_hz=0,
        elapsed_seconds=0,
    )

    assert revolutions == 0
    assert counter.total_revolutions == 0


def test_constant_frequency():
    counter = create_counter()

    counter.update(
        frequency_hz=30,
        elapsed_seconds=0,
    )

    revolutions = counter.update(
        frequency_hz=30,
        elapsed_seconds=60,
    )

    assert revolutions == pytest.approx(5.43)
    assert counter.total_revolutions == pytest.approx(5.43)


def test_acceleration():
    counter = create_counter()

    counter.update(
        frequency_hz=0,
        elapsed_seconds=0,
    )

    revolutions = counter.update(
        frequency_hz=20,
        elapsed_seconds=60,
    )

    assert revolutions == pytest.approx(1.81)


def test_multiple_updates():
    counter = create_counter()

    counter.update(
        frequency_hz=0,
        elapsed_seconds=0,
    )

    counter.update(
        frequency_hz=20,
        elapsed_seconds=60,
    )

    counter.update(
        frequency_hz=30,
        elapsed_seconds=60,
    )

    assert counter.total_revolutions == pytest.approx(6.335)


def test_reset():
    counter = create_counter()

    counter.update(
        frequency_hz=30,
        elapsed_seconds=0,
    )

    counter.update(
        frequency_hz=30,
        elapsed_seconds=60,
    )

    counter.reset()

    assert counter.total_revolutions == 0
