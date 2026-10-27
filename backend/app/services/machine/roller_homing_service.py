import logging
import math
from functools import wraps
from threading import RLock
from typing import Callable

from app.services.machine.calibration.stop_confirmation import StopObservation

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
        stop_observer: Callable[[], StopObservation] | None = None,
        fault_observer: Callable[[], int] | None = None,
    ) -> None:
        self._state_lock = RLock()
        self.machine = machine
        self.rotation_calculator = rotation_calculator
        self.clock = MonotonicClock()
        self._stop_observer = stop_observer
        self._fault_observer = fault_observer
        self._awaiting_stop = False
        self._stop_deadline: float | None = None
        self._stop_confirmations = 0
        self._home_timing: dict[str, float | None] = self._empty_home_timing()

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
        self._fault_code: str | None = None
        self._session_generation: int | None = None

    @staticmethod
    def _empty_home_timing() -> dict[str, float | None]:
        return {
            "pulse_detected_at": None,
            "stop_requested_at": None,
            "stop_command_returned_at": None,
            "stop_confirmed_at": None,
        }

    def _timing_status(self) -> dict:
        timing = self._home_timing.copy()
        pulse = timing["pulse_detected_at"]
        requested = timing["stop_requested_at"]
        returned = timing["stop_command_returned_at"]
        confirmed = timing["stop_confirmed_at"]

        def milliseconds(start, end):
            return round((end - start) * 1000, 3) if start is not None and end is not None else None

        return {
            "events_monotonic_seconds": timing,
            "pulse_to_stop_request_ms": milliseconds(pulse, requested),
            "stop_command_duration_ms": milliseconds(requested, returned),
            "stop_request_to_confirmation_ms": milliseconds(requested, confirmed),
            "pulse_to_confirmation_ms": milliseconds(pulse, confirmed),
            "stop_confirmations_observed": self._stop_confirmations,
        }

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

    def start(
        self,
        *,
        position_confirmed: bool,
        frequency_hz: float = DEFAULT_FREQUENCY_HZ,
    ) -> None:
        # Capture before waiting for HOME's state lock. A stale queued start
        # must not acquire a fresh epoch after fault + recovery.
        generation = (self.machine.capture_session_generation()
                      if isinstance(self.machine, Machine) else None)
        with self._state_lock:
            self._start_locked(position_confirmed=position_confirmed,
                               frequency_hz=frequency_hz, generation=generation)

    def _require_session_generation(self) -> None:
        if self._session_generation is not None:
            self.machine.require_session_generation(self._session_generation)

    def _start_locked(self, *, position_confirmed: bool,
                      frequency_hz: float, generation: int | None) -> None:
        if generation is not None:
            self.machine.require_session_generation(generation)
        if self._faulted:
            raise RuntimeError("Homing fault is latched. Recovery is required.")

        if self.searching or self._awaiting_stop:
            raise RuntimeError("Homing is already running or awaiting stop confirmation")

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

        self._session_generation = generation
        self._homed = False
        self._error = None
        self._fault_code = None
        self._home_timing = self._empty_home_timing()
        self._position_turns = 0.0
        self._frequency_hz = frequency_hz
        self._last_update_time = now

        try:
            self.machine.start_roller_reverse(
                frequency_hz,
                owner=self.OWNER,
                **({"session_generation": generation} if generation is not None else {}),
            )
        except Exception as exc:
            # Команда могла частично выполниться.
            # Поэтому даже успешный STOP не снимает fault.
            self._fail_and_stop(f"Failed to start homing: {exc}")
            raise

    @_synchronized
    def tick(self) -> None:
        if not self.searching and not self._awaiting_stop:
            return

        try:
            self._require_session_generation()
            now = self.clock.now()
            if self._awaiting_stop:
                self._poll_stop(now)
                return

            self._check_active_drive_fault()

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
                self._home_timing["pulse_detected_at"] = now
                self._complete()
                return

            self._fail_and_stop(self.homing.error or "Homing failed")

        except Exception as exc:
            if self._session_generation is not None:
                try:
                    self._require_session_generation()
                except RuntimeError:
                    self._session_generation = None
                    self._homed = False
                    self._faulted = True
                    self._error = "Stale HOME session: fault/recovery state changed"
                    self._fault_code = "VFD_MONITOR_FAULT"
                    self._awaiting_stop = False
                    self.homing._fail(self._error)
                    raise
            if not self._faulted:
                self._fail_and_stop(str(exc))
            raise

    def _check_active_drive_fault(self) -> None:
        if self._fault_observer is None:
            return  # FAKE and legacy callers do not require Modbus telemetry.
        try:
            fault = self._fault_observer()
        except Exception as exc:
            raise RuntimeError("Roller VFD fault telemetry unavailable") from exc
        if type(fault) is not int or not 0 <= fault <= 0xFFFF:
            raise RuntimeError("Roller VFD fault telemetry invalid")
        if fault != 0:
            raise RuntimeError(f"Roller VFD fault {fault} during HOME")

    def _complete(self) -> None:
        self._require_session_generation()
        # Command acknowledgement is not proof of a stopped drive.
        self._home_timing["stop_requested_at"] = self.clock.now()
        self.machine.stop_roller(owner=self.OWNER)
        self._home_timing["stop_command_returned_at"] = self.clock.now()
        if self._stop_observer is not None:
            self._awaiting_stop = True
            self._stop_deadline = self.clock.now() + 5.0
            self._stop_confirmations = 0
            return
        # Legacy path is retained for existing FAKE-only callers.
        self._finish_stop()

    def _poll_stop(self, now: float) -> None:
        if self._stop_deadline is None or now > self._stop_deadline:
            raise RuntimeError("Roller VFD stop confirmation timeout")
        observation = self._stop_observer()
        if observation.fault != 0:
            raise RuntimeError(f"Roller VFD fault {observation.fault} during HOME stop confirmation")
        self._stop_confirmations = self._stop_confirmations + 1 if observation.confirmed else 0
        if self._stop_confirmations >= 3:
            self._home_timing["stop_confirmed_at"] = self.clock.now()
            self._finish_stop()

    def _finish_stop(self) -> None:
        self._require_session_generation()
        # This verifies drive telemetry, not absolute mechanical shaft position.
        self._homed = True
        self._session_generation = None
        self._position_turns = 0.0
        self._last_update_time = None
        self._frequency_hz = None
        self._awaiting_stop = False
        self._stop_deadline = None
        self._stop_confirmations = 0
        self.machine.release_roller(self.OWNER)

    @_synchronized
    def cancel(self) -> None:
        if not self.searching and not self._awaiting_stop:
            return

        self._awaiting_stop = False
        self._homed = False
        self.homing.cancel()
        self._session_generation = None

        try:
            self.machine.stop_roller(owner=self.OWNER)
        except Exception as exc:
            self._faulted = True
            self._error = f"Failed to stop roller: {exc}"
            self._fault_code = "STOP_COMMAND_FAILED"
            self.homing._fail(self._error)
            logger.exception(self._error)
            raise
        else:
            self._last_update_time = None
            self._frequency_hz = None
            self.machine.release_roller(self.OWNER)

    @_synchronized
    def external_motion_fault(self, reason: str) -> None:
        """Latch external VFD failure, invalidate Point0, retain HOME ownership."""
        active = self.searching or self._awaiting_stop
        self._homed = False
        self._awaiting_stop = False
        self._stop_deadline = None
        self._session_generation = None
        self._faulted = True
        self._error = reason
        self._fault_code = "VFD_MONITOR_FAULT"
        self._last_update_time = None
        self._frequency_hz = None
        if active:
            self.homing._fail(reason)
        # No STOP here: Machine already attempted it. Do not release ownership.

    @_synchronized
    def invalidate(self) -> None:
        self._homed = False

    @staticmethod
    def _classify_fault(message: str) -> str:
        normalized = message.lower()
        if "vfd fault telemetry" in normalized:
            return "VFD_TELEMETRY_UNAVAILABLE"
        if "vfd fault " in normalized:
            return "VFD_FAULT"
        if "stop confirmation timeout" in normalized:
            return "STOP_CONFIRMATION_TIMEOUT"
        if "failed to start homing" in normalized:
            return "START_COMMAND_FAILED"
        if "homing timeout" in normalized:
            return "SENSOR_TIMEOUT"
        if "travel limit" in normalized:
            return "TRAVEL_LIMIT_EXCEEDED"
        if "sensor" in normalized or "esp32" in normalized:
            return "SENSOR_UNAVAILABLE"
        if "stop" in normalized:
            return "STOP_CONFIRMATION_FAILED"
        return "HOMING_RUNTIME_ERROR"

    def _fail_and_stop(self, message: str) -> None:
        self._homed = False
        self._awaiting_stop = False
        self._stop_deadline = None
        self._session_generation = None
        self._faulted = True
        self._error = message
        self._fault_code = self._classify_fault(message)
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
    def acknowledge_fault(self, *, operator_confirmed_stopped: bool) -> None:
        """Clear only HOME's software latch; never reset a VFD or command motion.

        Operator must separately release E-stop, use physical RESET, and
        verify that the roller is mechanically stopped.
        """
        if not self._faulted:
            raise RuntimeError("No HOME fault to acknowledge")
        if not operator_confirmed_stopped:
            raise RuntimeError("Operator must confirm the roller is mechanically stopped")
        if self.searching or self._awaiting_stop:
            raise RuntimeError("Cannot acknowledge while HOME is active")
        if self.machine.roller_owner != self.OWNER:
            raise RuntimeError("HOME does not own the roller")
        if self._fault_observer is None or self._stop_observer is None:
            raise RuntimeError("VFD recovery telemetry is not configured")

        # No writes or STOP/RUN commands during acknowledgement.
        for _ in range(3):
            try:
                fault = self._fault_observer()
                observation = self._stop_observer()
            except Exception as exc:
                raise RuntimeError("VFD recovery telemetry unavailable") from exc
            if type(fault) is not int or fault != 0:
                raise RuntimeError("VFD fault is not cleared")
            if not isinstance(observation, StopObservation):
                raise RuntimeError("Invalid VFD stop observation")
            if (type(observation.fault) is not int or observation.fault != 0
                    or type(observation.status) is not int or observation.status != 3
                    or type(observation.frequency_hz) not in (int, float)
                    or not math.isfinite(observation.frequency_hz)
                    or observation.frequency_hz != 0.0
                    or observation.confirmed is not True):
                raise RuntimeError("Roller VFD stop is not confirmed")

        # Release ownership before clearing latch: on failure remain faulted.
        self.machine.release_roller(self.OWNER)
        self.homing.reset()
        self._session_generation = None
        self._homed = False
        self._position_turns = 0.0
        self._faulted = False
        self._error = None
        self._fault_code = None
        self._frequency_hz = None
        self._last_update_time = None
        self._home_timing = self._empty_home_timing()
        self._stop_confirmations = 0

    @_synchronized
    def complete_motion_fault_recovery(self) -> None:
        """Software HOME cleanup after global three-drive recovery verification.

        Unlike standalone HOME acknowledgement, monitor faults may happen
        when HOME never owned the roller.
        """
        if self.searching or self._awaiting_stop:
            raise RuntimeError("HOME still active")
        owner = self.machine.roller_owner
        if owner not in (None, self.OWNER):
            raise RuntimeError("Roller reserved by another service")
        if owner == self.OWNER:
            self.machine.release_roller(self.OWNER)
        self.homing.reset()
        self._session_generation = None
        self._homed = False
        self._position_turns = 0.0
        self._faulted = False
        self._error = None
        self._fault_code = None
        self._frequency_hz = None
        self._last_update_time = None
        self._home_timing = self._empty_home_timing()
        self._stop_confirmations = 0

    @_synchronized
    def get_status(self) -> dict:
        return {
            "state": self.homing.state.value,
            "error": self._error or self.homing.error,
            "fault_code": self._fault_code,
            "homed": self.homed,
            "faulted": self._faulted,
            "searching": self.searching,
            "awaiting_stop_confirmation": self._awaiting_stop,
            "position_turns": self._position_turns,
            "roller_owner": self.machine.roller_owner,
            "timing": self._timing_status(),
        }

    @_synchronized
    def external_stop(self) -> None:
        """
        Вал остановлен командой другого сервиса.

        Не отправляет повторный STOP.
        Вызывается Machine после успешной команды остановки.
        """
        if not self.searching and not self._awaiting_stop:
            return

        self._awaiting_stop = False
        self._homed = False
        self.homing.cancel()
        self._error = "Homing interrupted by external STOP"
        self._last_update_time = None
        self._frequency_hz = None

        self.machine.release_roller(self.OWNER)
