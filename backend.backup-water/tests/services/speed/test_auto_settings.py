from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.machine_mode import MachineMode
from app.models.mode_speed_settings import ModeSpeedSettings
from app.services.machine.operation import AutoStage
from app.services.speed.auto_settings import AutoSpeedSettingsService


def make_result(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


@pytest.mark.anyio
async def test_load_washing_settings():
    mode = MachineMode(
        id=2,
        machine_id=1,
        name="Washing",
        code="washing",
        is_enabled=True,
    )

    settings = ModeSpeedSettings(
        machine_mode_id=2,
        belt_speed_percent=60,
        material_speed_percent=60,
        brush_speed_percent=80,
    )

    session = AsyncMock()
    session.execute.side_effect = [
        make_result(mode),
        make_result(settings),
    ]

    service = AutoSpeedSettingsService()

    result = await service.load(
        session=session,
        machine_id=1,
        stage=AutoStage.WASHING,
    )

    assert result.mode_speed_percent == 60
    assert result.brush_speed_percent == 80


@pytest.mark.anyio
async def test_save_mode_speed_updates_belt_and_material_together():
    mode = MachineMode(
        id=2,
        machine_id=1,
        name="Washing",
        code="washing",
        is_enabled=True,
    )

    settings = ModeSpeedSettings(
        machine_mode_id=2,
        belt_speed_percent=50,
        material_speed_percent=50,
        brush_speed_percent=80,
    )

    session = AsyncMock()
    session.execute.side_effect = [
        make_result(mode),
        make_result(settings),
    ]

    service = AutoSpeedSettingsService()

    result = await service.set_mode_speed(
        session=session,
        machine_id=1,
        stage=AutoStage.WASHING,
        speed_percent=65,
    )

    assert settings.belt_speed_percent == 65
    assert settings.material_speed_percent == 65

    # Щётки не должны изменяться.
    assert settings.brush_speed_percent == 80

    assert result.mode_speed_percent == 65
    assert result.brush_speed_percent == 80

    session.commit.assert_awaited_once()


@pytest.mark.anyio
async def test_save_brush_speed_does_not_change_mode_speed():
    mode = MachineMode(
        id=2,
        machine_id=1,
        name="Washing",
        code="washing",
        is_enabled=True,
    )

    settings = ModeSpeedSettings(
        machine_mode_id=2,
        belt_speed_percent=60,
        material_speed_percent=60,
        brush_speed_percent=70,
    )

    session = AsyncMock()
    session.execute.side_effect = [
        make_result(mode),
        make_result(settings),
    ]

    service = AutoSpeedSettingsService()

    result = await service.set_brush_speed(
        session=session,
        machine_id=1,
        stage=AutoStage.WASHING,
        speed_percent=85,
    )

    assert settings.belt_speed_percent == 60
    assert settings.material_speed_percent == 60
    assert settings.brush_speed_percent == 85

    assert result.mode_speed_percent == 60
    assert result.brush_speed_percent == 85

    session.commit.assert_awaited_once()


@pytest.mark.anyio
async def test_mode_speed_must_be_between_zero_and_100():
    service = AutoSpeedSettingsService()

    with pytest.raises(
        ValueError,
        match="Speed percent must be greater than 0 and no more than 100",
    ):
        await service.set_mode_speed(
            session=AsyncMock(),
            machine_id=1,
            stage=AutoStage.WASHING,
            speed_percent=0,
        )


@pytest.mark.anyio
async def test_machine_mode_must_exist():
    session = AsyncMock()
    session.execute.return_value = make_result(None)

    service = AutoSpeedSettingsService()

    with pytest.raises(
        ValueError,
        match="Machine mode not found",
    ):
        await service.load(
            session=session,
            machine_id=1,
            stage=AutoStage.WASHING,
        )
