"""Step 28B: simulated process restarts, no motor commands."""
from unittest.mock import Mock
import json
import pytest

from app.services.machine.machine import Machine
from app.services.machine.motion_fault_store import MotionFaultStore


def build(store):
    drives = [Mock() for _ in range(3)]
    for drive in drives:
        drive.get_fault.return_value = 0
        drive.get_status.return_value = 3
        drive.get_frequency.return_value = 0.0
    machine = Machine(Mock(left_drive=drives[0], right_drive=drives[1]),
                      Mock(drive=drives[2]), enforce_motion_preflight=True,
                      motion_fault_store=store)
    return machine, drives


def test_missing_state_blocks_startup(tmp_path):
    machine, drives = build(MotionFaultStore(tmp_path / 'state.json'))
    assert machine.motion_fault_latched
    with pytest.raises(RuntimeError, match='latched'):
        machine.start_brush(10)
    for drive in drives:
        drive.run_forward.assert_not_called()


def test_fault_survives_new_machine_instance(tmp_path):
    store = MotionFaultStore(tmp_path / 'state.json')
    store.write_latch(None)
    machine, drives = build(store)
    drives[2].get_fault.return_value = 15
    assert machine.poll_motion_faults()
    restarted, _ = build(store)
    assert restarted.motion_fault_latched == machine.motion_fault_latched
    with pytest.raises(RuntimeError, match='latched'):
        restarted.start_brush(10)


def test_acknowledged_state_survives_restart(tmp_path):
    store = MotionFaultStore(tmp_path / 'state.json')
    store.write_latch('E15')
    machine, _ = build(store)
    machine.complete_motion_fault_recovery()
    restarted, _ = build(store)
    assert restarted.motion_fault_latched is None


@pytest.mark.parametrize('contents', ['{', '{}', '{"version":1,"acknowledged":true,"reason":"E15"}'])
def test_corrupt_state_blocks_startup(tmp_path, contents):
    path = tmp_path / 'state.json'
    path.write_text(contents)
    machine, _ = build(MotionFaultStore(path))
    assert machine.motion_fault_latched


def test_failed_persist_cannot_clear_latch(tmp_path, monkeypatch):
    store = MotionFaultStore(tmp_path / 'state.json')
    store.write_latch('E15')
    machine, _ = build(store)
    def fail(_):
        raise OSError('disk full')
    monkeypatch.setattr(store, 'write_latch', fail)
    with pytest.raises(RuntimeError, match='Cannot persist'):
        machine.complete_motion_fault_recovery()
    assert machine.motion_fault_latched == 'E15'


def test_failed_fault_write_keeps_memory_latch(tmp_path, monkeypatch):
    store = MotionFaultStore(tmp_path / 'state.json')
    store.write_latch(None)
    machine, drives = build(store)
    drives[2].get_fault.return_value = 15
    monkeypatch.setattr(store, 'write_latch', Mock(side_effect=OSError('disk full')))
    assert machine.poll_motion_faults()
    assert machine.motion_fault_latched
