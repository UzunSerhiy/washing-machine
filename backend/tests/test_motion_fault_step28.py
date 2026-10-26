"""Step 28: software-only recovery edge cases (no hardware commands)."""
import asyncio
from threading import Event
from unittest.mock import Mock

import pytest

from app.services.machine.motion_fault_runtime import MotionFaultRuntime
from tests.test_motion_fault_acknowledgement import build


def test_second_acknowledgement_is_rejected_without_vfd_writes():
    machine, recovery, drives, auto, calibration, home = build()
    recovery.acknowledge(operator_confirmed_stopped=True)
    with pytest.raises(RuntimeError, match="No machine motion fault"):
        recovery.acknowledge(operator_confirmed_stopped=True)
    assert machine.motion_fault_latched is None
    assert home.complete_motion_fault_recovery.call_count == 1
    for drive in drives.values():
        drive.run_forward.assert_not_called()
        drive.run_reverse.assert_not_called()
        drive.stop.assert_not_called()


@pytest.mark.parametrize("failed_drive", (1, 2, 3))
def test_rs485_failure_on_any_drive_preserves_latch(failed_drive):
    machine, recovery, drives, auto, calibration, home = build()
    drives[failed_drive].get_status.side_effect = OSError("RS485 unavailable")
    with pytest.raises(RuntimeError, match="telemetry unavailable"):
        recovery.acknowledge(operator_confirmed_stopped=True)
    assert machine.motion_fault_latched == "E15"
    home.complete_motion_fault_recovery.assert_not_called()
    auto.complete_motion_fault_recovery.assert_not_called()
    calibration.complete_motion_fault_recovery.assert_not_called()
    for drive in drives.values():
        drive.run_forward.assert_not_called()
        drive.run_reverse.assert_not_called()
        drive.stop.assert_not_called()


def test_two_concurrent_acknowledgements_cannot_both_succeed():
    async def scenario():
        machine, recovery, drives, auto, calibration, home = build()
        runtime = MotionFaultRuntime(Mock())
        results = await asyncio.gather(
            runtime.acknowledge_exclusive(recovery, operator_confirmed_stopped=True),
            runtime.acknowledge_exclusive(recovery, operator_confirmed_stopped=True),
            return_exceptions=True,
        )
        assert sum(not isinstance(r, BaseException) for r in results) == 1
        assert sum(isinstance(r, RuntimeError) for r in results) == 1
        assert machine.motion_fault_latched is None
        assert home.complete_motion_fault_recovery.call_count == 1
        for drive in drives.values():
            drive.run_forward.assert_not_called()
            drive.run_reverse.assert_not_called()
            drive.stop.assert_not_called()
    asyncio.run(scenario())


def test_poll_during_acknowledgement_is_serialized():
    async def scenario():
        machine, recovery, drives, auto, calibration, home = build()
        entered = Event()
        release = Event()
        original = recovery.acknowledge

        def slow_acknowledge(*, operator_confirmed_stopped):
            entered.set()
            assert release.wait(3), "test synchronization timed out"
            return original(operator_confirmed_stopped=operator_confirmed_stopped)

        recovery.acknowledge = slow_acknowledge
        polled = Mock(return_value=None)
        runtime = MotionFaultRuntime(Mock(poll_motion_faults=polled))
        ack_task = asyncio.create_task(runtime.acknowledge_exclusive(recovery, operator_confirmed_stopped=True))
        try:
            entered_ok = await asyncio.to_thread(entered.wait, 3)
            assert entered_ok
            # Exercise the same lock acquisition used by the production polling loop.
            async def locked_poll():
                async with runtime._poll_lock:
                    await runtime._poll_once()
            guarded_poll = asyncio.create_task(locked_poll())
            await asyncio.sleep(0)
            assert polled.call_count == 0
        finally:
            release.set()
        await ack_task
        await guarded_poll
        assert polled.call_count == 1
    asyncio.run(scenario())
