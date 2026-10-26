from unittest.mock import Mock

import pytest

from app.services.machine.auto.drive_motion import read_roller_drive_sample


def drive(status=1, frequency=20.0, fault=0):
    return Mock(get_status=Mock(return_value=status), get_frequency=Mock(return_value=frequency), get_fault=Mock(return_value=fault))


@pytest.mark.parametrize("status,direction", [(1, 1), (2, -1), (3, 0)])
def test_drive_status_direction(status, direction):
    sample = read_roller_drive_sample(drive(status=status, frequency=0 if status == 3 else 20))
    assert sample.direction == direction
    assert sample.frequency_hz == (0 if status == 3 else 20)


@pytest.mark.parametrize("status,frequency,fault", [(4, 0, 0), (3, 5, 0), (1, -1, 0), (1, float('nan'), 0), (1, 20, 7)])
def test_invalid_telemetry_rejected(status, frequency, fault):
    with pytest.raises(RuntimeError):
        read_roller_drive_sample(drive(status, frequency, fault))


def test_communication_error_rejected():
    d = drive()
    d.get_frequency.side_effect = TimeoutError()
    with pytest.raises(RuntimeError, match="unavailable"):
        read_roller_drive_sample(d)


def test_elapsed_time_must_be_valid():
    sample = read_roller_drive_sample(drive())
    with pytest.raises(ValueError):
        sample.as_motion(elapsed_seconds=0, sensor=Mock())
