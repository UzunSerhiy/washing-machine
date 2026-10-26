from unittest.mock import Mock
import pytest

from app.services.machine.auto.real_diagnostics import read_real_auto_diagnostics
from app.services.machine.sensors.roller_reference import RollerReferenceState


def devices(*, connected=True):
    drive = Mock()
    drive.get_fault.return_value = 0
    drive.get_status.return_value = 1
    drive.get_frequency.return_value = 20.0
    sensor = Mock()
    sensor.get_state.return_value = RollerReferenceState(connected, False, 3, 4)
    io = Mock()
    io.status.return_value = {"connected": True, "water": False, "light": False}
    return drive, sensor, io


def test_snapshot_is_read_only():
    drive, sensor, io = devices()
    result = read_real_auto_diagnostics(roller_drive=drive, roller_sensor=sensor, io_controller=io)
    assert result.roller.frequency_hz == 20
    assert result.reference.pulses == 3
    assert result.io["connected"] is True
    assert drive.method_calls == [
        __import__('unittest').mock.call.get_fault(),
        __import__('unittest').mock.call.get_status(),
        __import__('unittest').mock.call.get_frequency(),
    ]
    sensor.get_state.assert_called_once_with()
    io.status.assert_called_once_with()


def test_disconnected_sensor_rejected_without_io_access():
    drive, sensor, io = devices(connected=False)
    with pytest.raises(RuntimeError, match="sensor unavailable"):
        read_real_auto_diagnostics(roller_drive=drive, roller_sensor=sensor, io_controller=io)
    io.status.assert_not_called()


def test_drive_fault_rejected_before_sensor_access():
    drive, sensor, io = devices()
    drive.get_fault.return_value = 2
    with pytest.raises(RuntimeError, match="fault"):
        read_real_auto_diagnostics(roller_drive=drive, roller_sensor=sensor, io_controller=io)
    sensor.get_state.assert_not_called()
