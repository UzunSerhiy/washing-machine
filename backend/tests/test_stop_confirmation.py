from unittest.mock import Mock
import pytest

from app.services.machine.calibration.stop_confirmation import observe_drive_stop


def drive(*, status=3, frequency=0.0, fault=0):
    return Mock(get_status=Mock(return_value=status), get_frequency=Mock(return_value=frequency), get_fault=Mock(return_value=fault))


def test_stopped_and_zero_frequency():
    assert observe_drive_stop(drive()).confirmed is True


@pytest.mark.parametrize("status,frequency,fault", [(1, 0.0, 0), (2, 0.0, 0), (3, 2.0, 0), (3, 0.0, 1)])
def test_not_confirmed(status, frequency, fault):
    assert observe_drive_stop(drive(status=status, frequency=frequency, fault=fault)).confirmed is False


@pytest.mark.parametrize("status,frequency,fault", [(None, 0.0, 0), (True, 0.0, 0), (3, float('nan'), 0), (3, -1, 0), (3, 0.0, None)])
def test_invalid_telemetry_fails_closed(status, frequency, fault):
    with pytest.raises(RuntimeError):
        observe_drive_stop(drive(status=status, frequency=frequency, fault=fault))


def test_communication_failure_fails_closed():
    d = drive()
    d.get_status.side_effect = OSError('RS485 disconnected')
    with pytest.raises(RuntimeError, match='unavailable'):
        observe_drive_stop(d)


def test_invalid_tolerance():
    with pytest.raises(ValueError):
        observe_drive_stop(drive(), frequency_tolerance_hz=-1)
