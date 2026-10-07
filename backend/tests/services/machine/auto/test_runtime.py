import asyncio

import pytest

from app.services.machine.auto.runtime import AutoRuntime


class FakeAutoService:
    def __init__(self):
        self.tick_count = 0

    def tick(self) -> None:
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
