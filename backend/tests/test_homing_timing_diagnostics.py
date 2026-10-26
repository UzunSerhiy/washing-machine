from unittest.mock import Mock

import pytest

from app.services.machine.calibration.stop_confirmation import StopObservation
from app.services.machine.roller_homing_service import RollerHomingService


def make_service(observer=None):
    machine = Mock()
    sensor = Mock()
    sensor.get_state.return_value = Mock(connected=True, triggered=False, pulses=0, sequence=1, generation=1)
    calculator = Mock()
    calculator.revolutions_for_time.return_value = 0.01
    service = RollerHomingService(machine, sensor, calculator, stop_observer=observer)
    return service, sensor, machine


def reach_pulse(service, sensor):
    service.start(position_confirmed=True)
    sensor.get_state.return_value = Mock(connected=True, triggered=True, pulses=1, sequence=2, generation=1)
    service.tick()


def test_timing_before_homing_is_empty():
    service, _, _ = make_service()
    timing = service.get_status()['timing']
    assert all(value is None for value in timing['events_monotonic_seconds'].values())
    assert timing['pulse_to_confirmation_ms'] is None


def test_pulse_stop_and_three_telemetry_confirmations_are_recorded():
    observer = Mock(return_value=StopObservation(3, 0.0, 0, True))
    service, sensor, _ = make_service(observer)
    reach_pulse(service, sensor)
    timing = service.get_status()['timing']
    assert timing['pulse_to_stop_request_ms'] >= 0
    assert timing['stop_command_duration_ms'] >= 0
    assert timing['events_monotonic_seconds']['stop_confirmed_at'] is None
    service.tick()
    assert service.get_status()['timing']['stop_confirmations_observed'] == 1
    service.tick()
    service.tick()
    assert service.homed
    timing = service.get_status()['timing']
    assert timing['pulse_to_confirmation_ms'] >= 0
    assert timing['stop_request_to_confirmation_ms'] >= 0
    assert timing['stop_confirmations_observed'] == 0  # reset on completion


def test_timing_survives_telemetry_fault():
    service, sensor, _ = make_service(Mock(side_effect=RuntimeError('RS485 lost')))
    reach_pulse(service, sensor)
    with pytest.raises(RuntimeError, match='RS485 lost'):
        service.tick()
    timing = service.get_status()['timing']
    assert timing['events_monotonic_seconds']['stop_requested_at'] is not None
    assert timing['events_monotonic_seconds']['stop_confirmed_at'] is None
    assert not service.homed


def test_timing_is_reset_on_next_start():
    service, sensor, _ = make_service()
    reach_pulse(service, sensor)
    assert service.homed
    sensor.get_state.return_value = Mock(connected=True, triggered=False, pulses=1, sequence=3, generation=1)
    service.start(position_confirmed=True)
    assert all(value is None for value in service.get_status()['timing']['events_monotonic_seconds'].values())
