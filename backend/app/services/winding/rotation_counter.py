from app.services.winding.rotation import RollerRotationCalculator


class RollerRotationCounter:
    """
    Накопитель физических оборотов ролика по измерениям
    частоты VFD.

    Частота измеряется периодически, а количество физических
    оборотов рассчитывается между двумя измерениями.

    Класс не интерпретирует направление движения материала.
    Он считает только физическое вращение ролика.
    """

    def __init__(
        self,
        calculator: RollerRotationCalculator,
    ):
        self.calculator = calculator

        self._total_revolutions = 0.0
        self._previous_frequency_hz: float | None = None

    @property
    def total_revolutions(self) -> float:
        return self._total_revolutions

    def update(
        self,
        frequency_hz: float,
        elapsed_seconds: float,
    ) -> float:
        """
        Добавляет физические обороты за прошедший интервал.

        При наличии предыдущей частоты используется средняя
        частота между двумя измерениями.
        """

        if frequency_hz < 0:
            raise ValueError("Frequency cannot be negative")

        if elapsed_seconds < 0:
            raise ValueError("Elapsed time cannot be negative")

        if self._previous_frequency_hz is None:
            self._previous_frequency_hz = frequency_hz
            return 0.0

        average_frequency = (self._previous_frequency_hz + frequency_hz) / 2

        revolutions = self.calculator.revolutions_for_time(
            frequency_hz=average_frequency,
            elapsed_seconds=elapsed_seconds,
        )

        self._total_revolutions += revolutions
        self._previous_frequency_hz = frequency_hz

        return revolutions

    def reset(self) -> None:
        self._total_revolutions = 0.0
        self._previous_frequency_hz = None
