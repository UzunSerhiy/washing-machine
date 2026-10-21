from enum import Enum

from app.services.machine.sensors.service import RollerSensorService


class HomingState(str, Enum):
    IDLE = "idle"
    SEARCHING = "searching"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ERROR = "error"


class HomingService:
    def __init__(
        self,
        sensor_service: RollerSensorService,
        timeout_seconds: float = 15.0,
        max_revolutions: float = 1.2,
    ) -> None:
        self.sensor_service = sensor_service
        self.timeout_seconds = timeout_seconds
        self.max_revolutions = max_revolutions

        self.state = HomingState.IDLE
        self.error: str | None = None

        self._started_at: float | None = None
        self._start_position: float | None = None
        self._initial_pulses: int | None = None
        self._last_sequence: int | None = None
        self._sensor_was_released = False

    def start(self, now: float, position_turns: float) -> None:
        if self.state == HomingState.SEARCHING:
            raise RuntimeError("Homing is already running")

        sensor = self.sensor_service.get_state()

        if not sensor.connected:
            raise RuntimeError("Reference sensor is disconnected")
        if sensor.triggered:
            raise RuntimeError("Release reference sensor before homing")

        self.state = HomingState.SEARCHING
        self.error = None

        self._started_at = now
        self._start_position = position_turns
        self._initial_pulses = sensor.pulses
        self._last_sequence = sensor.sequence
        self._sensor_was_released = not sensor.triggered

    def update(self, now: float, position_turns: float) -> None:
        if self.state != HomingState.SEARCHING:
            return

        sensor = self.sensor_service.get_state()

        if not sensor.connected:
            self._fail("Reference sensor disconnected")
            return

        if self._started_at is None or self._start_position is None:
            self._fail("Homing was not initialized")
            return

        if now - self._started_at > self.timeout_seconds:
            self._fail("Homing timeout")
            return

        distance = abs(position_turns - self._start_position)

        if distance > self.max_revolutions:
            self._fail("Homing travel limit exceeded")
            return

        if not sensor.triggered:
            self._sensor_was_released = True

        if (
            self._sensor_was_released
            and sensor.triggered
            and self._initial_pulses is not None
            and sensor.pulses > self._initial_pulses
        ):
            self.state = HomingState.COMPLETED

        self._last_sequence = sensor.sequence

    def reset(self) -> None:
        if self.state == HomingState.SEARCHING:
            raise RuntimeError("Cannot reset homing while searching")

        self.state = HomingState.IDLE
        self.error = None
        self._started_at = None
        self._start_position = None
        self._initial_pulses = None
        self._last_sequence = None
        self._sensor_was_released = False

    def cancel(self) -> None:
        if self.state == HomingState.SEARCHING:
            self.state = HomingState.CANCELLED

    def _fail(self, message: str) -> None:
        self.state = HomingState.ERROR
        self.error = message
