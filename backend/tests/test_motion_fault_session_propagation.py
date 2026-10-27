"""29E: simulated dispatch failure -> runtime notification, no physical I/O."""
import asyncio
from unittest.mock import Mock

import pytest

from app.services.machine.machine import Machine
from app.services.machine.motion_fault_runtime import MotionFaultRuntime
from app.services.machine.motion_fault_store import MotionFaultStore


def build(tmp_path):
    store = MotionFaultStore(tmp_path / 'fault.json')
    store.write_latch(None)
    drives = [Mock() for _ in range(3)]
    for drive in drives:
        drive.get_fault.return_value = 0
    brush = Mock(left_drive=drives[0], right_drive=drives[1])
    roller = Mock(drive=drives[2])
    machine = Machine(brush, roller, enforce_motion_preflight=True, motion_fault_store=store)
    return machine, brush, roller, drives, store


def test_failed_dispatch_reaches_all_session_callbacks_on_next_poll(tmp_path):
    machine, brush, roller, drives, store = build(tmp_path)
    sessions = [Mock() for _ in range(3)]
    roller.forward.side_effect = RuntimeError('GAIN E15 during RUN')
    with pytest.raises(RuntimeError, match='E15'):
        machine.start_roller_forward(10)
    assert all(s.external_motion_fault.call_count == 0 for s in sessions)

    def notify(reason):
        for session in sessions:
            session.external_motion_fault(reason)

    runtime = MotionFaultRuntime(machine, on_fault=notify)
    asyncio.run(runtime._poll_once())
    assert runtime.last_fault == machine.motion_fault_latched
    for session in sessions:
        session.external_motion_fault.assert_called_once_with(machine.motion_fault_latched)
    asyncio.run(runtime._poll_once())
    for session in sessions:
        assert session.external_motion_fault.call_count == 1
    assert store.read_latch() == machine.motion_fault_latched
    for drive in drives:
        drive.stop.assert_called_once()


def test_notification_failure_does_not_clear_machine_latch(tmp_path):
    machine, brush, roller, drives, store = build(tmp_path)
    brush.start.side_effect = OSError('RS485 timeout')
    with pytest.raises(OSError, match='timeout'):
        machine.start_brush(12)
    callback = Mock(side_effect=RuntimeError('session callback failed'))
    runtime = MotionFaultRuntime(machine, on_fault=callback)
    asyncio.run(runtime._poll_once())
    asyncio.run(runtime._poll_once())
    callback.assert_called_once()
    assert machine.motion_fault_latched
    assert store.read_latch()
    with pytest.raises(RuntimeError, match='latched'):
        machine.start_roller_reverse(12)
    roller.reverse.assert_not_called()


def test_one_session_callback_failure_can_be_isolated(tmp_path):
    machine, brush, roller, drives, store = build(tmp_path)
    roller.reverse.side_effect = RuntimeError('E15')
    with pytest.raises(RuntimeError, match='E15'):
        machine.start_roller_reverse(8)
    broken, healthy = Mock(), Mock()
    broken.external_motion_fault.side_effect = RuntimeError('handler failure')

    def notify(reason):
        for session in (broken, healthy):
            try:
                session.external_motion_fault(reason)
            except Exception:
                pass

    asyncio.run(MotionFaultRuntime(machine, on_fault=notify)._poll_once())
    healthy.external_motion_fault.assert_called_once_with(machine.motion_fault_latched)


def test_runtime_does_not_issue_new_motion_commands(tmp_path):
    machine, brush, roller, drives, store = build(tmp_path)
    drives[1].get_fault.return_value = 15
    runtime = MotionFaultRuntime(machine, on_fault=Mock())
    asyncio.run(runtime._poll_once())
    assert machine.motion_fault_latched
    assert store.read_latch()
    brush.start.assert_not_called()
    roller.forward.assert_not_called()
    roller.reverse.assert_not_called()
    for drive in drives:
        drive.run_forward.assert_not_called()
        drive.run_reverse.assert_not_called()
