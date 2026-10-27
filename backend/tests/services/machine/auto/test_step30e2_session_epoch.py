"""AUTO session epoch regressions using a fault-aware fake machine."""
import asyncio
from unittest.mock import Mock

import pytest

from app.services.machine.auto.session_service import AutoSessionService
from tests.services.machine.auto.test_session_service import (
    FakeOperationService, FakeSpeedSettingsService, FakeCalibrationRepository,
    FakeWindingParametersRepository, FakeMachineRepository,
)


def build(calibration_repository=None):
    operation = FakeOperationService()
    service = AutoSessionService(
        machine_id=1,
        operation_service=operation,
        speed_settings_service=FakeSpeedSettingsService(),
        calibration_repository=calibration_repository or FakeCalibrationRepository(),
        winding_parameters_repository=FakeWindingParametersRepository(),
        machine_repository=FakeMachineRepository(),
    )
    service.set_roller_homing_service(Mock())
    return service, operation


@pytest.mark.anyio
async def test_stale_start_cannot_move_after_recovery():
    service, operation = build()
    await service.prepare(object())
    operation.machine.simulate_fault_and_recovery()
    with pytest.raises(RuntimeError, match="Stale motion session"):
        service.start()
    assert operation.start_roller_forward_calls == []


@pytest.mark.anyio
async def test_stale_resume_cannot_move_after_recovery():
    service, operation = build()
    await service.prepare(object())
    service.start()
    service.pause()
    before = list(operation.start_roller_forward_calls)
    operation.machine.simulate_fault_and_recovery()
    with pytest.raises(RuntimeError, match="Stale motion session"):
        service.resume()
    assert operation.start_roller_forward_calls == before


@pytest.mark.anyio
async def test_stale_tick_cannot_move_after_recovery():
    service, operation = build()
    await service.prepare(object())
    service.start()
    before = list(operation.start_roller_forward_calls)
    operation.machine.simulate_fault_and_recovery()
    with pytest.raises(RuntimeError, match="Stale motion session"):
        service.tick(0.1)
    assert operation.start_roller_forward_calls == before


@pytest.mark.anyio
async def test_fault_during_async_prepare_cannot_publish_session():
    entered = asyncio.Event()
    proceed = asyncio.Event()

    class DelayedCalibration(FakeCalibrationRepository):
        async def load(self, *args, **kwargs):
            entered.set()
            await proceed.wait()
            return await super().load(*args, **kwargs)

    service, operation = build(DelayedCalibration())
    task = asyncio.create_task(service.prepare(object()))
    await entered.wait()
    operation.machine.simulate_fault_and_recovery()
    proceed.set()
    with pytest.raises(RuntimeError, match="Stale motion session"):
        await task
    assert service._prepared is None
    assert operation.start_roller_forward_calls == []
