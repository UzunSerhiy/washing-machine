from unittest.mock import AsyncMock

import pytest

from app.services.speed.service import ModeSpeedService
from app.services.speed.settings import RuntimeSpeedSettings


@pytest.mark.anyio
async def test_load_mode():
    runtime_settings = RuntimeSpeedSettings(
        belt_speed_percent=70,
        material_speed_percent=60,
        brush_speed_percent=90,
    )

    loader = AsyncMock()
    loader.load.return_value = runtime_settings

    service = ModeSpeedService(settings_loader=loader)

    result = await service.load_mode(
        session=AsyncMock(),
        machine_mode_id=1,
    )

    assert result is runtime_settings
    assert service.get_current() is runtime_settings

    loader.load.assert_awaited_once()


def test_get_current_without_loaded_mode():
    loader = AsyncMock()
    service = ModeSpeedService(settings_loader=loader)

    with pytest.raises(
        RuntimeError,
        match="Speed settings are not loaded",
    ):
        service.get_current()


def test_set_belt_speed():
    runtime_settings = RuntimeSpeedSettings(
        belt_speed_percent=70,
        material_speed_percent=60,
        brush_speed_percent=None,
    )

    loader = AsyncMock()
    service = ModeSpeedService(settings_loader=loader)
    service._current = runtime_settings

    service.set_belt_speed(50)

    assert runtime_settings.belt_speed_percent == 50


def test_set_material_speed():
    runtime_settings = RuntimeSpeedSettings(
        belt_speed_percent=70,
        material_speed_percent=60,
        brush_speed_percent=None,
    )

    loader = AsyncMock()
    service = ModeSpeedService(settings_loader=loader)
    service._current = runtime_settings

    service.set_material_speed(80)

    assert runtime_settings.material_speed_percent == 80


def test_set_brush_speed():
    runtime_settings = RuntimeSpeedSettings(
        belt_speed_percent=70,
        material_speed_percent=60,
        brush_speed_percent=90,
    )

    loader = AsyncMock()
    service = ModeSpeedService(settings_loader=loader)
    service._current = runtime_settings

    service.set_brush_speed(40)

    assert runtime_settings.brush_speed_percent == 40


def test_set_brush_speed_none():
    runtime_settings = RuntimeSpeedSettings(
        belt_speed_percent=70,
        material_speed_percent=60,
        brush_speed_percent=90,
    )

    loader = AsyncMock()
    service = ModeSpeedService(settings_loader=loader)
    service._current = runtime_settings

    service.set_brush_speed(None)

    assert runtime_settings.brush_speed_percent is None
