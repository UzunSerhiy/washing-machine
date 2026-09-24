from app.services.machine.brush import Brush
from app.services.machine.roller import Roller


class Machine:
    """
    Верхнеуровневый агрегат физических исполнительных механизмов машины.

    Machine не знает технологический процесс.
    Он только предоставляет единый интерфейс управления:
    - Brush
    - Roller
    """

    def __init__(
        self,
        brush: Brush,
        roller: Roller,
    ):
        self.brush = brush
        self.roller = roller

    def start_brush(self, frequency_hz: float) -> None:
        self.brush.start(frequency_hz)

    def stop_brush(self) -> None:
        self.brush.stop()

    def start_roller_forward(self, frequency_hz: float) -> None:
        self.roller.forward(frequency_hz)

    def start_roller_reverse(self, frequency_hz: float) -> None:
        self.roller.reverse(frequency_hz)

    def stop_roller(self) -> None:
        self.roller.stop()

    def stop_roller_coast(self) -> None:
        self.roller.stop_coast()

    def stop_all(self) -> None:
        self.brush.stop()
        self.roller.stop()
