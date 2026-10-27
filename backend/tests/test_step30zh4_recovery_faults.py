"""30ZH.4: fault notification and recovery regression tests; fake drives only."""
import asyncio

import pytest

from app.services.machine.motion_fault_runtime import MotionFaultRuntime
from tests.test_motion_fault_integration import setup, assert_no_motion


def test_callback_failure_is_diagnostic_and_never_retried_automatically():
    machine, drives, auto, calibration, home, recovery, _, _ = setup()
    calls = []

    def broken(reason):
        calls.append(reason)
        raise RuntimeError('session callback failed')

    runtime = MotionFaultRuntime(machine, on_fault=broken)

    async def scenario():
        await runtime._poll_once()
        await runtime._poll_once()
        assert calls == ['E15']
        assert runtime._notified
        assert runtime.last_notification_error == 'RuntimeError: session callback failed'
        assert machine.motion_fault_latched == 'E15'
        assert_no_motion(drives)
        # Recovery cannot proceed while an affected session remains active.
        auto.get_status.return_value = {'status': 'RUNNING', 'running': True, 'paused': False}
        with pytest.raises(RuntimeError, match='AUTO session is not inactive'):
            await runtime.acknowledge_exclusive(recovery, operator_confirmed_stopped=True)
        assert machine.motion_fault_latched == 'E15'
        assert runtime.last_notification_error is not None
        assert_no_motion(drives)

    asyncio.run(scenario())


def test_failed_recovery_does_not_clear_notification_diagnostic():
    machine, drives, auto, calibration, home, recovery, _, _ = setup()
    runtime = MotionFaultRuntime(machine, on_fault=lambda reason: (_ for _ in ()).throw(ValueError('handler failed')))

    async def scenario():
        await runtime._poll_once()
        drives[1].get_status.return_value = 1
        with pytest.raises(RuntimeError, match='STOP not confirmed'):
            await runtime.acknowledge_exclusive(recovery, operator_confirmed_stopped=True)
        assert runtime._notified
        assert 'handler failed' in runtime.last_notification_error
        assert machine.motion_fault_latched == 'E15'
        assert_no_motion(drives)

    asyncio.run(scenario())


def test_successful_recovery_resets_notification_diagnostic_without_run():
    machine, drives, auto, calibration, home, recovery, _, _ = setup()
    runtime = MotionFaultRuntime(machine, on_fault=lambda reason: (_ for _ in ()).throw(ValueError('handler failed')))

    async def scenario():
        await runtime._poll_once()
        assert runtime.last_notification_error
        result = await runtime.acknowledge_exclusive(recovery, operator_confirmed_stopped=True)
        assert result.verified
        assert runtime.last_notification_error is None
        assert runtime._notified is False
        assert_no_motion(drives)

    asyncio.run(scenario())
