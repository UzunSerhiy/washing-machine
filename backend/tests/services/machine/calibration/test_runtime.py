import asyncio

import pytest

from app.services.machine.calibration.runtime import CalibrationRuntime


class FakeCalibrationService:
    def __init__(self):
        self.tick_count = 0

    def tick(self) -> None:
        self.tick_count += 1


@pytest.mark.anyio
async def test_runtime_calls_tick_periodically() -> None:
    service = FakeCalibrationService()

    runtime = CalibrationRuntime(
        calibration_service=service,
        interval_seconds=0.01,
    )

    await runtime.start()

    await asyncio.sleep(0.035)

    await runtime.stop()

    assert service.tick_count >= 2


@pytest.mark.anyio
async def test_runtime_can_be_started_and_stopped() -> None:
    service = FakeCalibrationService()

    runtime = CalibrationRuntime(
        calibration_service=service,
        interval_seconds=0.01,
    )

    assert runtime.running is False

    await runtime.start()

    assert runtime.running is True

    await runtime.stop()

    assert runtime.running is False


@pytest.mark.anyio
async def test_runtime_stop_is_safe_when_not_started() -> None:
    service = FakeCalibrationService()

    runtime = CalibrationRuntime(
        calibration_service=service,
        interval_seconds=0.01,
    )

    await runtime.stop()

    assert runtime.running is False


@pytest.mark.anyio
async def test_runtime_does_not_tick_after_stop() -> None:
    service = FakeCalibrationService()

    runtime = CalibrationRuntime(
        calibration_service=service,
        interval_seconds=0.01,
    )

    await runtime.start()

    await asyncio.sleep(0.025)

    await runtime.stop()

    tick_count = service.tick_count

    await asyncio.sleep(0.025)

    assert service.tick_count == tick_count
