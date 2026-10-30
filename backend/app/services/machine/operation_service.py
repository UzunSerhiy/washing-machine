from functools import wraps
from threading import RLock

from app.services.machine.operation import AutoStage, OperationMode
from app.services.machine.state import MachineOperationState
from app.services.speed.layer import SpeedLayer
from app.services.machine.machine import Machine


def _mode_serialized(method):
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        with self._mode_lock:
            return method(self, *args, **kwargs)
    return wrapper


class MachineOperationService:
    def __init__(self, machine: Machine, speed_layer: SpeedLayer | None = None):
        self._mode_lock = RLock()
        self._mode_revision = 0
        self.machine = machine
        self.state = MachineOperationState()
        self.speed_layer = speed_layer or SpeedLayer()
        self.roller_homing_service = None
        self.manual_session_active = False

    @_mode_serialized
    def select_idle_mode(self, mode: OperationMode) -> None:
        """Select a tab without issuing any motor command."""
        if self.machine.roller_owner is not None:
            raise RuntimeError('Roller is reserved by Point0/HOME; finish STOP first')
        if self.manual_session_active or self.state.running or self.state.paused or self.state.roller_running or self.state.brush_running:
            raise RuntimeError("Finish the current session and stop all drives first")
        if self.roller_homing_service is not None and (self.roller_homing_service.searching or self.roller_homing_service.faulted):
            raise RuntimeError("HOME is active or requires fault acknowledgement")
        if mode != self.state.mode:
            self._mode_revision += 1
            self.state.mode = mode
            self.state.auto_stage = None
            self.state.material_profile_id = None

    @_mode_serialized
    def begin_manual_session(self) -> None:
        if self.state.mode != OperationMode.MANUAL:
            raise RuntimeError("Select MANUAL first")
        if self.manual_session_active:
            raise RuntimeError("MANUAL session is already active")
        if self.state.running or self.state.paused or self.state.roller_running or self.state.brush_running:
            raise RuntimeError("Machine must be stopped")
        self.manual_session_active = True

    @_mode_serialized
    def end_manual_session(self) -> None:
        if not self.manual_session_active:
            raise RuntimeError("MANUAL session is not active")
        if self.state.running or self.state.paused or self.state.roller_running or self.state.brush_running:
            raise RuntimeError("Stop all drives before ending MANUAL session")
        if self.roller_homing_service is not None and (self.roller_homing_service.searching or self.roller_homing_service.faulted):
            raise RuntimeError("HOME must finish and any fault must be acknowledged")
        self.manual_session_active = False

    def get_manual_roller_frequency(self) -> float:
        speed_percent = self.state.roller_speed_percent

        if speed_percent is None:
            raise RuntimeError("Manual roller speed is not configured")

        return self.speed_layer.belt_frequency(speed_percent)

    def get_manual_brush_frequency(self) -> float:
        speed_percent = self.state.brush_speed_percent

        if speed_percent is None:
            raise RuntimeError("Manual brush speed is not configured")

        return self.speed_layer.brush_frequency(speed_percent)

    @_mode_serialized
    def set_manual_mode(self) -> None:
        if (
            self.roller_homing_service is not None
            and self.roller_homing_service.searching
        ):
            raise RuntimeError("Cannot change mode while roller homing is active")
        self._stop_for_mode_change()

        self._mode_revision += 1
        self.state.mode = OperationMode.MANUAL
        self.state.auto_stage = None
        self.state.material_profile_id = None

    @_mode_serialized
    def set_auto_mode(self, material_profile_id: int) -> None:
        if (
            self.roller_homing_service is not None
            and self.roller_homing_service.searching
        ):
            raise RuntimeError("Cannot change mode while roller homing is active")

        if material_profile_id <= 0:
            raise ValueError("Material profile ID must be greater than zero")

        self._stop_for_mode_change()

        self._mode_revision += 1
        self.state.mode = OperationMode.AUTO
        self.state.auto_stage = AutoStage.WINDING
        self.state.material_profile_id = material_profile_id

    @_mode_serialized
    def set_calibration_mode(self, material_profile_id: int) -> None:
        if (
            self.roller_homing_service is not None
            and self.roller_homing_service.searching
        ):
            raise RuntimeError("Cannot change mode while roller homing is active")

        if material_profile_id <= 0:
            raise ValueError("Material profile ID must be greater than zero")

        self._stop_for_mode_change()

        self._mode_revision += 1
        self.state.mode = OperationMode.CALIBRATION
        self.state.auto_stage = None
        self.state.material_profile_id = material_profile_id

    @_mode_serialized
    def next_stage(self) -> None:
        if self.state.mode != OperationMode.AUTO:
            raise RuntimeError("Stage navigation is available only in auto mode")

        if self.state.auto_stage is None:
            raise RuntimeError("Auto stage is not selected")

        stages = list(AutoStage)
        current_index = stages.index(self.state.auto_stage)

        if current_index >= len(stages) - 1:
            raise RuntimeError("Already at the last auto stage")

        self.state.auto_stage = stages[current_index + 1]
        self.state.running = False
        self.state.paused = False

    @_mode_serialized
    def previous_stage(self) -> None:
        if self.state.mode != OperationMode.AUTO:
            raise RuntimeError("Stage navigation is available only in auto mode")
        if self.state.auto_stage is None:
            raise RuntimeError("Auto stage is not selected")

        stages = list(AutoStage)
        current_index = stages.index(self.state.auto_stage)

        if current_index <= 0:
            raise RuntimeError("Already at the first auto stage")

        self.state.auto_stage = stages[current_index - 1]
        self.state.running = False
        self.state.paused = False

    @_mode_serialized
    def set_manual_roller_speed(self, speed_percent: float) -> None:
        self._require_manual_mode()
        self._validate_speed_percent(speed_percent)
        self.state.roller_speed_percent = speed_percent

    @_mode_serialized
    def set_manual_brush_speed(self, speed_percent: float) -> None:
        self._require_manual_mode()
        self._validate_speed_percent(speed_percent)
        self.state.brush_speed_percent = speed_percent

    @_mode_serialized
    def start_manual_roller_forward(self) -> None:
        self._require_manual_mode()
        frequency_hz = self.get_manual_roller_frequency()

        # Once a motion command is attempted, position may be unknown.
        if self.roller_homing_service is not None:
            self.roller_homing_service.invalidate()

        self.machine.start_roller_forward(frequency_hz)

        self.state.roller_running = True

    @_mode_serialized
    def start_manual_roller_reverse(self) -> None:
        self._require_manual_mode()
        frequency_hz = self.get_manual_roller_frequency()

        # Once a motion command is attempted, position may be unknown.
        if self.roller_homing_service is not None:
            self.roller_homing_service.invalidate()

        self.machine.start_roller_reverse(frequency_hz)

        self.state.roller_running = True

    @_mode_serialized
    def stop_manual_roller(self) -> None:
        self._require_manual_mode()

        self.machine.stop_roller()

        self.state.roller_running = False

    @_mode_serialized
    def start_manual_brush(self) -> None:
        self._require_manual_mode()

        frequency_hz = self.get_manual_brush_frequency()

        self.machine.start_brush(frequency_hz)

        self.state.brush_running = True

    @_mode_serialized
    def stop_manual_brush(self) -> None:
        self._require_manual_mode()

        self.machine.stop_brush()

        self.state.brush_running = False

    @_mode_serialized
    def start_home(self, service, *, position_confirmed: bool, frequency_hz: float) -> None:
        """Validate mode and start HOME atomically against mode transitions."""
        # Point0 is a service operation, independent of selected UI mode.
        # The API additionally checks AUTO/CALIBRATION session ownership.
        if self.state.running or self.state.paused:
            raise RuntimeError("Stop the active operation before homing")
        if self.state.roller_running or self.state.brush_running:
            raise RuntimeError("Stop manual movement before homing")
        service.start(position_confirmed=position_confirmed, frequency_hz=frequency_hz)

    def set_roller_homing_service(self, service) -> None:
        self.roller_homing_service = service

    def _stop_for_mode_change(self) -> None:
        if getattr(self.machine, 'roller_owner', None) is not None:
            raise RuntimeError('Roller is reserved by Point0/HOME; finish STOP first')
        self.machine.stop_all()

        self.state.roller_running = False
        self.state.brush_running = False
        self.state.running = False
        self.state.paused = False

    def _require_manual_mode(self) -> None:
        if self.state.mode != OperationMode.MANUAL:
            raise RuntimeError("Manual control is available only in manual mode")

    @staticmethod
    def _validate_speed_percent(speed_percent: float) -> None:
        if not 0 < speed_percent <= 100:
            raise ValueError(
                "Speed percent must be greater than 0 and no more than 100"
            )
