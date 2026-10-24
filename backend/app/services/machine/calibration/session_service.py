from typing import Protocol

from app.services.machine.calibration.clock import MonotonicClock
from app.services.machine.calibration.points import CalibrationPoint
from app.services.machine.calibration.session import CalibrationSession
from app.services.machine.machine import Machine
from app.services.winding.rotation import RollerRotationCalculator
from app.services.machine.calibration.stage import CalibrationStage
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
        self._auto_unwinding = False
        self._auto_winding = False
        self._saved = False
        self._water_reverse_started = False
        self._auto_paused = False
        self.roller_homming_service = None

    @property
    def active(self) -> bool:
        return self._session is not None

    def start(self, material_profile_id: int) -> CalibrationSession:
        if self._session is not None:
            raise RuntimeError("Calibration session is already active")

        if self.roller_homing_service is None:
            raise RuntimeError("Roller homing service is not configured")

        self.roller_homing_service.require_zero()

        self._saved = False
        self._auto_unwinding = False
        self._auto_winding = False
        self._auto_paused = False
        self._water_reverse_started = False
        self._last_update_time = None

        self._session = CalibrationSession(
            machine=self.machine,
            rotation_calculator=self.rotation_calculator,
            material_profile_id=material_profile_id,
        )

        return self._session

    def set_roller_homing_service(self, service) -> None:
        self.roller_homing_service = service

    def get_current(self) -> CalibrationSession:
        if self._session is None:
            raise RuntimeError("Calibration session is not active")

        return self._session

    @property
    def saved(self) -> bool:
        return self._saved

    @property
    def auto_mode(self) -> str | None:
        if self._auto_unwinding:
            return "unwinding"
        if self._auto_winding:
            return "winding"
        if self._auto_paused:
            return "paused"
        return None

    def _motion_limits(self):
        session = self.get_current()
        if self._saved:
            return (
                session.machine_calibration.washing_stop_turns,
                session.winding_calibration.material_end_turns,
            )
        if session.stage == CalibrationStage.WATER_START:
            return (
                session.machine_calibration.material_start_turns,
                session.winding_calibration.material_end_turns,
            )
        if session.stage == CalibrationStage.READY_TO_UNWIND:
            return (
                session.machine_calibration.material_start_turns,
                session.winding_calibration.material_end_turns,
            )
        if session.stage == CalibrationStage.WASHING_STOP:
            return (0.0, session.machine_calibration.material_start_turns)
        if self._saved:
            return (
                session.machine_calibration.washing_stop_turns,
                session.winding_calibration.material_end_turns,
            )
        return (None, None)

    def jog_forward(self, frequency_hz: float) -> None:
        self._ensure_not_homing()
        session = self.get_current()

        self._sync_position()

        if (
            self._saved
            or self._auto_unwinding
            or self._auto_winding
            or self._auto_paused
        ):
            raise RuntimeError("Manual jog unavailable during automatic motion")
        _, upper = self._motion_limits()
        if upper is not None and session.position_turns >= upper - 1e-6:
            raise RuntimeError("Forward limit reached")
        if session.player.running:
            raise RuntimeError("Pause roller before changing direction")
        session.player.start_jog_forward(frequency_hz)
        self._last_update_time = self.clock.now()

    def jog_reverse(
        self, frequency_hz: float, brush_frequency_hz: float | None = None
    ) -> None:
        self._ensure_not_homing()
        session = self.get_current()

        self._sync_position()

        if (
            self._saved
            or self._auto_unwinding
            or self._auto_winding
            or self._auto_paused
        ):
            raise RuntimeError("Manual jog unavailable during automatic motion")
        lower, _ = self._motion_limits()
        if lower is not None and session.position_turns <= lower + 1e-6:
            raise RuntimeError("Reverse limit reached")
        if session.player.running:
            raise RuntimeError("Pause roller before changing direction")
        if (
            session.stage == CalibrationStage.WATER_START
            and not self._water_reverse_started
        ):
            if brush_frequency_hz is None or brush_frequency_hz <= 0:
                raise ValueError("Brush speed required for first reverse movement")
            try:
                session.player.start_brush(brush_frequency_hz)
                session.player.start_jog_reverse(frequency_hz)
            except Exception:
                session.player.stop()
                raise
            self._water_reverse_started = True
        else:
            session.player.start_jog_reverse(frequency_hz)
        self._last_update_time = self.clock.now()

    def pause(self) -> None:
        self._ensure_not_homing()
        session = self.get_current()
        self._sync_position()

        if self._auto_paused:
            return

        was_auto = self._auto_unwinding or self._auto_winding

        session.player.pause()

        if session.player.brush_running and (
            session.stage
            in (
                CalibrationStage.WATER_START,
                CalibrationStage.READY_TO_UNWIND,
            )
            or was_auto
        ):
            session.player.stop_brush()

        self._auto_paused = was_auto
        self._auto_unwinding = False
        self._auto_winding = False
        self._last_update_time = None

    def stop(self) -> None:
        session = self.get_current()

        try:
            self._sync_position()
        finally:
            session.player.stop()
            self._auto_unwinding = False
            self._auto_winding = False
            self._auto_paused = False
            self._last_update_time = None

    def reset_position(self) -> None:
        self._ensure_not_homing()

        if self.roller_homing_service is None:
            raise RuntimeError("Roller homing service is not configured")

        self.roller_homing_service.require_zero()

        session = self.get_current()

        if session.player.running or session.player.brush_running:
            raise RuntimeError("Stop roller and brushes before resetting position")

        self._sync_position()
        session.confirm_zero()
        self._last_update_time = None

    def mark(
        self, point: CalibrationPoint, brush_frequency_hz: float | None = None
    ) -> None:
        self._ensure_not_homing()
        session = self.get_current()
        self._sync_position()
        if self._auto_unwinding or self._auto_winding or self._auto_paused:
            raise RuntimeError("Cannot mark during automatic movement")
        session.set_point(point)
        if point == CalibrationPoint.WATER_START:
            if brush_frequency_hz is None or brush_frequency_hz <= 0:
                raise ValueError(
                    "Brush frequency required to start automatic unwinding"
                )
            self.next_step(50.0, brush_frequency_hz)

    def cancel(self) -> None:
        if self._session is None:
            return

        try:
            self._sync_position()
        finally:
            self._session.player.stop()
            self._auto_unwinding = False
            self._auto_winding = False
            self._auto_paused = False
            self._last_update_time = None
            self._session = None
            self._saved = False
            self._water_reverse_started = False

    def complete(self) -> CalibrationSession:
        self._ensure_not_homing()
        session = self.get_current()

        self._sync_position()
        if session.player.running or session.player.brush_running:
            raise RuntimeError("Stop roller and brushes before completing calibration")
        session.validate()
        self._last_update_time = None

        return session

    def tick(self) -> None:
        if self._session is None:
            return

        try:
            self._sync_position()
        except Exception:
            self._last_update_time = None
            self._session.player.stop()
            self._auto_unwinding = False
            raise

        if not self._session.player.running:
            self._last_update_time = None

    def _sync_position(self) -> None:
        session = self.get_current()
        if self._last_update_time is None:
            return
        now = self.clock.now()
        elapsed = now - self._last_update_time
        if elapsed < 0:
            raise RuntimeError("Clock moved backwards")
        if not session.player.running:
            self._last_update_time = None
            return
        hz = session.player.frequency_hz
        direction = session.player.direction
        if hz is None or direction is None:
            raise RuntimeError("Invalid roller state")
        lower, upper = self._motion_limits()
        target = upper if direction == "forward" else lower
        remaining = (
            None
            if target is None
            else (
                (target - session.position_turns)
                if direction == "forward"
                else (session.position_turns - target)
            )
        )
        revolutions = self.rotation_calculator.revolutions_for_time(hz, elapsed)
        if remaining is not None and (remaining <= 0 or revolutions >= remaining):
            if remaining > 0:
                lo, hi = 0.0, elapsed
                for _ in range(40):
                    mid = (lo + hi) / 2
                    if (
                        self.rotation_calculator.revolutions_for_time(hz, mid)
                        < remaining
                    ):
                        lo = mid
                    else:
                        hi = mid
                session.player.update(hi)
            session.player.stop()
            if target is not None:
                session.position_tracker.set_position(target)
            if self._auto_unwinding:
                session.stage = CalibrationStage.WASHING_STOP
            if self._auto_winding:
                session.stage = CalibrationStage.REWIND_COMPLETE
            self._auto_unwinding = False
            self._auto_winding = False
            self._auto_paused = False
            self._last_update_time = None
            return
        session.player.update(elapsed)
        self._last_update_time = now

    def next_step(self, roller_frequency_hz: float, brush_frequency_hz: float) -> None:
        self._ensure_not_homing()
        session = self.get_current()
        self._sync_position()
        if session.stage != CalibrationStage.READY_TO_UNWIND:
            raise RuntimeError("Automatic unwind only available after Water Start")
        if session.player.running or session.player.brush_running:
            raise RuntimeError("Stop both drives before automatic unwind")
        if session.machine_calibration.water_start_turns is None:
            raise RuntimeError("Water Start not marked")
        if session.position_turns <= session.machine_calibration.material_start_turns:
            raise RuntimeError("Material Start already reached")
        if brush_frequency_hz <= 0:
            raise ValueError("Brush frequency must be positive")
        try:
            session.player.start_brush(brush_frequency_hz)
            session.player.start_jog_reverse(50.0)  # maximum roller frequency
        except Exception:
            session.player.stop()
            raise
        self._auto_unwinding = True
        self._auto_paused = False
        self._last_update_time = self.clock.now()

    def mark_saved(self) -> None:
        session = self.get_current()
        session.validate()
        if session.player.running or session.player.brush_running:
            raise RuntimeError("Stop drives before saving")
        self._saved = True

    def start_auto_wind(self) -> None:
        self._ensure_not_homing()
        session = self.get_current()
        self._sync_position()

        if not self._saved:
            raise RuntimeError("Save calibration before auto winding")

        if session.player.running or session.player.brush_running:
            raise RuntimeError("Stop drives before winding")

        material_end = session.winding_calibration.material_end_turns

        if material_end is None:
            raise RuntimeError("Material End is not calibrated")

        if session.position_turns >= material_end:
            raise RuntimeError("Material End already reached")

        if session.stage == CalibrationStage.REWIND_COMPLETE:
            raise RuntimeError("Auto winding is already completed")

        if session.stage != CalibrationStage.WASHING_STOP:
            raise RuntimeError("Auto winding requires Washing Stop stage")

        if self._auto_unwinding or self._auto_winding or self._auto_paused:
            raise RuntimeError("Automatic movement is already active")

        session.player.start_jog_forward(50.0)  # maximum roller frequency
        self._auto_winding = True
        self._auto_paused = False
        self._last_update_time = self.clock.now()

    def resume_auto(self, brush_frequency_hz: float) -> None:
        if not self._auto_paused:
            raise RuntimeError("No paused automatic movement")
        session = self.get_current()
        if session.stage == CalibrationStage.READY_TO_UNWIND:
            self._auto_paused = False
            self.next_step(50.0, brush_frequency_hz)
        elif self._saved:
            self._auto_paused = False
            self.start_auto_wind()
        else:
            raise RuntimeError("No automatic movement to resume")

    def finish(self) -> None:
        session = self.get_current()

        if session.player.running:
            raise RuntimeError("Cannot finish calibration while roller is running")

        self._session = None
        self._auto_unwinding = False
        self._auto_winding = False
        self._auto_paused = False
        self._saved = False
        self._last_update_time = None

    def start_brush(self, frequency_hz: float) -> None:
        self._ensure_not_homing()
        session = self.get_current()
        if self._saved or session.stage in (
            CalibrationStage.WATER_START,
            CalibrationStage.READY_TO_UNWIND,
        ):
            raise RuntimeError(
                "Brushes are controlled by Next during reverse calibration"
            )
        session.player.start_brush(frequency_hz)

    def stop_brush(self) -> None:
        session = self.get_current()
        session.player.stop_brush()

    def _ensure_not_homing(self) -> None:
        if (
            self.roller_homing_service is not None
            and self.roller_homing_service.searching
        ):
            raise RuntimeError("Roller homing is running")

    def require_geometry_ready(self) -> CalibrationSession:
        self._ensure_not_homing()
        self.tick()

        session = self.get_current()

        if not self._saved:
            raise RuntimeError("Save positional calibration first")

        if session.stage != CalibrationStage.REWIND_COMPLETE:
            raise RuntimeError("Auto winding is not completed")

        if self.auto_mode is not None:
            raise RuntimeError("Automatic movement is still active")

        if session.player.running or session.player.brush_running:
            raise RuntimeError("Stop roller and brushes before saving geometry")

        end = session.winding_calibration.material_end_turns

        if end is None or abs(session.position_turns - end) > 1e-6:
            raise RuntimeError("Roller has not reached Material End")

        return session
