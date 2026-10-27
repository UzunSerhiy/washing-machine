"""31B: Modbus telemetry failures must latch before any new motion; mocks only."""
from unittest.mock import Mock

import pytest

from app.services.machine.machine import Machine


def setup_machine():
    brush, roller = Mock(), Mock()
    brush.left_drive.get_fault.return_value = 0
    brush.right_drive.get_fault.return_value = 0
    roller.drive.get_fault.return_value = 0
    machine = Machine(brush, roller, enforce_motion_preflight=True)
    return machine, brush, roller


@pytest.mark.parametrize('failed_drive', ['left', 'right', 'roller'])
def test_rs485_timeout_on_motion_preflight_latches_and_never_dispatches(failed_drive):
    machine, brush, roller = setup_machine()
    old_epoch = machine.capture_session_generation()
    target = {'left': brush.left_drive, 'right': brush.right_drive, 'roller': roller.drive}[failed_drive]
    target.get_fault.side_effect = TimeoutError('RS485 timeout')
    with pytest.raises(RuntimeError, match='telemetry unavailable'):
        machine.start_roller_forward(12, session_generation=old_epoch)
    assert machine.motion_fault_latched is not None
    brush.start.assert_not_called()
    roller.forward.assert_not_called()
    roller.reverse.assert_not_called()
    for drive in (brush.left_drive, brush.right_drive, roller.drive):
        drive.stop.assert_called_once()
    target.get_fault.side_effect = None
    target.get_fault.return_value = 0
    with pytest.raises(RuntimeError, match='latched'):
        machine.start_roller_forward(12, session_generation=old_epoch)
    roller.forward.assert_not_called()


def test_monitor_detects_timeout_and_does_not_auto_clear_on_reconnection():
    machine, brush, roller = setup_machine()
    brush.right_drive.get_fault.side_effect = TimeoutError('bus timeout')
    assert 'telemetry unavailable' in machine.poll_motion_faults()
    generation = machine._motion_generation
    brush.right_drive.get_fault.side_effect = None
    brush.right_drive.get_fault.return_value = 0
    assert machine.poll_motion_faults() == machine.motion_fault_latched
    assert machine._motion_generation == generation
    with pytest.raises(RuntimeError, match='latched'):
        machine.start_brush(10)
    brush.start.assert_not_called()


def test_stop_timeout_does_not_erase_original_communication_fault():
    machine, brush, roller = setup_machine()
    roller.drive.get_fault.side_effect = TimeoutError('bus timeout')
    roller.drive.stop.side_effect = TimeoutError('STOP timeout')
    with pytest.raises(RuntimeError, match='telemetry unavailable'):
        machine.start_brush(10)
    assert 'telemetry unavailable' in machine.motion_fault_latched
    assert machine._roller_stop_fault is True
    with pytest.raises(RuntimeError, match='latched'):
        machine.start_brush(10)
    brush.start.assert_not_called()
