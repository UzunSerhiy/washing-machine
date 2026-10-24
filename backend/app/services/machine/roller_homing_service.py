import logging
import math
from functools import wraps
from threading import RLock

from app.services.machine.calibration.clock import MonotonicClock
from app.services.machine.calibration.homing import (
    HomingService,
    HomingState,
)
from app.services.machine.machine import Machine
from app.services.machine.sensors.service import RollerSensorService
from app.services.winding.rotation import RollerRotationCalculator


logger = logging.getLogger(__name__)


def _synchronized(method):
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        with self._state_lock:
            return method(self, *args, **kwargs)
    return wrapper


class RollerHomingService:
    OWNER = "homing"
    DEFAULT_FREQUENCY_HZ = 10.0

    def __init__(
        self,
        machine: Machine,
        sensor_service: RollerSensorService,
        rotation_calculator: RollerRotationCalculator,
    ) -> None:
        self._state_lock = RLock()
        self.machine = machine
        self.rotation_calculator = rotation_calculator
        self.clock = MonotonicClock()

        self.homing = HomingService(
            sensor_service=sensor_service,
            timeout_seconds=60.0,
            max_revolutions=1.2,
        )

        self._last_update_time: float | None = None
        self._frequency_hz: float | None = None
        self._position_turns = 0.0
        self._homed = False
        self._faulted = False
        self._error: str | None = None

    @property
    @_synchronized
    def searching(self) -> bool:
        return self.homing.state == HomingState.SEARCHING

    @property
    @_synchronized
    def homed(self) -> bool:
        return self._homed and not self._faulted

    @property
    @_synchronized
    def faulted(self) -> bool:
        return self._faulted

    @_synchronized
    def require_zero(self) -> None:
        if not self.homed:
            raise RuntimeError("Point 0 is not confirmed. Perform homing first.")

    @_synchronized
    def start(
        self,
        *,
        position_confirmed: bool,
        frequency_hz: float = DEFAULT_FREQUENCY_HZ,
    ) -> None:
        if self._faulted:
            raise RuntimeError("Homing fault is latched. Recovery is required.")

        if self.searching:
            raise RuntimeError("Homing is already running")

        if not position_confirmed:
            raise RuntimeError(
                "Operator must confirm roller position within the first revolution"
            )

        if not math.isfinite(frequency_hz) or not (
            0.0 < frequency_hz <= self.DEFAULT_FREQUENCY_HZ
        ):
            raise ValueError("Homing frequency must be within (0, 10] Hz")

        # Захватываем вал до изменения состояния HOME.
        self.machine.acquire_roller(self.OWNER)

        try:
            self.homing.reset()
            now = self.clock.now()
            self.homing.start(
                now=now,
                position_turns=0.0,
            )
        except Exception:
            # Команда движения ещё не отправлялась.
            self.machine.release_roller(self.OWNER)
            raise

        self._homed = False
        self._error = None
        self._position_turns = 0.0
        self._frequency_hz = frequency_hz
        self._last_update_time = now

        try:
            self.machine.start_roller_reverse(
                frequency_hz,
                owner=self.OWNER,
            )
        except Exception as exc:
            # Команда могла частично выполниться.
            # Поэтому даже успешный STOP не снимает fault.
            self._fail_and_stop(f"Failed to start homing: {exc}")
            raise

    @_synchronized
    def tick(self) -> None:
        if not self.searching:
            return

        try:
            now = self.clock.now()

            if self._last_update_time is None or self._frequency_hz is None:
                raise RuntimeError("Homing runtime is not initialized")

            elapsed = max(
                0.0,
                now - self._last_update_time,
            )
            self._last_update_time = now

            revolutions = self.rotation_calculator.revolutions_for_time(
                self._frequency_hz,
                elapsed,
            )

            if not math.isfinite(revolutions) or revolutions < 0:
                raise RuntimeError("Invalid calculated roller movement")

            self._position_turns -= revolutions

            self.homing.update(
                now=now,
                position_turns=self._position_turns,
            )

            if self.searching:
                return

            if self.homing.state == HomingState.COMPLETED:
                self._complete()
                return

            self._fail_and_stop(self.homing.error or "Homing failed")

        except Exception as exc:
            if not self._faulted:
                self._fail_and_stop(str(exc))
            raise

    def _complete(self) -> None:
        # Если STOP выбросит исключение, владение
        # не будет освобождено.
        self.machine.stop_roller(owner=self.OWNER)

        # Только для FAKE: успешная команда STOP
        # считается достаточной для завершения.
        self._homed = True
        self._position_turns = 0.0
        self._last_update_time = None
        self._frequency_hz = None

        self.machine.release_roller(self.OWNER)

    @_synchronized
    def cancel(self) -> None:
        if not self.searching:
            return

        self._homed = False
        self.homing.cancel()

        try:
            self.machine.stop_roller(owner=self.OWNER)
        except Exception as exc:
            self._faulted = True
            self._error = f"Failed to stop roller: {exc}"
            logger.exception(self._error)
            raise
        else:
            self._last_update_time = None
            self._frequency_hz = None
            self.machine.release_roller(self.OWNER)

    @_synchronized
    def invalidate(self) -> None:
        self._homed = False

    def _fail_and_stop(self, message: str) -> None:
        self._homed = False
        self._faulted = True
        self._error = message

        if self.searching:
            self.homing._fail(message)

        try:
            self.machine.stop_roller(owner=self.OWNER)
        except Exception:
            logger.exception("CRITICAL: roller STOP failed during homing")
        finally:
            self._last_update_time = None
            self._frequency_hz = None

        # В faulted владение НЕ освобождаем.
        # Требуется отдельная процедура восстановления.

    @_synchronized
    def get_status(self) -> dict:
        return {
            "state": self.homing.state.value,
            "error": self._error or self.homing.error,
            "homed": self.homed,
            "faulted": self._faulted,
            "searching": self.searching,
            "position_turns": self._position_turns,
            "roller_owner": self.machine.roller_owner,
        }

    @_synchronized
    def external_stop(self) -> None:
        """
        Вал остановлен командой другого сервиса.

        Не отправляет повторный STOP.
        Вызывается Machine после успешной команды остановки.
        """
        if not self.searching:
            return

        self._homed = False
        self.homing.cancel()
        self._error = "Homing interrupted by external STOP"
        self._last_update_time = None
        self._frequency_hz = None

        self.machine.release_roller(self.OWNER)
