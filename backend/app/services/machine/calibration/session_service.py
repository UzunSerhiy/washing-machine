from typing import Protocol
from contextlib import nullcontext
from functools import wraps

from app.services.machine.operation import OperationMode

from app.services.machine.calibration.clock import MonotonicClock
from app.services.machine.calibration.points import CalibrationPoint
from app.services.machine.calibration.session import CalibrationSession
from app.services.machine.machine import Machine
from app.services.winding.rotation import RollerRotationCalculator
from app.services.machine.calibration.stage import CalibrationStage
from app.services.machine.sensors.service import RollerSensorService


class Clock(Protocol):
    def now(self) -> float: ...


def _mode_serialized(method):
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        operation = getattr(self, "operation_service", None)
        lock = getattr(operation, "_mode_lock", None)
        with lock if lock is not None else nullcontext():
            return method(self, *args, **kwargs)
    return wrapper


class CalibrationSessionService:
    def __init__(
        self,
        machine: Machine,
        rotation_calculator: RollerRotationCalculator,
        clock: Clock | None = None,
        sensor_service: RollerSensorService | None = None,
    ):
        self.machine = machine
        self.sensor_service = sensor_service
        self._return_to_zero = False
        self._return_sensor_sequence = None
        self._return_slow = False
        self.rotation_calculator = rotation_calculator
        self.clock = clock or MonotonicClock()

        self._session: CalibrationSession | None = None
        self._last_update_time: float | None = None
        self._auto_unwinding = False
        self._auto_winding = False
        self._saved = False
        self._geometry_saved = False
        self._water_reverse_started = False
        self._auto_paused = False
        self.roller_homing_service = None
        self._motion_fault: str | None = None
        self._session_generation: int | None = None
        self.operation_service = None
        self._session_mode_revision: int | None = None
        self._edit_mode = False
        self._edit_target: CalibrationPoint | None = None
        self._edit_navigating = False
        self._edit_adjusting = False
        self._edit_moved = False
        self._edit_return_confirmed = False
        self._edit_route = []
        self._edit_wait_until = None
        self._edit_speed = 5.0
        self._edit_brush_speed = 15.0
        self._edit_committed = False

    @property
    def active(self) -> bool:
        return self._session is not None

    def set_operation_service(self, operation_service) -> None:
        self.operation_service = operation_service

    @_mode_serialized
    def start(self, material_profile_id: int) -> CalibrationSession:
        if getattr(self, "operation_service", None) is not None:
            if self.operation_service.state.mode != OperationMode.CALIBRATION:
                raise RuntimeError("CALIBRATION mode is required")
            if self.operation_service.state.material_profile_id != material_profile_id:
                raise RuntimeError("Calibration material profile mismatch")
        if self._motion_fault is not None:
            raise RuntimeError(f"Calibration motion fault latched: {self._motion_fault}")
        if self._session is not None:
            raise RuntimeError("Calibration session is already active")

        if self.roller_homing_service is None:
            raise RuntimeError("Roller homing service is not configured")

        self.roller_homing_service.require_zero()
        generation = self.machine.capture_session_generation()

        self._edit_mode = False
        self._edit_target = None
        self._edit_navigating = False
        self._edit_adjusting = False
        self._edit_moved = False
        self._edit_return_confirmed = False
        self._edit_route = []
        self._edit_wait_until = None
        self._edit_committed = False
        self._saved = False
        self._geometry_saved = False
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
        self._session.player.session_generation = generation
        self._session_generation = generation
        self._session_mode_revision = (getattr(self.operation_service, "_mode_revision", None))
        # Shared HOME has already established the reference position.
        self._session.confirm_zero()

        return self._session

    def set_roller_homing_service(self, service) -> None:
        self.roller_homing_service = service

    def get_current(self) -> CalibrationSession:
        if self._motion_fault is not None:
            raise RuntimeError(f"Calibration motion fault latched: {self._motion_fault}")
        if self._session is None:
            raise RuntimeError("Calibration session is not active")

        self._require_session_generation()
        if getattr(self, "operation_service", None) is not None:
            if self.operation_service.state.mode != OperationMode.CALIBRATION:
                raise RuntimeError("Calibration session is no longer in CALIBRATION mode")
            if self._session_mode_revision != self.operation_service._mode_revision:
                raise RuntimeError("Calibration session belongs to a previous mode revision")
        return self._session

    def _require_session_generation(self) -> None:
        if self._session_generation is None:
            raise RuntimeError("Calibration session has no motion generation")
        self.machine.require_session_generation(self._session_generation)

    @property
    def editing(self) -> bool:
        return self._edit_mode

    @property
    def edit_target(self) -> str | None:
        return self._edit_target.value if self._edit_target else None

    @property
    def edit_adjusting(self) -> bool:
        return self._edit_adjusting

    @_mode_serialized
    def start_edit(self, material_profile_id: int, data) -> CalibrationSession:
        session = self.start(material_profile_id)
        try:
            session.machine_calibration.set_washing_stop(data.washing_stop_turns)
            session.machine_calibration.set_material_start(data.material_start_turns)
            session.machine_calibration.set_water_start(data.water_start_turns)
            session.winding_calibration.set_material_end(data.material_end_turns)
            session.stage = CalibrationStage.WASHING_STOP
            self._edit_mode = True
            self._edit_target = None
            return session
        except Exception:
            self.cancel()
            raise

    def _edit_start_leg(self) -> None:
        session = self.get_current()
        if not self._edit_route:
            self._edit_navigating = False
            self._edit_wait_until = None
            return
        point = self._edit_route[0]
        target = session.store.get(point)
        if target is None:
            raise RuntimeError("Missing calibration route point")
        delta = target - session.position_turns
        if abs(delta) <= 0.01:
            self._edit_route.pop(0)
            self._edit_wait_until = self.clock.now() + 2 if self._edit_route else None
            if not self._edit_route:
                self._edit_navigating = False
            return
        # Brushes only on the wash-directed reverse leg (Material End -> Water Start / Washing Stop).
        # Unwinding outward to Point0 must never energize brushes.
        wash_reverse = delta < 0 and session.position_turns > session.machine_calibration.water_start_turns + 0.01 and target >= session.machine_calibration.washing_stop_turns - 0.01
        if wash_reverse:
            session.player.start_brush(self._edit_brush_speed)
        try:
            if delta > 0:
                session.player.start_jog_forward(self._edit_speed)
            else:
                session.player.start_jog_reverse(self._edit_speed)
        except Exception:
            if session.player.brush_running:
                session.player.stop_brush()
            raise
        self._last_update_time = self.clock.now()

    @_mode_serialized
    def edit_navigate(self, point: CalibrationPoint, frequency_hz: float = 5.0, brush_frequency_hz: float = 15.0) -> None:
        self._ensure_not_homing()
        session = self.get_current()
        if not self._edit_mode or self._edit_committed:
            raise RuntimeError("No active editable calibration")
        self._sync_position()
        if session.player.running or session.player.brush_running or self._edit_navigating:
            raise RuntimeError("Stop drives before navigation")
        if not 0 < frequency_hz <= 50 or not 0 < brush_frequency_hz <= 50:
            raise ValueError("Drive speed must be between 0 and 50 Hz")
        if session.store.get(point) is None:
            raise ValueError("Point is not calibrated")
        order = [CalibrationPoint.MATERIAL_START, CalibrationPoint.MATERIAL_END, CalibrationPoint.WATER_START, CalibrationPoint.WASHING_STOP]
        position = session.position_turns
        target_index = order.index(point)
        # When departing Point0, respect the established calibration path.
        if abs(position) <= 0.01:
            route = order[:target_index + 1]
        else:
            route = [point]
            # Material End -> Washing Stop must pass through Water Start.
            if position > session.machine_calibration.water_start_turns + 0.01 and point == CalibrationPoint.WASHING_STOP:
                route = [CalibrationPoint.WATER_START, point]
        self._edit_target = point
        self._edit_adjusting = False
        self._edit_route = route
        self._edit_wait_until = None
        self._edit_speed = frequency_hz
        self._edit_brush_speed = brush_frequency_hz
        self._edit_navigating = True
        self._edit_moved = True
        self._edit_return_confirmed = False
        self._edit_start_leg()

    @_mode_serialized
    def edit_begin_adjust(self) -> None:
        session = self.get_current()
        self._sync_position()
        if not self._edit_mode or self._edit_committed or self._edit_target is None:
            raise RuntimeError("Select a point first")
        if self._edit_navigating or session.player.running or session.player.brush_running:
            raise RuntimeError("Wait until movement stops")
        if abs(session.position_turns - session.store.get(self._edit_target)) > 0.05:
            raise RuntimeError("Navigate to the selected point first")
        self._edit_adjusting = True
        self._edit_moved = True
        self._edit_return_confirmed = False

    @_mode_serialized
    def edit_save_point(self) -> None:
        session = self.get_current()
        self._sync_position()
        if not self._edit_mode or self._edit_committed or not self._edit_adjusting or self._edit_target is None:
            raise RuntimeError("Point adjustment is not active")
        if session.player.running or session.player.brush_running:
            raise RuntimeError("Stop drives before saving point")
        point = self._edit_target
        position = session.position_turns
        values = {
            CalibrationPoint.WASHING_STOP: session.machine_calibration.washing_stop_turns,
            CalibrationPoint.MATERIAL_START: session.machine_calibration.material_start_turns,
            CalibrationPoint.WATER_START: session.machine_calibration.water_start_turns,
            CalibrationPoint.MATERIAL_END: session.winding_calibration.material_end_turns,
        }
        values[point] = position
        if not (0 < values[CalibrationPoint.WASHING_STOP] < values[CalibrationPoint.MATERIAL_START] < values[CalibrationPoint.WATER_START] < values[CalibrationPoint.MATERIAL_END]):
            raise ValueError("Invalid point order: 0 < Washing Stop < Material Start < Water Start < Material End")
        if point == CalibrationPoint.MATERIAL_END:
            session.winding_calibration.set_material_end(position)
        else:
            session.machine_calibration.set_point(point, position)
        self._edit_adjusting = False

    @_mode_serialized
    def edit_prepare_commit(self) -> CalibrationSession:
        session = self.get_current()
        self._sync_position()
        if not self._edit_mode or self._edit_committed or self._edit_navigating or self._edit_adjusting:
            raise RuntimeError("Finish point adjustment before saving")
        if session.player.running or session.player.brush_running:
            raise RuntimeError("Stop drives before saving")
        session.validate()
        return session

    @_mode_serialized
    def edit_mark_committed(self) -> None:
        self.edit_prepare_commit()
        self._edit_committed = True
        self._saved = True
        self._geometry_saved = True
        self._edit_adjusting = False

    @property
    def saved(self) -> bool:
        return self._saved

    @property
    def auto_mode(self) -> str | None:
        if self._return_to_zero:
            return "returning_zero"
        if self._auto_unwinding:
            return "unwinding"
        if self._auto_winding:
            return "winding"
        if self._auto_paused:
            return "paused"
        return None

    def _motion_limits(self):
        session = self.get_current()
        if self._edit_mode:
            return (0.0, self._session.winding_calibration.material_end_turns)
        if self._return_to_zero:
            return (-0.25, session.winding_calibration.material_end_turns)
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

    @_mode_serialized
    def jog_forward(self, frequency_hz: float, brush_frequency_hz: float | None = None) -> None:
        self._ensure_not_homing()
        session = self.get_current()

        self._sync_position()

        if self._edit_mode and (not self._edit_adjusting or self._edit_committed):
            raise RuntimeError("Choose Edit Point before jogging")
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
        if not self._edit_mode and session.stage in (CalibrationStage.WATER_START, CalibrationStage.WASHING_STOP):
            if brush_frequency_hz is None or brush_frequency_hz <= 0:
                raise ValueError("Brush speed required for material positioning")
            try:
                if not session.player.brush_running:
                    session.player.start_brush(brush_frequency_hz)
                session.player.start_jog_forward(frequency_hz)
            except Exception:
                session.player.stop()
                raise
        else:
            session.player.start_jog_forward(frequency_hz)
        self._last_update_time = self.clock.now()

    @_mode_serialized
    def jog_reverse(
        self, frequency_hz: float, brush_frequency_hz: float | None = None
    ) -> None:
        self._ensure_not_homing()
        session = self.get_current()

        self._sync_position()

        if self._edit_mode and (not self._edit_adjusting or self._edit_committed):
            raise RuntimeError("Choose Edit Point before jogging")
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
        if not self._edit_mode and session.stage in (CalibrationStage.WATER_START, CalibrationStage.WASHING_STOP):
            if brush_frequency_hz is None or brush_frequency_hz <= 0:
                raise ValueError("Brush speed required for material positioning")
            try:
                if not session.player.brush_running:
                    session.player.start_brush(brush_frequency_hz)
                session.player.start_jog_reverse(frequency_hz)
            except Exception:
                session.player.stop()
                raise
            if session.stage == CalibrationStage.WATER_START:
                self._water_reverse_started = True
        else:
            session.player.start_jog_reverse(frequency_hz)
        self._last_update_time = self.clock.now()

    @_mode_serialized
    def pause(self) -> None:
        self._ensure_not_homing()
        session = self.get_current()
        self._sync_position()

        if self._auto_paused:
            return

        was_auto = self._auto_unwinding or self._auto_winding or self._return_to_zero
        self._edit_navigating = False
        self._edit_route = []
        self._edit_wait_until = None

        session.player.pause()

        if session.player.brush_running and (
            session.stage
            in (
                CalibrationStage.WATER_START,
                CalibrationStage.READY_TO_UNWIND,
                CalibrationStage.WASHING_STOP,
            )
            or was_auto
        ):
            session.player.stop_brush()

        self._auto_paused = was_auto
        self._auto_unwinding = False
        self._auto_winding = False
        self._return_to_zero = False
        self._last_update_time = None

    @_mode_serialized
    def stop(self) -> None:
        session = self.get_current()

        try:
            self._sync_position()
        finally:
            session.player.stop()
            self._auto_unwinding = False
            self._auto_winding = False
            self._return_to_zero = False
            self._auto_paused = False
            self._edit_navigating = False
            self._edit_route = []
            self._edit_wait_until = None
            if session.player.brush_running:
                session.player.stop_brush()
            self._last_update_time = None

    @_mode_serialized
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

    @_mode_serialized
    def mark(
        self, point: CalibrationPoint, brush_frequency_hz: float | None = None
    ) -> None:
        self._ensure_not_homing()
        session = self.get_current()
        self._sync_position()
        if self._auto_unwinding or self._auto_winding or self._auto_paused:
            raise RuntimeError("Cannot mark during automatic movement")
        if self._edit_mode:
            raise RuntimeError("Use Edit Point instead of Mark")
        session.set_point(point)
        if point == CalibrationPoint.WATER_START:
            if brush_frequency_hz is None or brush_frequency_hz <= 0:
                raise ValueError(
                    "Brush frequency required to start automatic unwinding"
                )
            self.next_step(50.0, brush_frequency_hz)

    @_mode_serialized
    def cancel(self) -> None:
        if self._session is None:
            return
        if self._edit_mode:
            self._sync_position()
            # Never discard the only live position tracker away from Point0.
            if (self._edit_moved and not self._edit_return_confirmed) or abs(self._session.position_turns) > 0.01 or self._return_to_zero:
                if self._session.player.running:
                    self._session.player.stop()
                    self._edit_navigating = False
                    self._return_to_zero = False
                    self._last_update_time = None
                raise RuntimeError("Position is away from Point0. Motion stopped; use Return to Point0 before Cancel Editing.")

        try:
            self._require_session_generation()
            self._sync_position()
        finally:
            self._session.player.stop()
            self._auto_unwinding = False
            self._auto_winding = False
            self._auto_paused = False
            self._last_update_time = None
            self._session = None
            self._edit_mode = False
            self._edit_target = None
            self._edit_navigating = False
            self._edit_adjusting = False
            self._session_generation = None
            self._saved = False
            self._water_reverse_started = False

    @_mode_serialized
    def complete(self) -> CalibrationSession:
        self._ensure_not_homing()
        session = self.get_current()
        if self._edit_mode:
            raise RuntimeError("Use Save Calibration in edit mode")

        self._sync_position()
        if session.player.running or session.player.brush_running:
            raise RuntimeError("Stop roller and brushes before completing calibration")
        session.validate()
        self._last_update_time = None

        return session

    def complete_motion_fault_recovery(self) -> None:
        if self.active or self.auto_mode is not None:
            raise RuntimeError("CALIBRATION still active")
        self._motion_fault = None

    def external_motion_fault(self, reason: str) -> None:
        """Abort calibration without a second drive command or position update."""
        self._motion_fault = reason
        if self._session is not None:
            self._session.player.external_motion_fault()
        if abs(session.position_turns) > 0.01 or (self._edit_mode and self._edit_moved and not self._edit_return_confirmed):
            raise RuntimeError("Return to Point0 and confirm sensor before finishing")
        self._session = None
        self._edit_mode = False
        self._edit_target = None
        self._edit_navigating = False
        self._edit_adjusting = False
        self._session_generation = None
        self._return_to_zero = False
        self._geometry_saved = False
        self._auto_unwinding = False
        self._auto_winding = False
        self._auto_paused = False
        self._saved = False
        self._last_update_time = None

    @_mode_serialized
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
        if self._edit_navigating and self._edit_wait_until is not None:
            if self.clock.now() >= self._edit_wait_until:
                self._edit_wait_until = None
                self._edit_start_leg()
            return
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
        if self._return_to_zero:
            if self.sensor_service is None:
                raise RuntimeError("Point0 sensor is unavailable")
            state = self.sensor_service.get_state()
            if not state.connected:
                raise RuntimeError("Point0 sensor disconnected during return")
            # Ignore intermediate revolutions. Arm only near calculated zero.
            if session.position_turns <= 0.5:
                if not self._return_slow:
                    session.player.pause()
                    session.player.start_jog_reverse(5.0)
                    self._return_slow = True
                    self._return_sensor_sequence = state.sequence
                    self._last_update_time = now
                    return
                if state.sequence != self._return_sensor_sequence:
                    session.player.stop()
                    session.position_tracker.set_position(0.0)
                    if self._edit_mode:
                        self._edit_return_confirmed = True
                    self._return_to_zero = False
                    self._auto_paused = False
                    self._last_update_time = None
                    return
            if session.position_turns <= -0.25:
                session.player.stop()
                self._return_to_zero = False
                self._auto_paused = False
                self._last_update_time = None
                raise RuntimeError("Point0 not detected near calculated zero")
        lower, upper = self._motion_limits()
        target = (session.store.get(self._edit_route[0]) if self._edit_navigating and self._edit_route else (upper if direction == "forward" else lower))
        if self._return_to_zero and not self._return_slow:
            target = 0.5
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
            if self._return_to_zero and not self._return_slow:
                state = self.sensor_service.get_state()
                if not state.connected:
                    self._return_to_zero = False
                    raise RuntimeError("Point0 sensor disconnected during return")
                self._return_sensor_sequence = state.sequence
                self._return_slow = True
                session.player.start_jog_reverse(5.0)
                self._last_update_time = now
                return
            if self._edit_navigating:
                if session.player.brush_running:
                    session.player.stop_brush()
                self._edit_route.pop(0)
                self._last_update_time = None
                if self._edit_route:
                    self._edit_wait_until = now + 2.0
                else:
                    self._edit_navigating = False
                return
            if session.player.brush_running and session.stage in (
                CalibrationStage.WATER_START,
                CalibrationStage.WASHING_STOP,
                CalibrationStage.READY_TO_UNWIND,
            ):
                session.player.stop_brush()
            if self._auto_unwinding:
                session.stage = CalibrationStage.WASHING_STOP
            if self._auto_winding:
                session.stage = CalibrationStage.REWIND_COMPLETE
            if self._return_to_zero:
                self._return_to_zero = False
                raise RuntimeError("Point0 not confirmed before return travel limit")
            self._auto_unwinding = False
            self._auto_winding = False
            self._auto_paused = False
            self._last_update_time = None
            return
        session.player.update(elapsed)
        self._last_update_time = now

    @_mode_serialized
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

    @_mode_serialized
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

    @_mode_serialized
    def start_return_to_zero(self) -> None:
        self._ensure_not_homing()
        session = self.get_current()
        self._sync_position()
        if not self._edit_mode and (not self._saved or not self._geometry_saved or session.stage != CalibrationStage.REWIND_COMPLETE):
            raise RuntimeError("Save calibration and geometry before returning to Point0")
        if self.auto_mode is not None or session.player.running or session.player.brush_running:
            raise RuntimeError("Stop drives before return to Point0")
        if self._edit_mode:
            self._edit_navigating = False
            self._edit_route = []
            self._edit_wait_until = None
            self._edit_adjusting = False
        if self.sensor_service is None or not self.sensor_service.get_state().connected:
            raise RuntimeError("Point0 sensor must be connected")
        if session.position_turns <= 0.0:
            raise RuntimeError("Already at calculated Point0; verify sensor manually")
        self._return_to_zero = True
        self._return_slow = False
        self._return_sensor_sequence = self.sensor_service.get_state().sequence
        try:
            session.player.start_jog_reverse(50.0 if session.position_turns > 0.5 else 5.0)
            if session.position_turns <= 0.5:
                self._return_slow = True
        except Exception:
            self._return_to_zero = False
            raise
        self._last_update_time = self.clock.now()

    @_mode_serialized
    def resume_auto(self, brush_frequency_hz: float) -> None:
        if not self._auto_paused:
            raise RuntimeError("No paused automatic movement")
        session = self.get_current()
        if session.stage == CalibrationStage.READY_TO_UNWIND:
            self._auto_paused = False
            self.next_step(50.0, brush_frequency_hz)
        elif self._saved and session.stage == CalibrationStage.WASHING_STOP:
            self._auto_paused = False
            self.start_auto_wind()
        else:
            raise RuntimeError("No automatic movement to resume")

    def mark_geometry_saved(self) -> None:
        self.require_geometry_ready()
        self._geometry_saved = True

    @_mode_serialized
    def finish_saved_session(self) -> None:
        session = self.get_current()
        self._sync_position()
        if not self._saved or not self._geometry_saved:
            raise RuntimeError("Save calibration and material geometry before finishing")
        if self.auto_mode is not None or session.player.running or session.player.brush_running:
            raise RuntimeError("Stop roller and brushes before finishing")
        if self.machine.roller_owner not in (None, "calibration"):
            raise RuntimeError("Roller is owned by another operation")
        # Do not issue movement or release machine mode here.
        self.finish()

    @_mode_serialized
    def finish(self) -> None:
        session = self.get_current()

        if session.player.running or session.player.brush_running or self.auto_mode is not None:
            raise RuntimeError("Cannot finish calibration while drives or automatic motion are active")

        self._session = None
        self._edit_mode = False
        self._edit_target = None
        self._edit_navigating = False
        self._edit_adjusting = False
        self._session_generation = None
        self._return_to_zero = False
        self._geometry_saved = False
        self._auto_unwinding = False
        self._auto_winding = False
        self._auto_paused = False
        self._saved = False
        self._last_update_time = None

    @_mode_serialized
    def start_brush(self, frequency_hz: float) -> None:
        self._ensure_not_homing()
        session = self.get_current()
        if self._edit_mode or self._saved or session.stage in (
            CalibrationStage.WATER_START,
            CalibrationStage.READY_TO_UNWIND,
        ):
            raise RuntimeError(
                "Brushes are controlled by Next during reverse calibration"
            )
        session.player.start_brush(frequency_hz)

    @_mode_serialized
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
