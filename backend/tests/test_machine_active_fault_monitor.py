from unittest.mock import Mock

import pytest

from app.services.machine.machine import Machine
from app.services.machine.brush import Brush
from app.services.machine.roller import Roller


def setup():
    left, right, roller = Mock(), Mock(), Mock()
    for drive in (left, right, roller):
        drive.get_fault.return_value = 0
    machine = Machine(Brush(left, right), Roller(roller), enforce_motion_preflight=True)
    return machine, left, right, roller


def test_healthy_poll_does_not_stop():
    machine, left, right, roller = setup()
    assert machine.poll_motion_faults() is None
    for drive in (left, right, roller):
        drive.stop.assert_not_called()


def test_active_external_fault_latches_and_requests_stop_all():
    machine, left, right, roller = setup()
    roller.get_fault.return_value = 15
    assert 'VFD fault 15' in machine.poll_motion_faults()
    for drive in (left, right, roller):
        drive.stop.assert_called_once()
    assert machine.motion_fault_latched is not None


def test_physical_reset_does_not_automatically_restart():
    machine, left, right, roller = setup()
    roller.get_fault.return_value = 15
    machine.poll_motion_faults()
    roller.get_fault.return_value = 0
    assert machine.poll_motion_faults() is not None
    with pytest.raises(RuntimeError, match='Motion fault latched'):
        machine.start_brush(10)
    left.run_forward.assert_not_called()


@pytest.mark.parametrize('bad', [None, True, '0', -1])
def test_invalid_telemetry_latches(bad):
    machine, left, right, roller = setup()
    right.get_fault.return_value = bad
    assert 'invalid fault telemetry' in machine.poll_motion_faults()


def test_communication_loss_latches():
    machine, left, right, roller = setup()
    left.get_fault.side_effect = OSError('offline')
    assert 'telemetry unavailable' in machine.poll_motion_faults()


def test_stop_failure_does_not_erase_original_fault():
    machine, left, right, roller = setup()
    roller.get_fault.return_value = 15
    roller.stop.side_effect = OSError('stop failed')
    assert 'VFD fault 15' in machine.poll_motion_faults()
    assert machine.motion_fault_latched is not None


def test_stop_remains_available_after_latch():
    machine, left, right, roller = setup()
    roller.get_fault.return_value = 15
    machine.poll_motion_faults()
    machine.stop_brush()
    assert left.stop.call_count == 2
