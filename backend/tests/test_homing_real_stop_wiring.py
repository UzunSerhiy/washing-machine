from unittest.mock import Mock
import pytest

from app.services.machine.calibration.stop_observer_factory import make_roller_stop_observer


def test_observer_uses_roller_drive_and_confirms_stopped():
    drive = Mock()
    drive.get_fault.return_value = 0
    drive.get_status.return_value = 3
    drive.get_frequency.return_value = 0.0
    machine = Mock()
    machine.roller.drive = drive
    observation = make_roller_stop_observer(machine)()
    assert observation.confirmed
    drive.get_fault.assert_called_once()
    drive.get_status.assert_called_once()
    drive.get_frequency.assert_called_once()


def test_observer_rejects_running_drive():
    drive = Mock()
    drive.get_fault.return_value = 0
    drive.get_status.return_value = 2
    drive.get_frequency.return_value = 3.0
    machine = Mock()
    machine.roller.drive = drive
    assert not make_roller_stop_observer(machine)().confirmed


def test_observer_fails_closed_on_modbus_error():
    drive = Mock()
    drive.get_fault.side_effect = TimeoutError('Modbus timeout')
    machine = Mock()
    machine.roller.drive = drive
    with pytest.raises(RuntimeError, match='telemetry unavailable'):
        make_roller_stop_observer(machine)()
