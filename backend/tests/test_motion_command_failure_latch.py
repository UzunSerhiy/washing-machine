"""Step 29G: motion dispatch failures, fake drives only; no hardware motion."""
from unittest.mock import Mock

import pytest

from app.services.machine.machine import Machine
from app.services.machine.motion_fault_store import MotionFaultStore


def setup(tmp_path):
    store = MotionFaultStore(tmp_path / "motion.json")
    store.write_latch(None)
    drives = [Mock() for _ in range(3)]
    for drive in drives:
        drive.get_fault.return_value = 0
    brush = Mock(left_drive=drives[0], right_drive=drives[1])
    roller = Mock(drive=drives[2])
    machine = Machine(brush, roller, enforce_motion_preflight=True, motion_fault_store=store)
    return machine, brush, roller, drives, store


@pytest.mark.parametrize("method", ["start_brush", "start_roller_forward", "start_roller_reverse"])
def test_dispatch_failure_latches_persists_and_stops(tmp_path, method):
    machine, brush, roller, drives, store = setup(tmp_path)
    target = brush.start if method == "start_brush" else getattr(roller, "forward" if method.endswith("forward") else "reverse")
    target.side_effect = RuntimeError("GAIN E15 during RUN")
    with pytest.raises(RuntimeError, match="E15"):
        getattr(machine, method)(10)
    assert "E15" in machine.motion_fault_latched
    assert "E15" in store.read_latch()
    for drive in drives:
        drive.stop.assert_called_once()
    with pytest.raises(RuntimeError, match="latched"):
        machine.start_brush(10)
    assert brush.start.call_count == (1 if method == "start_brush" else 0)


def test_failure_latch_survives_new_machine_instance(tmp_path):
    machine, brush, roller, drives, store = setup(tmp_path)
    roller.forward.side_effect = RuntimeError("write timeout")
    with pytest.raises(RuntimeError, match="write timeout"):
        machine.start_roller_forward(10)
    restarted = Machine(brush, roller, enforce_motion_preflight=True, motion_fault_store=store)
    assert restarted.motion_fault_latched
    with pytest.raises(RuntimeError, match="latched"):
        restarted.start_roller_reverse(10)


def test_failed_persistence_keeps_memory_latch(tmp_path, monkeypatch):
    machine, brush, roller, drives, store = setup(tmp_path)
    monkeypatch.setattr(store, "write_latch", Mock(side_effect=OSError("disk full")))
    roller.reverse.side_effect = RuntimeError("E15")
    with pytest.raises(RuntimeError, match="E15"):
        machine.start_roller_reverse(10)
    assert machine.motion_fault_latched
    for drive in drives:
        drive.stop.assert_called_once()


def test_preflight_failure_does_not_dispatch(tmp_path):
    machine, brush, roller, drives, store = setup(tmp_path)
    drives[0].get_fault.return_value = 15
    with pytest.raises(RuntimeError, match="fault 15"):
        machine.start_brush(10)
    brush.start.assert_not_called()
