"""Safety regression tests for HOME, sensor faults and emergency STOP (FAKE only)."""

from unittest.mock import Mock

import pytest

from app.services.machine.calibration.homing import HomingState
from app.services.machine.machine import Machine
from app.services.machine.roller import Roller
from app.services.machine.roller_homing_service import RollerHomingService


def make_homing():
    left, right, roller_drive = Mock(), Mock(), Mock()
    brush = Mock(left_drive=left, right_drive=right)
    machine = Machine(brush=brush, roller=Roller(drive=roller_drive))
    sensor = Mock()
    state = Mock(connected=True, triggered=False, pulses=0, sequence=1, generation=1)
    sensor.get_state.return_value = state
    rotation = Mock()
    rotation.revolutions_for_time.return_value = 0.01
    home = RollerHomingService(machine, sensor, rotation)
    machine.set_roller_external_stop_callback(home.external_stop)
    home.start(position_confirmed=True)
    return home, machine, state, (left, right, roller_drive), rotation


@pytest.mark.parametrize("fault", ["disconnected", "generation", "sequence", "pulses"])
def test_sensor_fault_latches_home_and_keeps_ownership(fault):
    home, machine, state, drives, _ = make_homing()
    if fault == "disconnected":
        state.connected = False
    elif fault == "generation":
        state.generation += 1
    elif fault == "sequence":
        state.sequence = 0
    else:
        state.pulses = -1

    home.tick()

    assert home.faulted
    assert home.homing.state == HomingState.ERROR
    assert not home.homed
    assert machine.roller_owner == "homing"
    drives[2].stop.assert_called_once()
    with pytest.raises(RuntimeError, match="reserved"):
        machine.start_roller_forward(10)


def test_home_timeout_stops_and_latches_fault():
    home, machine, _, drives, _ = make_homing()
    started = home.homing._started_at
    home.clock = Mock(now=Mock(return_value=started + 61))
    home.tick()
    assert home.faulted
    assert "timeout" in home.get_status()["error"].lower()
    assert machine.roller_owner == "homing"
    drives[2].stop.assert_called_once()


def test_home_travel_limit_stops_and_latches_fault():
    home, machine, _, drives, rotation = make_homing()
    rotation.revolutions_for_time.return_value = 1.21
    home.tick()
    assert home.faulted
    assert "travel limit" in home.get_status()["error"].lower()
    assert machine.roller_owner == "homing"
    drives[2].stop.assert_called_once()


def test_emergency_stop_cancels_home_and_stops_every_drive():
    home, machine, _, drives, _ = make_homing()
    machine.stop_all()
    assert [d.stop.call_count for d in drives] == [1, 1, 1]
    assert home.homing.state == HomingState.CANCELLED
    assert not home.homed
    assert machine.roller_owner is None


def test_emergency_stop_attempts_other_drives_after_one_fails():
    home, machine, _, drives, _ = make_homing()
    drives[0].stop.side_effect = RuntimeError("brush failure")
    with pytest.raises(RuntimeError, match="left_brush"):
        machine.stop_all()
    assert [d.stop.call_count for d in drives] == [1, 1, 1]
    assert not home.homed
    assert machine.roller_owner is None


def test_emergency_roller_stop_failure_keeps_home_owner():
    home, machine, _, drives, _ = make_homing()
    drives[2].stop.side_effect = RuntimeError("roller failure")
    with pytest.raises(RuntimeError, match="roller"):
        machine.stop_all()
    assert [d.stop.call_count for d in drives] == [1, 1, 1]
    assert machine.roller_owner == "homing"
    assert not home.homed


def test_manual_motion_blocked_while_homing():
    _, machine, _, drives, _ = make_homing()
    with pytest.raises(RuntimeError, match="reserved"):
        machine.start_roller_reverse(10)
    with pytest.raises(RuntimeError, match="reserved"):
        machine.start_roller_forward(10)
    assert drives[2].run_forward.call_count == 0
    assert drives[2].run_reverse.call_count == 1
