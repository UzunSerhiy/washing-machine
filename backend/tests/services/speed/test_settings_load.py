from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.mode_speed_settings import ModeSpeedSettings
from app.services.speed.settings import RuntimeSpeedSettings
from app.services.speed.settings_loader import SpeedSettingsLoader


@pytest.mark.anyio
async def test_load_speed_settings():
    db_settings = ModeSpeedSettings(
        machine_mode_id=1,
        belt_speed_percent=70,
        material_speed_percent=60,
        brush_speed_percent=90,
    )

    result = MagicMock()
    result.scalar_one_or_none.return_value = db_settings

    session = AsyncMock()
    session.execute.return_value = result

    loader = SpeedSettingsLoader()

    settings = await loader.load(
        session=session,
        machine_mode_id=1,
    )

    assert isinstance(settings, RuntimeSpeedSettings)
    assert settings.belt_speed_percent == 70
    assert settings.material_speed_percent == 60
    assert settings.brush_speed_percent == 90

    session.execute.assert_awaited_once()


@pytest.mark.anyio
async def test_load_speed_settings_without_brush():
    db_settings = ModeSpeedSettings(
        machine_mode_id=1,
        belt_speed_percent=80,
        material_speed_percent=75,
        brush_speed_percent=None,
    )

    result = MagicMock()
    result.scalar_one_or_none.return_value = db_settings

    session = AsyncMock()
    session.execute.return_value = result

    loader = SpeedSettingsLoader()

    settings = await loader.load(
        session=session,
        machine_mode_id=1,
    )

    assert settings.belt_speed_percent == 80
    assert settings.material_speed_percent == 75
    assert settings.brush_speed_percent is None


@pytest.mark.anyio
async def test_load_speed_settings_not_found():
    result = MagicMock()
    result.scalar_one_or_none.return_value = None

    session = AsyncMock()
    session.execute.return_value = result

    loader = SpeedSettingsLoader()

    with pytest.raises(
        ValueError,
        match="Speed settings not found for machine mode 999",
    ):
        await loader.load(
            session=session,
            machine_mode_id=999,
        )
