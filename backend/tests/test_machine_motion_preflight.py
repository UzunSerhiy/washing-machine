from unittest.mock import Mock

import pytest

from app.services.machine.machine import Machine
from app.services.machine.roller import Roller
from app.services.machine.brush import Brush


def make_machine():
    left, right, roller = Mock(), Mock(), Mock()
    for drive in (left, right, roller):
        drive.get_fault.return_value = 0
    return Machine(Brush(left, right), Roller(roller), enforce_motion_preflight=True), left, right, roller


@pytest.mark.parametrize('method', ['start_brush', 'start_roller_forward', 'start_roller_reverse'])
def test_fault_blocks_every_entry(method):
    machine, left, right, roller = make_machine()
    right.get_fault.return_value = 15
    with pytest.raises(RuntimeError, match='right_brush VFD fault 15'):
        getattr(machine, method)(10)
    for drive in (left, right, roller):
        drive.set_frequency.assert_not_called()
        drive.run_forward.assert_not_called()
        drive.run_reverse.assert_not_called()


@pytest.mark.parametrize('bad', [None, True, -1, 65536, '0'])
def test_invalid_telemetry_fails_closed(bad):
    machine, left, right, roller = make_machine()
    roller.get_fault.return_value = bad
    with pytest.raises(RuntimeError, match='invalid fault telemetry'):
        machine.start_brush(10)
    left.run_forward.assert_not_called()


def test_unavailable_telemetry_fails_closed():
    machine, left, right, roller = make_machine()
    left.get_fault.side_effect = OSError('serial unavailable')
    with pytest.raises(RuntimeError, match='telemetry unavailable'):
        machine.start_roller_forward(10)
    roller.run_forward.assert_not_called()


def test_running_other_drive_is_not_a_blocker():
    machine, left, right, roller = make_machine()
    left.get_status.return_value = 1
    left.get_frequency.return_value = 25
    machine.start_roller_forward(10)
    roller.run_forward.assert_called_once()


def test_stop_still_available_on_fault():
    machine, left, right, roller = make_machine()
    roller.get_fault.return_value = 15
    machine.stop_roller()
    roller.stop.assert_called_once()
    machine.stop_brush()
    left.stop.assert_called_once()
    right.stop.assert_called_once()


def test_disabled_guard_preserves_fake_and_unit_test_behavior():
    left, right, roller = Mock(), Mock(), Mock()
    machine = Machine(Brush(left, right), Roller(roller))
    machine.start_brush(10)
    left.get_fault.assert_not_called()
    left.run_forward.assert_called_once()
