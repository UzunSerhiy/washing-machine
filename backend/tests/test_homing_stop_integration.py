from unittest.mock import Mock
import pytest

from app.services.machine.calibration.stop_confirmation import StopObservation
from app.services.machine.roller_homing_service import RollerHomingService


def service_with_observer(observer):
    machine = Mock()
    sensor = Mock()
    sensor.get_state.return_value = Mock(connected=True, triggered=False, pulses=0, sequence=1, generation=1)
    calculator = Mock()
    calculator.revolutions_for_time.return_value = 0.01
    service = RollerHomingService(machine, sensor, calculator, stop_observer=observer)
    service.start(position_confirmed=True)
    sensor.get_state.return_value = Mock(connected=True, triggered=True, pulses=1, sequence=2, generation=1)
    service.tick()
    assert service.get_status()['awaiting_stop_confirmation']
    assert not service.homed
    return service, machine


def test_three_consecutive_stop_observations():
    observer = Mock(return_value=StopObservation(status=3, frequency_hz=0.0, fault=0, confirmed=True))
    service, machine = service_with_observer(observer)
    for _ in range(2):
        service.tick()
        assert not service.homed
    service.tick()
    assert service.homed
    machine.release_roller.assert_called_once_with('homing')


def test_unconfirmed_observation_resets_counter():
    good = StopObservation(3, 0.0, 0, True)
    bad = StopObservation(2, 2.0, 0, False)
    observer = Mock(side_effect=[good, bad, good, good, good])
    service, _ = service_with_observer(observer)
    for _ in range(4):
        service.tick()
    assert not service.homed
    service.tick()
    assert service.homed


def test_telemetry_failure_latches_fault():
    observer = Mock(side_effect=RuntimeError('RS485 unavailable'))
    service, machine = service_with_observer(observer)
    with pytest.raises(RuntimeError, match='RS485 unavailable'):
        service.tick()
    assert service.faulted
    assert not service.homed
    machine.release_roller.assert_not_called()


def test_timeout_latches_fault():
    observer = Mock(return_value=StopObservation(2, 1.0, 0, False))
    service, _ = service_with_observer(observer)
    service._stop_deadline = service.clock.now() - 1
    with pytest.raises(RuntimeError, match='timeout'):
        service.tick()
    assert service.faulted


def test_cannot_restart_during_stop_confirmation():
    service, _ = service_with_observer(Mock())
    with pytest.raises(RuntimeError, match='awaiting stop confirmation'):
        service.start(position_confirmed=True)
