from app.services.speed.context import SpeedContext
from app.services.speed.values import SpeedValues
from app.services.winding.calculator import WindingCalculator


class SpeedLayer:
    def __init__(self, max_frequency_hz: float = 50.0):
        if max_frequency_hz <= 0:
            raise ValueError("Max frequency must be greater than zero")

        self.max_frequency_hz = max_frequency_hz

    def belt_frequency(self, speed_percent: float) -> float:
        self._validate_speed_percent(speed_percent)

        return self.max_frequency_hz * speed_percent / 100

    def brush_frequency(self, speed_percent: float) -> float:
        self._validate_speed_percent(speed_percent)

        return self.max_frequency_hz * speed_percent / 100

    def material_frequency(
        self,
        calculator: WindingCalculator,
        speed_percent: float,
    ) -> float:
        self._validate_speed_percent(speed_percent)

        return calculator.frequency_hz(speed_percent)

    def calculate(
        self,
        context: SpeedContext,
    ) -> SpeedValues:
        settings = context.settings
        winding_calculator = context.winding_calculator

        belt_frequency_hz = self.belt_frequency(settings.belt_speed_percent)

        material_frequency_hz = self.material_frequency(
            winding_calculator, settings.material_speed_percent
        )

        if settings.brush_speed_percent is None:
            brush_frequency_hz = None
        else:
            brush_frequency_hz = self.brush_frequency(settings.brush_speed_percent)

        return SpeedValues(
            belt_frequency_hz=belt_frequency_hz,
            material_frequency_hz=material_frequency_hz,
            brush_frequency_hz=brush_frequency_hz,
        )

    @staticmethod
    def _validate_speed_percent(speed_percent: float) -> None:
        if not 0 < speed_percent <= 100:
            raise ValueError(
                "Speed percent must be greater than 0 and no more than 100"
            )
