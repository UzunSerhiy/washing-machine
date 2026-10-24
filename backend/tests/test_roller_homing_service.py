from unittest.mock import Mock

import pytest

from app.services.machine.calibration.homing import HomingState
from app.services.machine.roller_homing_service import RollerHomingService


def make_service():
    machine = Mock()
    sensor_service = Mock()
    sensor_service.get_state.return_value = Mock(
        connected=True,
        triggered=False,
        pulses=0,
        sequence=1,
        generation=1,
    )

    calculator = Mock()
    calculator.revolutions_for_time.return_value = 0.01

    service = RollerHomingService(
        machine=machine,
        sensor_service=sensor_service,
        rotation_calculator=calculator,
    )
    return service, machine, sensor_service


def test_start_homing():
    service, machine, _ = make_service()

    service.start(position_confirmed=True)

    assert service.searching
    assert not service.homed
    machine.start_roller_reverse.assert_called_once_with(10.0, owner="homing")


def test_requires_operator_confirmation():
    service, machine, _ = make_service()

    with pytest.raises(RuntimeError):
        service.start(position_confirmed=False)

    machine.start_roller_reverse.assert_not_called()


def test_cancel_stops_roller():
    service, machine, _ = make_service()

    service.start(position_confirmed=True)
    service.cancel()

    assert service.homing.state == HomingState.CANCELLED
    assert not service.homed
    machine.stop_roller.assert_called_once()


def test_repeat_homing_after_cancel():
    service, machine, _ = make_service()

    service.start(position_confirmed=True)
    service.cancel()

    service.start(position_confirmed=True)

    assert service.searching
    assert machine.start_roller_reverse.call_count == 2


def test_invalid_frequency():
    service, _, _ = make_service()

    with pytest.raises(ValueError):
        service.start(
            position_confirmed=True,
            frequency_hz=15.0,
        )


def test_start_failure_sets_fault():
    service, machine, _ = make_service()
    machine.start_roller_reverse.side_effect = RuntimeError("RS485 error")

    with pytest.raises(RuntimeError):
        service.start(position_confirmed=True)

    assert service.faulted
    assert not service.homed
    machine.stop_roller.assert_called()


def test_require_zero_before_homing():
    homing_service, _, _ = make_service()
    with pytest.raises(RuntimeError):
        homing_service.require_zero()


def test_manual_movement_invalidates_zero():
    homing_service, _, _ = make_service()
    homing_service._homed = True

    assert homing_service.homed is True

    homing_service.invalidate()

    assert homing_service.homed is False

    with pytest.raises(RuntimeError):
        homing_service.require_zero()
