from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mode_speed_settings import ModeSpeedSettings
from app.services.speed.settings import RuntimeSpeedSettings


class SpeedSettingsLoader:
    async def load(
        self,
        session: AsyncSession,
        machine_mode_id: int,
    ) -> RuntimeSpeedSettings:
        result = await session.execute(
            select(ModeSpeedSettings).where(
                ModeSpeedSettings.machine_mode_id == machine_mode_id
            )
        )

        settings = result.scalar_one_or_none()

        if settings is None:
            raise ValueError(
                f"Speed settings not found for machine mode {machine_mode_id}"
            )

        return RuntimeSpeedSettings(
            belt_speed_percent=settings.belt_speed_percent,
            material_speed_percent=settings.material_speed_percent,
            brush_speed_percent=settings.brush_speed_percent,
        )
