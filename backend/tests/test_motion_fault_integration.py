"""Step 27: integration checks using fake GAIN telemetry; no hardware motion."""
import asyncio
from threading import RLock
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.services.machine.motion_fault_recovery import MotionFaultRecoveryService
from app.services.machine.motion_fault_runtime import MotionFaultRuntime


class FakeMachine:
    def __init__(self):
        self._roller_lock = RLock()
        self.motion_fault_latched = 'E15'
        self._roller_stop_fault = False
        self._external_stop_pending = 0
        self.roller_owner = None
        self.fault_on_poll = False
        self.poll_count = 0
        self.clear_count = 0

    def poll_motion_faults(self):
        self.poll_count += 1
        if self.fault_on_poll:
            self.motion_fault_latched = 'E15-again'
        return self.motion_fault_latched

    def complete_motion_fault_recovery(self):
        self.clear_count += 1
        self.motion_fault_latched = None


def setup():
    machine = FakeMachine()
    drives = {i: Mock() for i in (1, 2, 3)}
    for drive in drives.values():
        drive.get_fault.return_value = 0
        drive.get_status.return_value = 3
        drive.get_frequency.return_value = 0.0
    drive_service = SimpleNamespace(
        drives=drives,
        configs={i: SimpleNamespace(enabled=True) for i in drives},
    )
    auto = Mock()
    auto.get_status.return_value = {'status': 'FAULT', 'running': False, 'paused': False}
    auto._prepared = None
    calibration = Mock()
    calibration.active = False
    calibration.auto_mode = None
    home = Mock()
    home.OWNER = 'homing'
    home.get_status.return_value = {'state': 'FAULT', 'searching': False, 'awaiting_stop': False}
    recovery = MotionFaultRecoveryService(machine, drive_service, auto, calibration, home)
    notifications = []
    runtime = MotionFaultRuntime(machine, interval_seconds=0.005, on_fault=notifications.append)
    return machine, drives, auto, calibration, home, recovery, runtime, notifications


def assert_no_motion(drives):
    for drive in drives.values():
        drive.run_forward.assert_not_called()
        drive.run_reverse.assert_not_called()
        drive.stop.assert_not_called()
        drive.set_frequency.assert_not_called()


def test_fault_recovery_and_second_fault_notification():
    async def scenario():
        machine, drives, auto, calibration, home, recovery, runtime, notifications = setup()
        await runtime._poll_once()
        assert notifications == ['E15']
        assert runtime._notified
        result = await runtime.acknowledge_exclusive(recovery, operator_confirmed_stopped=True)
        assert result.consecutive_stop_samples == 3
        assert machine.motion_fault_latched is None
        assert not runtime._notified
        assert machine.clear_count == 1
        machine.fault_on_poll = True
        await runtime._poll_once()
        assert notifications == ['E15', 'E15-again']
        assert machine.motion_fault_latched == 'E15-again'
        assert_no_motion(drives)
    asyncio.run(scenario())


def test_telemetry_failure_keeps_fault_and_monitor_armed():
    async def scenario():
        machine, drives, auto, calibration, home, recovery, runtime, notifications = setup()
        await runtime._poll_once()
        drives[2].get_frequency.side_effect = OSError('RS485 timeout')
        with pytest.raises(RuntimeError, match='telemetry unavailable'):
            await runtime.acknowledge_exclusive(recovery, operator_confirmed_stopped=True)
        assert machine.motion_fault_latched == 'E15'
        assert runtime._notified
        assert machine.clear_count == 0
        auto.complete_motion_fault_recovery.assert_not_called()
        assert_no_motion(drives)
    asyncio.run(scenario())


def test_operator_rejection_preserves_latch():
    async def scenario():
        machine, drives, auto, calibration, home, recovery, runtime, notifications = setup()
        with pytest.raises(RuntimeError, match='Operator must confirm'):
            await runtime.acknowledge_exclusive(recovery, operator_confirmed_stopped=False)
        assert machine.motion_fault_latched == 'E15'
        assert machine.clear_count == 0
        assert_no_motion(drives)
    asyncio.run(scenario())


def test_monitor_poll_waits_during_recovery():
    async def scenario():
        machine, drives, auto, calibration, home, recovery, runtime, notifications = setup()
        entered = asyncio.Event()
        release = asyncio.Event()
        async def hold_lock():
            async with runtime._poll_lock:
                entered.set()
                await release.wait()
        holder = asyncio.create_task(hold_lock())
        await entered.wait()
        try:
            await runtime.start()
            await asyncio.sleep(0.02)
            assert machine.poll_count == 0
            check = asyncio.create_task(runtime.verify_exclusive(recovery.verify, operator_confirmed_stopped=True))
            await asyncio.sleep(0)
            assert not check.done()
            release.set()
            result = await asyncio.wait_for(check, 1)
            assert result.verified
        finally:
            release.set()
            await holder
            await runtime.stop()
        assert machine.motion_fault_latched == 'E15'
        assert_no_motion(drives)
    asyncio.run(scenario())
