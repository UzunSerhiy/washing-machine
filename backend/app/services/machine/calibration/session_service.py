from typing import Protocol

from app.services.machine.calibration.clock import MonotonicClock
from app.services.machine.calibration.points import CalibrationPoint
from app.services.machine.calibration.session import CalibrationSession
from app.services.machine.machine import Machine
from app.services.winding.rotation import RollerRotationCalculator


class Clock(Protocol):
    def now(self) -> float: ...


class CalibrationSessionService:
    def __init__(
        self,
        machine: Machine,
        rotation_calculator: RollerRotationCalculator,
        clock: Clock | None = None,
    ):
        self.machine = machine
        self.rotation_calculator = rotation_calculator
        self.clock = clock or MonotonicClock()

        self._session: CalibrationSession | None = None
        self._last_update_time: float | None = None

    @property
    def active(self) -> bool:
        return self._session is not None

    def start(self, material_profile_id: int) -> CalibrationSession:
        if self._session is not None:
            raise RuntimeError("Calibration session is already active")

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
        session = self.get_current()

        self._sync_position()

        session.player.start_jog_forward(frequency_hz)
        self._last_update_time = self.clock.now()

    def jog_reverse(self, frequency_hz: float) -> None:
        session = self.get_current()

        self._sync_position()

        session.player.start_jog_reverse(frequency_hz)
        self._last_update_time = self.clock.now()

    def pause(self) -> None:
        session = self.get_current()
        self._sync_position()

        session.player.pause()
        self._last_update_time = None

    def stop(self) -> None:
        session = self.get_current()
        self._sync_position()
        session.player.stop()

        self._last_update_time = None

    def reset_position(self) -> None:
        session = self.get_current()
        self._sync_position()
        session.player.reset_position()
        if session.player.running:
            self._last_update_time = self.clock.now()

    def mark(self, point: CalibrationPoint) -> None:
        session = self.get_current()
        self._sync_position()
        session.set_point(point)

    def cancel(self) -> None:
        if self._session is None:
            return

        self._sync_position()
        self._session.player.stop()
        self._last_update_time = None
        self._session = None

    def complete(self) -> CalibrationSession:
        session = self.get_current()

        self._sync_position()

        session.player.stop()
        self._last_update_time = None

        session.validate()

        self._session = None

        return session

    def tick(self) -> None:
        if self._session is None:
            return

        self._sync_position()

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
