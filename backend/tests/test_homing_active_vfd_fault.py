from unittest.mock import Mock
import pytest
from app.services.machine.roller_homing_service import RollerHomingService
from app.services.machine.calibration.stop_confirmation import StopObservation
from app.services.machine.calibration.stop_observer_factory import make_roller_fault_observer


def make_service(fault):
    machine = Mock()
    sensor = Mock()
    sensor.get_state.return_value = Mock(connected=True, triggered=False, pulses=0, sequence=1, generation=1)
    calc = Mock()
    calc.revolutions_for_time.return_value = 0.01
    observer = Mock(return_value=fault) if not isinstance(fault, Exception) else Mock(side_effect=fault)
    service = RollerHomingService(machine, sensor, calc, fault_observer=observer)
    service.start(position_confirmed=True)
    return service, machine, observer


@pytest.mark.parametrize('fault', [15, 1, 65535])
def test_active_fault_latches_and_invalidates_home(fault):
    service, machine, _ = make_service(fault)
    with pytest.raises(RuntimeError, match=f'VFD fault {fault}'):
        service.tick()
    status = service.get_status()
    assert status['faulted'] and not status['homed']
    assert status['fault_code'] == 'VFD_FAULT'
    machine.stop_roller.assert_called_once_with(owner='homing')
    machine.release_roller.assert_not_called()
    with pytest.raises(RuntimeError, match='latched'):
        service.start(position_confirmed=True)


@pytest.mark.parametrize('fault', [None, True, -1, '15', 65536])
def test_invalid_fault_telemetry_latches(fault):
    service, _, _ = make_service(fault)
    with pytest.raises(RuntimeError, match='telemetry invalid'):
        service.tick()
    assert service.get_status()['fault_code'] == 'VFD_TELEMETRY_UNAVAILABLE'


def test_modbus_failure_latches():
    service, _, _ = make_service(TimeoutError('RS485 lost'))
    with pytest.raises(RuntimeError, match='telemetry unavailable'):
        service.tick()
    assert service.get_status()['fault_code'] == 'VFD_TELEMETRY_UNAVAILABLE'


def test_healthy_telemetry_does_not_interrupt_search():
    service, machine, observer = make_service(0)
    service.tick()
    assert service.searching
    assert not service.faulted
    observer.assert_called_once()
    machine.stop_roller.assert_not_called()


def test_stop_confirmation_rejects_vfd_fault_immediately():
    machine = Mock()
    sensor = Mock()
    sensor.get_state.side_effect = [
        Mock(connected=True, triggered=False, pulses=0, sequence=1, generation=1),
        Mock(connected=True, triggered=True, pulses=1, sequence=2, generation=1),
    ]
    calc = Mock()
    calc.revolutions_for_time.return_value = 0.01
    observer = Mock(return_value=StopObservation(3, 0.0, 15, False))
    service = RollerHomingService(machine, sensor, calc, stop_observer=observer)
    service.start(position_confirmed=True)
    service.tick()
    with pytest.raises(RuntimeError, match='VFD fault 15'):
        service.tick()
    assert service.get_status()['fault_code'] == 'VFD_FAULT'
    assert not service.homed


def test_factory_reads_actual_roller_drive():
    machine = Mock()
    machine.roller.drive.get_fault.return_value = 15
    assert make_roller_fault_observer(machine)() == 15
    machine.roller.drive.get_fault.assert_called_once()
