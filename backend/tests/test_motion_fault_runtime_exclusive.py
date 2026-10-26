"""Recovery verification must not overlap monitor Modbus polling."""
import asyncio
import time

from app.services.machine.motion_fault_runtime import MotionFaultRuntime


def test_exclusive_verification_blocks_polling_and_does_not_clear_latch():
    async def scenario():
        class Machine:
            def __init__(self):
                self.calls = 0
                self.motion_fault_latched = 'E15'
            def poll_motion_faults(self):
                self.calls += 1
                return self.motion_fault_latched

        machine = Machine()
        runtime = MotionFaultRuntime(machine, interval_seconds=0.005)
        entered = asyncio.Event()
        release = asyncio.Event()

        async def hold_verification():
            async with runtime._poll_lock:
                entered.set()
                await release.wait()

        holder = asyncio.create_task(hold_verification())
        await entered.wait()
        await runtime.start()
        try:
            await asyncio.sleep(0.025)
            assert machine.calls == 0
            release.set()
            await holder
            await asyncio.sleep(0.025)
            assert machine.calls > 0
            assert machine.motion_fault_latched == 'E15'
        finally:
            release.set()
            await runtime.stop()
            await holder
    asyncio.run(scenario())


def test_exclusive_verification_is_read_only():
    async def scenario():
        class Machine:
            def poll_motion_faults(self):
                raise AssertionError('poll must not run during verification')
        runtime = MotionFaultRuntime(Machine())
        result = await runtime.verify_exclusive(
            lambda *, operator_confirmed_stopped: operator_confirmed_stopped,
            operator_confirmed_stopped=True,
        )
        assert result is True
        assert runtime.last_fault is None
        assert runtime._notified is False
    asyncio.run(scenario())
