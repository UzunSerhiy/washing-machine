"""Step 28B.1: restart is fail-closed even after a failed fault write."""
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


def test_clean_state_requires_new_acknowledgement_after_restart(tmp_path):
    store = MotionFaultStore(tmp_path / "state.json")
    store.write_latch(None)
    restarted, drives = make_machine(store)
    restarted.arm_startup_interlock()
    assert restarted.motion_fault_latched is not None
    assert store.read_latch() is not None
    with pytest.raises(RuntimeError, match="latched"):
        restarted.start_brush(10)
    for drive in drives:
        drive.run_forward.assert_not_called()


def test_existing_fault_reason_is_preserved(tmp_path):
    store = MotionFaultStore(tmp_path / "state.json")
    store.write_latch("Motion blocked: roller VFD fault 15")
    machine, _ = make_machine(store)
    machine.arm_startup_interlock()
    assert machine.motion_fault_latched == "Motion blocked: roller VFD fault 15"
    assert store.read_latch() == machine.motion_fault_latched


def test_unwritable_store_prevents_startup(tmp_path, monkeypatch):
    store = MotionFaultStore(tmp_path / "state.json")
    store.write_latch(None)
    machine, _ = make_machine(store)
    monkeypatch.setattr(store, "write_latch", Mock(side_effect=OSError("disk full")))
    with pytest.raises(RuntimeError, match="refusing startup"):
        machine.arm_startup_interlock()
    assert machine.motion_fault_latched is not None


def test_stale_clean_disk_after_failed_fault_write_cannot_bypass_restart(tmp_path, monkeypatch):
    store = MotionFaultStore(tmp_path / "state.json")
    store.write_latch(None)
    machine, drives = make_machine(store)
    drives[2].get_fault.return_value = 15
    original_write = store.write_latch
    monkeypatch.setattr(store, "write_latch", Mock(side_effect=OSError("disk full")))
    assert machine.poll_motion_faults()
    assert store.read_latch() is None  # stale clean disk record
    monkeypatch.setattr(store, "write_latch", original_write)
    restarted, _ = make_machine(store)
    restarted.arm_startup_interlock()
    assert restarted.motion_fault_latched is not None
    assert store.read_latch() is not None
