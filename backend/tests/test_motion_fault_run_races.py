"""Step 29V: deterministic software concurrency regression tests; no hardware I/O."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from unittest.mock import Mock

import pytest

from app.services.machine.brush import Brush
from app.services.machine.machine import Machine
from app.services.machine.roller import Roller


def build():
    left, right, roller = Mock(), Mock(), Mock()
    for drive in (left, right, roller):
        drive.get_fault.return_value = 0
    machine = Machine(Brush(left, right), Roller(roller), enforce_motion_preflight=True)
    return machine, left, right, roller


@pytest.mark.parametrize('method', ['start_brush', 'start_roller_forward', 'start_roller_reverse'])
def test_monitor_cannot_interleave_a_machine_motion_command(method):
    machine, left, right, roller = build()
    entered, release = Event(), Event()

    def block_preflight():
        entered.set()
        assert release.wait(3), 'test timed out waiting for preflight release'
        return 0

    left.get_fault.side_effect = block_preflight
    with ThreadPoolExecutor(max_workers=2) as pool:
        motion = pool.submit(getattr(machine, method), 10)
        assert entered.wait(3)
        monitor = pool.submit(machine.poll_motion_faults)
        try:
            # The monitor must not complete its own preflight while motion holds the machine lock.
            assert not monitor.done()
            assert left.get_fault.call_count == 1
        finally:
            release.set()
        motion.result(timeout=3)
        assert monitor.result(timeout=3) is None
    assert left.get_fault.call_count == 2


def test_detected_fault_latches_and_blocks_queued_run():
    machine, left, right, roller = build()
    entered, release = Event(), Event()

    def fault_on_monitor():
        entered.set()
        assert release.wait(3), 'test timed out waiting for fault release'
        return 15

    left.get_fault.side_effect = fault_on_monitor
    with ThreadPoolExecutor(max_workers=2) as pool:
        monitor = pool.submit(machine.poll_motion_faults)
        assert entered.wait(3)
        motion = pool.submit(machine.start_roller_forward, 10)
        try:
            assert not motion.done()
        finally:
            release.set()
        assert 'VFD fault 15' in monitor.result(timeout=3)
        with pytest.raises(RuntimeError, match='Motion fault latched'):
            motion.result(timeout=3)
    roller.set_frequency.assert_not_called()
    roller.run_forward.assert_not_called()


def test_fault_preflight_rejects_motion_before_frequency_or_run():
    machine, left, right, roller = build()
    right.get_fault.return_value = 15
    with pytest.raises(RuntimeError, match='VFD fault 15'):
        machine.start_brush(12)
    for drive in (left, right, roller):
        drive.set_frequency.assert_not_called()
        drive.run_forward.assert_not_called()
        drive.run_reverse.assert_not_called()
