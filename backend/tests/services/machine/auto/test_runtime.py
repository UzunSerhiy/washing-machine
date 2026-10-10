import asyncio

import pytest

from app.services.machine.auto.runtime import AutoRuntime


class FakeAutoService:
    def __init__(self):
        self.tick_count = 0

    def tick(self, elapsed_seconds: float) -> None:
        self.tick_count += 1


def test_interval_must_be_positive():
    service = FakeAutoService()

    with pytest.raises(ValueError, match="Interval must be greater than zero"):
        AutoRuntime(
            auto_service=service,
            interval_seconds=0.0,
        )


@pytest.mark.anyio
async def test_runtime_starts():
    service = FakeAutoService()

    runtime = AutoRuntime(
        auto_service=service,
        interval_seconds=0.01,
    )

    await runtime.start()

    assert runtime.running is True

    await runtime.stop()


@pytest.mark.anyio
async def test_start_is_idempotent():
    service = FakeAutoService()

    runtime = AutoRuntime(
        auto_service=service,
        interval_seconds=0.01,
    )

    await runtime.start()
    first_task = runtime._task

    await runtime.start()

    assert runtime._task is first_task

    await runtime.stop()


@pytest.mark.anyio
async def test_runtime_calls_tick():
    service = FakeAutoService()

    runtime = AutoRuntime(
        auto_service=service,
        interval_seconds=0.01,
    )

    await runtime.start()

    await asyncio.sleep(0.035)

    await runtime.stop()

    assert service.tick_count >= 2


@pytest.mark.anyio
async def test_runtime_stops():
    service = FakeAutoService()

    runtime = AutoRuntime(
        auto_service=service,
        interval_seconds=0.01,
    )

    await runtime.start()
    await runtime.stop()

    assert runtime.running is False
    assert runtime._task is None


@pytest.mark.anyio
async def test_runtime_passes_elapsed_time_to_tick():
    class FakeAutoService:
        def __init__(self):
            self.elapsed_values = []
            self.called = asyncio.Event()

        def tick(self, elapsed_seconds: float) -> None:
            self.elapsed_values.append(elapsed_seconds)
            self.called.set()

    auto_service = FakeAutoService()

    runtime = AutoRuntime(
        auto_service=auto_service,
        interval_seconds=0.01,
    )

    await runtime.start()

    try:
        await asyncio.wait_for(
            auto_service.called.wait(),
            timeout=1.0,
        )
    finally:
        await runtime.stop()

    assert len(auto_service.elapsed_values) >= 1
    assert auto_service.elapsed_values[0] > 0
