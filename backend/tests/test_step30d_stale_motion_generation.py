"""30D: stale queued RUN must never dispatch after successful recovery (fake drives)."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from unittest.mock import Mock

import pytest

from app.services.machine.brush import Brush
from app.services.machine.roller import Roller
from app.services.machine.machine import Machine


def build():
    left, right, roller = Mock(), Mock(), Mock()
    for drive in (left, right, roller):
        drive.get_fault.return_value = 0
    return Machine(Brush(left, right), Roller(roller), enforce_motion_preflight=True), (left, right, roller)


@pytest.mark.parametrize('method', ['start_brush', 'start_roller_forward', 'start_roller_reverse'])
def test_queued_run_from_latched_epoch_rejected_after_recovery(method):
    machine, drives = build()
    machine._motion_fault_latched = 'E15'
    entered = Event()
    proceed = Event()
    original_ticket = machine._motion_ticket

    def ticket():
        result = original_ticket()
        entered.set()
        assert proceed.wait(3)
        return result

    machine._motion_ticket = ticket
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(getattr(machine, method), 10)
        assert entered.wait(3)
        # Simulate a fully verified, successful recovery under the machine lock.
        with machine._roller_lock:
            machine.complete_motion_fault_recovery()
        proceed.set()
        with pytest.raises(RuntimeError, match='Stale motion command'):
            future.result(timeout=3)
    for drive in drives:
        drive.set_frequency.assert_not_called()
        drive.run_forward.assert_not_called()
        drive.run_reverse.assert_not_called()


@pytest.mark.parametrize('method', ['start_brush', 'start_roller_forward', 'start_roller_reverse'])
def test_clean_epoch_allows_new_command_after_recovery(method):
    machine, drives = build()
    machine._motion_fault_latched = 'E15'
    machine.complete_motion_fault_recovery()
    getattr(machine, method)(10)
    assert any(d.set_frequency.called for d in drives)


def test_generation_increases_on_monitor_fault_and_recovery():
    machine, drives = build()
    before = machine._motion_generation
    drives[0].get_fault.return_value = 15
    assert machine.poll_motion_faults() is not None
    assert machine._motion_generation > before
    after_fault = machine._motion_generation
    machine.complete_motion_fault_recovery()
    assert machine._motion_generation > after_fault
