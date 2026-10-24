from app.services.speed.settings import RuntimeSpeedSettings
from app.services.speed.settings_loader import SpeedSettingsLoader


class ModeSpeedService:
    def __init__(self, settings_loader: SpeedSettingsLoader):
        self.settings_loader = settings_loader
        self._current: RuntimeSpeedSettings | None = None

    async def load_mode(
        self,
        session,
        machine_mode_id: int,
    ) -> RuntimeSpeedSettings:
        self._current = await self.settings_loader.load(
            session=session, machine_mode_id=machine_mode_id
        )

        return self._current

    def get_current(self) -> RuntimeSpeedSettings:
        if self._current is None:
            raise RuntimeError("Speed settings are not loaded")

        return self._current

    def set_belt_speed(self, speed_percent: float) -> None:
        self.get_current().set_belt_speed(speed_percent)

    def set_material_speed(self, speed_percent: float) -> None:
        self.get_current().set_material_speed(speed_percent)

    def set_brush_speed(self, speed_percent: float | None) -> None:
        self.get_current().set_brush_speed(speed_percent)
