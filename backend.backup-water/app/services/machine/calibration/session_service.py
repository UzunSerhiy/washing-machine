from typing import Protocol

from app.services.machine.calibration.clock import MonotonicClock
from app.services.machine.calibration.points import CalibrationPoint
from app.services.machine.calibration.session import CalibrationSession
from app.services.machine.machine import Machine
from app.services.winding.rotation import RollerRotationCalculator
from app.services.machine.calibration.stage import CalibrationStage
from app.services.machine.calibration.homing import HomingService, HomingState
from app.services.machine.sensors.service import RollerSensorService


class Clock(Protocol):
    def now(self) -> float: ...


class CalibrationSessionService:
    def __init__(
        self,
        machine: Machine,
        rotation_calculator: RollerRotationCalculator,
        clock: Clock | None = None,
        sensor_service: RollerSensorService | None = None,
    ):
        self.machine = machine
        self.rotation_calculator = rotation_calculator
        self.clock = clock or MonotonicClock()

        self._session: CalibrationSession | None = None
        self._last_update_time: float | None = None
        self.homing = (
            HomingService(sensor_service) if sensor_service is not None else None
        )

    @property
    def active(self) -> bool:
        return self._session is not None

    def start(self, material_profile_id: int) -> CalibrationSession:
        if self._session is not None:
            raise RuntimeError("Calibration session is already active")

        if self.homing is not None:
            self.homing.reset()

        self._session = CalibrationSession(
            machine=self.machine,
            rotation_calculator=self.rotation_calculator,
            material_profile_id=material_profile_id,
        )

        return self._session

    def get_current(self) -> CalibrationSession:
        if self._session is None:
            raise RuntimeError("Calibration session is not active")

        return self._session

    def jog_forward(self, frequency_hz: float) -> None:
        self._ensure_not_homing()
        session = self.get_current()

        self._sync_position()

        session.player.start_jog_forward(frequency_hz)
        self._last_update_time = self.clock.now()

    def jog_reverse(self, frequency_hz: float) -> None:
        self._ensure_not_homing()
        session = self.get_current()

        self._sync_position()

        session.player.start_jog_reverse(frequency_hz)
        self._last_update_time = self.clock.now()

    def pause(self) -> None:
        self._ensure_not_homing()
        session = self.get_current()
        self._sync_position()

        session.player.pause()
        self._last_update_time = None

    def stop(self) -> None:
        session = self.get_current()

        if self.homing is not None:
            self.homing.cancel()

        try:
            self._sync_position()
        finally:
            session.player.stop()
            self._last_update_time = None

    def reset_position(self) -> None:
        self._ensure_not_homing()
        session = self.get_current()

        self._sync_position()
        session.confirm_zero()
        self._last_update_time = None

    def mark(self, point: CalibrationPoint) -> None:
        self._ensure_not_homing()
        session = self.get_current()
        self._sync_position()
        session.set_point(point)

    def cancel(self) -> None:
        if self._session is None:
            return

        if self.homing is not None:
            self.homing.cancel()

        try:
            self._sync_position()
        finally:
            self._session.player.stop()
            self._last_update_time = None
            self._session = None

    def complete(self) -> CalibrationSession:
        self._ensure_not_homing()
        session = self.get_current()

        self._sync_position()
        session.player.stop()
        self._last_update_time = None

        session.validate()

        return session

    def tick(self) -> None:
        if self._session is None:
            return

        try:
            self._sync_position()
            self._update_homing()
        except Exception:
            if self.homing is not None:
                self.homing.cancel()

            self._last_update_time = None
            self._session.player.stop()
            raise

        if not self._session.player.running:
            self._last_update_time = None

    def _sync_position(self) -> None:
        session = self.get_current()

        if self._last_update_time is None:
            return

        now = self.clock.now()
        elapsed_seconds = now - self._last_update_time

        if elapsed_seconds < 0:
            raise RuntimeError("Clock moved backwards")

        session.player.update(elapsed_seconds)

        self._last_update_time = now

    def finish(self) -> None:
        session = self.get_current()

        if session.player.running:
            raise RuntimeError("Cannot finish calibration while roller is running")

        self._session = None
        self._last_update_time = None

    def start_brush(self, frequency_hz: float) -> None:
        self._ensure_not_homing()
        session = self.get_current()
        session.player.start_brush(frequency_hz)

    def stop_brush(self) -> None:
        session = self.get_current()
        session.player.stop_brush()

    def start_homing(self, frequency_hz: float) -> None:
        session = self.get_current()

        if self.homing is None:
            raise RuntimeError("Reference sensor is not configured")

        if session.stage != CalibrationStage.SET_ZERO:
            raise RuntimeError("Homing is only available at SET_ZERO stage")

        if session.player.running or session.player.brush_running:
            raise RuntimeError("Stop roller and brushes before homing")

        if frequency_hz <= 0:
            raise ValueError("Homing frequency must be positive")

        now = self.clock.now()

        self.homing.start(
            now=now,
            position_turns=session.position_turns,
        )

        try:
            session.player.start_jog_reverse(frequency_hz)
        except Exception:
            self.homing.cancel()
            session.player.stop()
            raise

        self._last_update_time = now

    def _update_homing(self) -> None:
        if self.homing is None:
            return

        if self.homing.state != HomingState.SEARCHING:
            return

        session = self.get_current()

        try:
            self.homing.update(
                now=self.clock.now(),
                position_turns=session.position_turns,
            )
        except Exception:
            self.homing.cancel()
            session.player.stop()
            self._last_update_time = None
            raise

        if self.homing.state == HomingState.SEARCHING:
            return

        try:
            session.player.stop()
        finally:
            self._last_update_time = None

        if self.homing.state == HomingState.COMPLETED:
            session.confirm_zero()

    def _ensure_not_homing(self) -> None:
        if self.homing is not None and self.homing.state == HomingState.SEARCHING:
            raise RuntimeError("Homing is running")
