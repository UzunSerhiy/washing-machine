"""HOME epoch regressions: mock drives and sensors only, never real hardware."""
from unittest.mock import Mock

import pytest

from app.services.machine.brush import Brush
from app.services.machine.roller import Roller
from app.services.machine.machine import Machine
from app.services.machine.roller_homing_service import RollerHomingService


def make_service():
    drives = [Mock() for _ in range(3)]
    for drive in drives:
        drive.get_fault.return_value = 0
    machine = Machine(Brush(*drives[:2]), Roller(drives[2]), enforce_motion_preflight=True)
    sensor = Mock()
    sensor.get_state.return_value = Mock(connected=True, triggered=False, pulses=0, sequence=1, generation=1)
    calc = Mock()
    calc.revolutions_for_time.return_value = 0.01
    return RollerHomingService(machine, sensor, calc), machine, drives


def test_home_dispatch_receives_original_generation():
    home, machine, drives = make_service()
    home.start(position_confirmed=True)
    assert home.searching
    assert home._session_generation == machine.capture_session_generation()
    assert drives[2].set_frequency.called


def test_stale_home_tick_does_not_confirm_zero_or_issue_new_run():
    home, machine, drives = make_service()
    home.start(position_confirmed=True)
    with machine._roller_lock:
        machine._motion_generation += 2  # simulated fault + recovery epoch changes
    count = drives[2].set_frequency.call_count
    with pytest.raises(RuntimeError, match='Stale motion session'):
        home.tick()
    assert not home.homed
    assert home.faulted
    assert drives[2].set_frequency.call_count == count


def test_stale_queued_home_start_rejected_before_run():
    home, machine, drives = make_service()
    original = machine.capture_session_generation

    def change_epoch_after_capture():
        epoch = original()
        with machine._roller_lock:
            machine._motion_generation += 2
        return epoch

    machine.capture_session_generation = change_epoch_after_capture
    with pytest.raises(RuntimeError, match='Stale motion session'):
        home.start(position_confirmed=True)
    assert not home.searching
    assert not home.homed
    drives[2].set_frequency.assert_not_called()
