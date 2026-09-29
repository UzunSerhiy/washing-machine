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

    @staticmethod
    def _validate_speed_percent(speed_percent: float) -> None:
        if not 0 < speed_percent <= 100:
            raise ValueError("Speed pecent must be greater than 0 and no more than 100")
