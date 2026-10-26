from unittest.mock import Mock
import pytest

from app.services.machine.auto.telemetry_freshness import (
    TimedAutoDiagnostics, read_timed_auto_diagnostics,
)
from app.services.machine.sensors.roller_reference import RollerReferenceState


def devices():
    drive = Mock()
    drive.get_fault.return_value = 0
    drive.get_status.return_value = 3
    drive.get_frequency.return_value = 0.0
    sensor = Mock()
    sensor.get_state.return_value = RollerReferenceState(True, False, 0, 0)
    io = Mock()
    io.status.return_value = {"connected": True}
    return drive, sensor, io


def test_stationary_sensor_is_valid_when_connected_and_fresh():
    drive, sensor, io = devices()
    times = iter([10.0, 10.1])
    result = read_timed_auto_diagnostics(
        roller_drive=drive, roller_sensor=sensor, io_controller=io, clock=lambda: next(times)
    )
    result.validate(now=10.2, max_age_seconds=1.0, max_read_seconds=0.5)
    assert result.diagnostics.reference.pulses == 0
    assert result.diagnostics.roller.direction == 0
    assert not any(call[0].startswith("set_") for call in drive.method_calls)


def test_reject_stale_snapshot():
    sample = TimedAutoDiagnostics(Mock(), 1.0, 1.1)
    with pytest.raises(RuntimeError, match="stale"):
        sample.validate(now=3.0, max_age_seconds=1, max_read_seconds=0.5)


def test_reject_slow_sequential_reads():
    sample = TimedAutoDiagnostics(Mock(), 1.0, 2.0)
    with pytest.raises(RuntimeError, match="too long"):
        sample.validate(now=2.0, max_age_seconds=3, max_read_seconds=0.5)


def test_reject_clock_rollback_and_invalid_limits():
    sample = TimedAutoDiagnostics(Mock(), 2.0, 2.1)
    with pytest.raises(RuntimeError, match="timestamp"):
        sample.validate(now=2.0, max_age_seconds=1, max_read_seconds=1)
    with pytest.raises(ValueError, match="positive"):
        sample.validate(now=3.0, max_age_seconds=0, max_read_seconds=1)
