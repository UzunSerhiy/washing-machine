"""Regression tests for shared HOME across AUTO session lifecycle."""
from unittest.mock import Mock

import pytest

from app.services.machine.auto.session_service import AutoSessionService
from tests.services.machine.auto.test_session_service import (
    FakeOperationService,
    FakeSpeedSettingsService,
    FakeCalibrationRepository,
    FakeWindingParametersRepository,
    FakeMachineRepository,
)


def make_service(homed=True):
    operation = FakeOperationService()
    service = AutoSessionService(
        machine_id=1,
        operation_service=operation,
        speed_settings_service=FakeSpeedSettingsService(),
        calibration_repository=FakeCalibrationRepository(),
        winding_parameters_repository=FakeWindingParametersRepository(),
        machine_repository=FakeMachineRepository(),
    )
    home = Mock()
    if not homed:
        home.require_zero.side_effect = RuntimeError("Point 0 is not confirmed")
    service.set_roller_homing_service(home)
    return service, operation, home


@pytest.mark.anyio
async def test_prepare_rejects_unconfirmed_home_without_motion():
    service, operation, home = make_service(homed=False)
    with pytest.raises(RuntimeError, match="Point 0"):
        await service.prepare(object())
    assert service._prepared is None
    assert operation.start_roller_forward_calls == []
    home.require_zero.assert_called_once()


@pytest.mark.anyio
async def test_start_rechecks_home_after_prepare():
    service, operation, home = make_service()
    await service.prepare(object())
    home.require_zero.side_effect = RuntimeError("Point 0 is not confirmed")
    with pytest.raises(RuntimeError, match="Point 0"):
        service.start()
    assert operation.start_roller_forward_calls == []
    assert operation.state.running is False


@pytest.mark.anyio
async def test_resume_preserves_position_without_rehoming():
    service, operation, home = make_service()
    prepared = await service.prepare(object())
    service.start()
    service.tick(elapsed_seconds=1.0)
    service.pause()
    position = prepared.controller.position_turns
    home.require_zero.reset_mock()
    service.resume()
    home.require_zero.assert_not_called()
    assert prepared.controller.position_turns == pytest.approx(position)
    assert operation.state.running is True
    service.tick(elapsed_seconds=1.0)
    assert prepared.controller.position_turns > position


@pytest.mark.anyio
async def test_stop_discards_session_but_does_not_invalidate_home():
    service, operation, home = make_service()
    await service.prepare(object())
    service.start()
    service.stop()
    assert service._prepared is None
    assert operation.state.running is False
    assert operation.state.paused is False
    home.invalidate.assert_not_called()
    with pytest.raises(RuntimeError, match="not prepared"):
        service.start()


@pytest.mark.anyio
async def test_new_session_requires_home_after_invalidation():
    service, operation, home = make_service()
    await service.prepare(object())
    service.start()
    service.stop()
    home.require_zero.side_effect = RuntimeError("Point 0 is not confirmed")
    with pytest.raises(RuntimeError, match="Point 0"):
        await service.prepare(object())
    assert operation.start_roller_forward_calls != []
    assert service._prepared is None
