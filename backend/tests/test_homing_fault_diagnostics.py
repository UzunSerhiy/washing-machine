from unittest.mock import Mock

import pytest

from app.services.machine.calibration.stop_confirmation import StopObservation
from app.services.machine.roller_homing_service import RollerHomingService


def make_service():
    machine = Mock()
    machine.roller_owner = 'homing'
    sensor = Mock()
    sensor.get_state.return_value = Mock(connected=True, triggered=False, pulses=0, sequence=1, generation=1)
    calculator = Mock()
    calculator.revolutions_for_time.return_value = 0.01
    observer = Mock(return_value=StopObservation(2, 1.0, 0, False))
    service = RollerHomingService(machine, sensor, calculator, stop_observer=observer)
    return service, machine, sensor, observer


def awaiting_stop():
    service, machine, sensor, observer = make_service()
    service.start(position_confirmed=True)
    sensor.get_state.return_value = Mock(connected=True, triggered=True, pulses=1, sequence=2, generation=1)
    service.tick()
    assert service.get_status()['awaiting_stop_confirmation']
    return service, machine, observer


def test_stop_timeout_has_error_state_and_code():
    service, machine, _ = awaiting_stop()
    service._stop_deadline = service.clock.now() - 1
    with pytest.raises(RuntimeError, match='timeout'):
        service.tick()
    status = service.get_status()
    assert status['state'] == 'error'
    assert status['fault_code'] == 'STOP_CONFIRMATION_TIMEOUT'
    assert status['faulted'] and not status['homed']
    machine.release_roller.assert_not_called()


def test_stop_telemetry_failure_has_error_state_and_code():
    service, machine, observer = awaiting_stop()
    observer.side_effect = ConnectionError('RS485 unavailable')
    with pytest.raises(ConnectionError):
        service.tick()
    status = service.get_status()
    assert status['state'] == 'error'
    assert status['fault_code'] == 'HOMING_RUNTIME_ERROR'
    assert 'RS485 unavailable' in status['error']
    machine.release_roller.assert_not_called()


def test_sensor_timeout_has_distinct_code():
    service, machine, _, _ = make_service()
    service.start(position_confirmed=True)
    service.homing._started_at = service.clock.now() - 61
    service.tick()
    status = service.get_status()
    assert status['state'] == 'error'
    assert status['fault_code'] == 'SENSOR_TIMEOUT'
    assert status['faulted']
    machine.release_roller.assert_not_called()


def test_stop_command_failure_on_cancel_is_latched():
    service, machine, _, _ = make_service()
    service.start(position_confirmed=True)
    machine.stop_roller.side_effect = RuntimeError('drive unavailable')
    with pytest.raises(RuntimeError, match='drive unavailable'):
        service.cancel()
    status = service.get_status()
    assert status['state'] == 'error'
    assert status['fault_code'] == 'STOP_COMMAND_FAILED'
    assert status['faulted']
    machine.release_roller.assert_not_called()


def test_idle_has_no_fault_code():
    service, _, _, _ = make_service()
    assert service.get_status()['fault_code'] is None
