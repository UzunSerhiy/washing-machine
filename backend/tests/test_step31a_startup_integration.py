"""Step 31A: restart admission contract, with mocked actuators only."""
from unittest.mock import Mock

import pytest

from app.services.machine.machine import Machine
from app.services.machine.motion_fault_store import MotionFaultStore


def make_machine(store):
    brush, roller = Mock(), Mock()
    return Machine(brush, roller, motion_fault_store=store), brush, roller


def assert_no_motion(brush, roller):
    brush.start.assert_not_called()
    roller.forward.assert_not_called()
    roller.reverse.assert_not_called()


def test_clean_disk_restart_blocks_all_motion_entrypoints(tmp_path):
    store = MotionFaultStore(tmp_path / 'fault.json')
    store.write_latch(None)
    machine, brush, roller = make_machine(store)
    machine.arm_startup_interlock()
    assert 'backend restarted' in machine.motion_fault_latched
    assert store.read_latch() == machine.motion_fault_latched
    for command in (lambda: machine.start_brush(10),
                    lambda: machine.start_roller_forward(10),
                    lambda: machine.start_roller_reverse(10)):
        with pytest.raises(RuntimeError, match='latched'):
            command()
    assert_no_motion(brush, roller)


@pytest.mark.parametrize('contents', [None, '{broken json', '{"version":1,"acknowledged":true,"reason":"E15"}'])
def test_missing_or_corrupt_disk_never_opens_motion(tmp_path, contents):
    path = tmp_path / 'fault.json'
    if contents is not None:
        path.write_text(contents)
    machine, brush, roller = make_machine(MotionFaultStore(path))
    machine.arm_startup_interlock()
    assert machine.motion_fault_latched is not None
    with pytest.raises(RuntimeError, match='latched'):
        machine.start_brush(10)
    assert_no_motion(brush, roller)


def test_startup_invalidates_previously_captured_session_epoch(tmp_path):
    store = MotionFaultStore(tmp_path / 'fault.json')
    store.write_latch(None)
    machine, brush, roller = make_machine(store)
    old_epoch = machine.capture_session_generation()
    machine.arm_startup_interlock()
    with pytest.raises(RuntimeError, match='latched'):
        machine.start_roller_forward(10, session_generation=old_epoch)
    assert_no_motion(brush, roller)
