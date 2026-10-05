from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.machine_mode import MachineMode
from app.models.mode_speed_settings import ModeSpeedSettings
from app.services.machine.operation import AutoStage


@dataclass(frozen=True)
class AutoSpeedSettings:
    stage: AutoStage
    mode_speed_percent: float
    brush_speed_percent: float | None


class AutoSpeedSettingsService:
    async def load(
        self,
        session: AsyncSession,
        machine_id: int,
        stage: AutoStage,
    ) -> AutoSpeedSettings:
        _, settings = await self._load_models(
            session=session,
            machine_id=machine_id,
            stage=stage,
        )

        return self._build_result(
            stage=stage,
            settings=settings,
        )

    async def set_mode_speed(
        self,
        session: AsyncSession,
        machine_id: int,
        stage: AutoStage,
        speed_percent: float,
    ) -> AutoSpeedSettings:
        self._validate_speed_percent(speed_percent)

        _, settings = await self._load_models(
            session=session,
            machine_id=machine_id,
            stage=stage,
        )

        # Оператор видит ОДНУ скорость этапа.
        #
        # BELTS:
        #     используется напрямую.
        #
        # MATERIAL:
        #     является масштабом физической кривой постоянной
        #     линейной скорости.
        settings.belt_speed_percent = speed_percent
        settings.material_speed_percent = speed_percent

        await session.commit()

        return self._build_result(
            stage=stage,
            settings=settings,
        )

    async def set_brush_speed(
        self,
        session: AsyncSession,
        machine_id: int,
        stage: AutoStage,
        speed_percent: float,
    ) -> AutoSpeedSettings:
        self._validate_speed_percent(speed_percent)

        _, settings = await self._load_models(
            session=session,
            machine_id=machine_id,
            stage=stage,
        )

        if settings.brush_speed_percent is None:
            raise ValueError(f"Brush speed is not available for stage {stage.value}")

        settings.brush_speed_percent = speed_percent

        await session.commit()

        return self._build_result(
            stage=stage,
            settings=settings,
        )

    async def _load_models(
        self,
        session: AsyncSession,
        machine_id: int,
        stage: AutoStage,
    ) -> tuple[MachineMode, ModeSpeedSettings]:
        mode_result = await session.execute(
            select(MachineMode).where(
                MachineMode.machine_id == machine_id,
                MachineMode.code == stage.name,
                MachineMode.is_enabled.is_(True),
            )
        )

        mode = mode_result.scalar_one_or_none()

        if mode is None:
            raise ValueError(f"Machine mode not found for stage {stage.value}")

        settings_result = await session.execute(
            select(ModeSpeedSettings).where(
                ModeSpeedSettings.machine_mode_id == mode.id
            )
        )

        settings = settings_result.scalar_one_or_none()

        if settings is None:
            raise ValueError(f"Speed settings not found for stage {stage.value}")

        return mode, settings

    @staticmethod
    def _build_result(
        stage: AutoStage,
        settings: ModeSpeedSettings,
    ) -> AutoSpeedSettings:
        # belt/material должны представлять одну операторскую
        # скорость режима.
        if settings.belt_speed_percent != settings.material_speed_percent:
            raise RuntimeError(
                f"Inconsistent mode speed settings for stage {stage.value}"
            )

        return AutoSpeedSettings(
            stage=stage,
            mode_speed_percent=settings.belt_speed_percent,
            brush_speed_percent=settings.brush_speed_percent,
        )

    @staticmethod
    def _validate_speed_percent(
        speed_percent: float,
    ) -> None:
        if not 0 < speed_percent <= 100:
            raise ValueError(
                "Speed percent must be greater than 0 and no more than 100"
            )
