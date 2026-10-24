from unittest.mock import Mock

import pytest

from app.services.machine.roller_homing_service import (
    RollerHomingService,
)

from app.services.machine.calibration.homing import HomingState


def make_service():
    machine = Mock()
    machine.roller_owner = None

    def acquire(owner):
        if machine.roller_owner is not None:
            raise RuntimeError("Roller already reserved")
        machine.roller_owner = owner

    def release(owner):
        if machine.roller_owner != owner:
            raise RuntimeError("Owner mismatch")
        machine.roller_owner = None

    machine.acquire_roller.side_effect = acquire
    machine.release_roller.side_effect = release

    sensor = Mock()
    sensor.get_state.return_value = Mock(
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
        sensor_service=sensor,
        rotation_calculator=calculator,
    )

    return service, machine, sensor


def test_homing_acquires_roller():
    service, machine, _ = make_service()

    service.start(position_confirmed=True)

    assert machine.roller_owner == "homing"
    machine.start_roller_reverse.assert_called_once_with(
        10.0,
        owner="homing",
    )


def test_cancel_releases_roller():
    service, machine, _ = make_service()

    service.start(position_confirmed=True)
    service.cancel()

    assert machine.roller_owner is None
    machine.stop_roller.assert_called_once_with(
        owner="homing",
    )


def test_cancel_stop_failure_keeps_ownership():
    service, machine, _ = make_service()

    service.start(position_confirmed=True)
    machine.stop_roller.side_effect = RuntimeError("Modbus STOP failed")

    with pytest.raises(RuntimeError):
        service.cancel()

    assert service.faulted
    assert machine.roller_owner == "homing"


def test_start_failure_keeps_ownership():
    service, machine, _ = make_service()

    machine.start_roller_reverse.side_effect = RuntimeError("Modbus error")

    with pytest.raises(RuntimeError):
        service.start(position_confirmed=True)

    assert service.faulted
    assert machine.roller_owner == "homing"


def test_sensor_validation_releases_ownership():
    service, machine, sensor = make_service()
    sensor.get_state.return_value.connected = False

    with pytest.raises(RuntimeError):
        service.start(position_confirmed=True)

    assert machine.roller_owner is None


def test_homing_completion_releases_ownership():
    service, machine, sensor = make_service()

    service.start(position_confirmed=True)

    sensor.get_state.return_value.triggered = True
    sensor.get_state.return_value.pulses = 1
    sensor.get_state.return_value.sequence = 2

    service.tick()

    assert service.homed
    assert machine.roller_owner is None
    machine.stop_roller.assert_called_once_with(
        owner="homing",
    )


def test_completion_stop_failure_latches_fault():
    service, machine, sensor = make_service()

    service.start(position_confirmed=True)

    sensor.get_state.return_value.triggered = True
    sensor.get_state.return_value.pulses = 1
    sensor.get_state.return_value.sequence = 2

    machine.stop_roller.side_effect = RuntimeError("STOP failed")

    with pytest.raises(RuntimeError):
        service.tick()

    assert service.faulted
    assert not service.homed
    assert machine.roller_owner == "homing"


def test_external_stop_cancels_homing_without_second_stop():
    service, machine, _ = make_service()

    service.start(position_confirmed=True)

    assert service.searching
    assert machine.roller_owner == "homing"

    service.external_stop()

    assert not service.searching
    assert not service.homed
    assert service.homing.state == HomingState.CANCELLED
    assert machine.roller_owner is None

    machine.stop_roller.assert_not_called()
