"""Step 29Z: fail-closed simulated REAL restarts, without hardware or Docker restart."""
import json
from unittest.mock import Mock

import pytest

from app.services.machine.machine import Machine
from app.services.machine.motion_fault_store import MotionFaultStore


def make_machine(store):
    drives = [Mock() for _ in range(3)]
    for drive in drives:
        drive.get_fault.return_value = 0
        drive.get_status.return_value = 3
        drive.get_frequency.return_value = 0.0
    machine = Machine(Mock(left_drive=drives[0], right_drive=drives[1]),
                      Mock(drive=drives[2]), enforce_motion_preflight=True,
                      motion_fault_store=store)
    return machine, drives


def assert_no_run(machine, drives):
    with pytest.raises(RuntimeError, match="latched"):
        machine.start_brush(10)
    with pytest.raises(RuntimeError, match="latched"):
        machine.start_roller_forward(10)
    for drive in drives:
        drive.run_forward.assert_not_called()
        drive.run_reverse.assert_not_called()


def test_e15_latch_survives_restart_and_blocks_run(tmp_path):
    store = MotionFaultStore(tmp_path / "state.json")
    store.write_latch(None)
    machine, drives = make_machine(store)
    drives[2].get_fault.return_value = 15
    assert machine.poll_motion_faults()
    restarted, new_drives = make_machine(store)
    restarted.arm_startup_interlock()
    assert "15" in restarted.motion_fault_latched
    assert store.read_latch() == restarted.motion_fault_latched
    assert_no_run(restarted, new_drives)


def test_acknowledged_state_is_relatched_on_real_startup(tmp_path):
    store = MotionFaultStore(tmp_path / "state.json")
    store.write_latch("E15")
    machine, _ = make_machine(store)
    machine.complete_motion_fault_recovery()
    assert store.read_latch() is None
    restarted, drives = make_machine(store)
    restarted.arm_startup_interlock()
    assert "backend restarted" in restarted.motion_fault_latched
    assert store.read_latch() == restarted.motion_fault_latched
    assert_no_run(restarted, drives)


@pytest.mark.parametrize("contents", [None, "{", "[]", '{"version":1,"acknowledged":true,"reason":"E15"}'])
def test_missing_or_corrupt_state_stays_blocked_after_startup(tmp_path, contents):
    path = tmp_path / "state.json"
    if contents is not None:
        path.write_text(contents, encoding="utf-8")
    store = MotionFaultStore(path)
    machine, drives = make_machine(store)
    machine.arm_startup_interlock()
    assert machine.motion_fault_latched
    assert store.read_latch() == machine.motion_fault_latched
    assert_no_run(machine, drives)


def test_failed_startup_write_refuses_startup_and_blocks_run(tmp_path, monkeypatch):
    store = MotionFaultStore(tmp_path / "state.json")
    store.write_latch(None)
    machine, drives = make_machine(store)
    monkeypatch.setattr(store, "write_latch", Mock(side_effect=OSError("disk full")))
    with pytest.raises(RuntimeError, match="refusing startup"):
        machine.arm_startup_interlock()
    assert machine.motion_fault_latched
    assert_no_run(machine, drives)


def test_failed_fault_persistence_cannot_bypass_next_startup(tmp_path, monkeypatch):
    store = MotionFaultStore(tmp_path / "state.json")
    store.write_latch(None)
    machine, drives = make_machine(store)
    drives[2].get_fault.return_value = 15
    original = store.write_latch
    monkeypatch.setattr(store, "write_latch", Mock(side_effect=OSError("disk full")))
    assert machine.poll_motion_faults()
    assert machine.motion_fault_latched
    assert store.read_latch() is None  # stale disk state is not safe
    monkeypatch.setattr(store, "write_latch", original)
    restarted, new_drives = make_machine(store)
    restarted.arm_startup_interlock()
    assert_no_run(restarted, new_drives)
    assert store.read_latch() is not None
