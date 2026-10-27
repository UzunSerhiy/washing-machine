"""Step 29D: REAL preflight failures fail closed across all Machine RUN entries."""
from unittest.mock import Mock

import pytest

from app.services.machine.machine import Machine
from app.services.machine.motion_fault_store import MotionFaultStore


def make_machine(tmp_path):
    store = MotionFaultStore(tmp_path / 'fault.json')
    store.write_latch(None)
    drives = [Mock() for _ in range(3)]
    for drive in drives:
        drive.get_fault.return_value = 0
    brush = Mock(left_drive=drives[0], right_drive=drives[1])
    roller = Mock(drive=drives[2])
    machine = Machine(brush, roller, enforce_motion_preflight=True, motion_fault_store=store)
    return machine, brush, roller, drives, store


@pytest.mark.parametrize('method', ['start_brush', 'start_roller_forward', 'start_roller_reverse'])
def test_preflight_e15_latches_persists_stops_and_blocks_retry(tmp_path, method):
    machine, brush, roller, drives, store = make_machine(tmp_path)
    drives[1].get_fault.return_value = 15
    with pytest.raises(RuntimeError, match='VFD fault 15'):
        getattr(machine, method)(10)
    assert 'fault 15' in machine.motion_fault_latched
    assert store.read_latch() == machine.motion_fault_latched
    brush.start.assert_not_called()
    roller.forward.assert_not_called()
    roller.reverse.assert_not_called()
    for drive in drives:
        drive.stop.assert_called_once()
    drives[1].get_fault.return_value = 0  # physical RESET alone cannot clear latch
    with pytest.raises(RuntimeError, match='latched'):
        getattr(machine, method)(10)
    for drive in drives:
        drive.stop.assert_called_once()
    restarted = Machine(brush, roller, enforce_motion_preflight=True, motion_fault_store=store)
    assert restarted.motion_fault_latched == machine.motion_fault_latched


@pytest.mark.parametrize('fault', [OSError('RS485 timeout'), None, True, -1])
def test_unavailable_or_invalid_preflight_latches(tmp_path, fault):
    machine, brush, roller, drives, store = make_machine(tmp_path)
    if isinstance(fault, Exception):
        drives[2].get_fault.side_effect = fault
    else:
        drives[2].get_fault.return_value = fault
    with pytest.raises(RuntimeError, match='telemetry'):
        machine.start_brush(10)
    assert machine.motion_fault_latched
    assert store.read_latch()
    brush.start.assert_not_called()
    for drive in drives:
        drive.stop.assert_called_once()


def test_preflight_persistence_failure_keeps_memory_latch(tmp_path):
    machine, brush, roller, drives, store = make_machine(tmp_path)
    drives[0].get_fault.return_value = 15
    store.write_latch = Mock(side_effect=OSError('disk full'))
    with pytest.raises(RuntimeError, match='fault 15'):
        machine.start_brush(10)
    assert machine.motion_fault_latched
    for drive in drives:
        drive.stop.assert_called_once()
