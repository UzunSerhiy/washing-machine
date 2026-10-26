import asyncio

import pytest

from app.services.machine.motion_fault_runtime import MotionFaultRuntime


class StubMachine:
    def __init__(self, fault=None):
        self.fault = fault
        self.calls = 0

    def poll_motion_faults(self):
        self.calls += 1
        return self.fault


async def _scenario_runtime_polls_and_latches():
    machine = StubMachine("E15")
    runtime = MotionFaultRuntime(machine, interval_seconds=0.005)
    await runtime.start()
    await asyncio.sleep(0.035)
    await runtime.stop()
    assert machine.calls > 0
    assert runtime.last_fault == "E15"
    assert not runtime.running


async def _scenario_start_is_idempotent():
    runtime = MotionFaultRuntime(StubMachine(), interval_seconds=0.005)
    await runtime.start()
    task = runtime._task
    await runtime.start()
    assert runtime._task is task
    await runtime.stop()


async def _scenario_poll_exception_is_recorded_and_loop_continues():
    class Broken:
        def poll_motion_faults(self):
            raise OSError("serial unavailable")

    runtime = MotionFaultRuntime(Broken(), interval_seconds=0.005)
    await runtime.start()
    await asyncio.sleep(0.03)
    await runtime.stop()
    assert "serial unavailable" in runtime.last_poll_error


def test_invalid_interval():
    with pytest.raises(ValueError):
        MotionFaultRuntime(StubMachine(), 0)


def test_runtime_polls_and_latches():
    asyncio.run(_scenario_runtime_polls_and_latches())

def test_start_is_idempotent():
    asyncio.run(_scenario_start_is_idempotent())

def test_poll_exception_is_recorded_and_loop_continues():
    asyncio.run(_scenario_poll_exception_is_recorded_and_loop_continues())
