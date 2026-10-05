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
        settings = await self._get_settings(
            session=session,
            machine_mode_id=machine_mode_id,
        )

        return RuntimeSpeedSettings(
            belt_speed_percent=settings.belt_speed_percent,
            material_speed_percent=settings.material_speed_percent,
            brush_speed_percent=settings.brush_speed_percent,
        )

    async def save_mode_speed(
        self,
        session: AsyncSession,
        machine_mode_id: int,
        speed_percent: float,
    ) -> None:
        self._validate_speed_percent(speed_percent)

        settings = await self._get_settings(
            session=session,
            machine_mode_id=machine_mode_id,
        )

        settings.belt_speed_percent = speed_percent
        settings.material_speed_percent = speed_percent

    async def save_brush_speed(
        self,
        session: AsyncSession,
        machine_mode_id: int,
        speed_percent: float,
    ) -> None:
        self._validate_speed_percent(speed_percent)

        settings = await self._get_settings(
            session=session,
            machine_mode_id=machine_mode_id,
        )

        settings.brush_speed_percent = speed_percent

    async def _get_settings(
        self,
        session: AsyncSession,
        machine_mode_id: int,
    ) -> ModeSpeedSettings:
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

        return settings

    @staticmethod
    def _validate_speed_percent(
        speed_percent: float,
    ) -> None:
        if not 0 < speed_percent <= 100:
            raise ValueError(
                "Speed percent must be greater than 0 and no more than 100"
            )
