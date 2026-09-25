from app.services.machine.machine import Machine
from app.services.machine.calibration.position import RollerPositionTracker
from app.services.winding.rotation import RollerRotationCalculator
from app.services.machine.calibration.points import CalibrationPoint
from app.services.machine.calibration.store import CalibrationPointStore


class CalibrationPlayer:
    def __init__(
        self,
        machine: Machine,
        position_tracker: RollerPositionTracker,
        rotation_calculator: RollerRotationCalculator,
        calibration_store: CalibrationPointStore | None = None,
    ):
        self.machine = machine
        self.position_tracker = position_tracker
        self.rotation_calculator = rotation_calculator
        self.calibration_store = calibration_store

        self._running = False
        self._paused = False
        self._direction: str | None = None
        self._frequency_hz: float | None = None

    @property
    def running(self) -> bool:
        return self._running

    @property
    def paused(self) -> bool:
        return self._paused

    @property
    def direction(self) -> str | None:
        return self._direction

    @property
    def frequency_hz(self) -> float | None:
        return self._frequency_hz

    @property
    def position_turns(self) -> float:
        return self.position_tracker.position_turns

    def start_jog_forward(self, frequency_hz: float) -> None:
        self._validate_frequency(frequency_hz)

        self.machine.start_roller_forward(frequency_hz)

        self._running = True
        self._paused = False
        self._direction = "forward"
        self._frequency_hz = frequency_hz

    def start_jog_reverse(self, frequency_hz: float) -> None:
        self._validate_frequency(frequency_hz)

        self.machine.start_roller_reverse(frequency_hz)

        self._running = True
        self._paused = False
        self._direction = "reverse"
        self._frequency_hz = frequency_hz

    def stop(self) -> None:
        self.machine.stop_roller()

        self._running = False
        self._paused = False
        self._direction = None
        self._frequency_hz = None

    def pause(self) -> None:
        if not self._running:
            return

        self.machine.stop_roller()

        self._running = False
        self._paused = True

    def reset_position(self) -> None:
        self.position_tracker.reset()

    def update(self, elapsed_seconds: float) -> None:
        if elapsed_seconds < 0:
            raise ValueError("Elapsed seconds cannot be negative")

        if not self._running:
            return

        if self._frequency_hz is None:
            return

        revolutions = self.rotation_calculator.revolutions_for_time(
            self._frequency_hz,
            elapsed_seconds,
        )

        if self._direction == "forward":
            self.position_tracker.move_forward(revolutions)
        elif self._direction == "reverse":
            self.position_tracker.move_reverse(revolutions)

    def save_point(self, point: CalibrationPoint) -> None:
        if self.calibration_store is None:
            raise RuntimeError("Calibration store is not configured")

        self.calibration_store.set(point, self.position_turns)

    @staticmethod
    def _validate_frequency(frequency_hz: float) -> None:
        if frequency_hz <= 0:
            raise ValueError("Frequency must be greater than zero")
