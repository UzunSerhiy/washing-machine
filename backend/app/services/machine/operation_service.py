from app.services.machine.operation import AutoStage, OperationMode
from app.services.machine.state import MachineOperationState
from app.services.speed.layer import SpeedLayer
from app.services.machine.machine import Machine


class MachineOperationService:
    def __init__(self, machine: Machine, speed_layer: SpeedLayer | None = None):
        self.machine = machine
        self.state = MachineOperationState()
        self.speed_layer = speed_layer or SpeedLayer()

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

    def set_manual_mode(self) -> None:
        self._stop_for_mode_change()

        self.state.mode = OperationMode.MANUAL
        self.state.auto_stage = None
        self.state.material_profile_id = None

    def set_auto_mode(self, material_profile_id: int) -> None:
        if material_profile_id <= 0:
            raise ValueError("Material profile ID must be greater than zero")

        self._stop_for_mode_change()

        self.state.mode = OperationMode.AUTO
        self.state.auto_stage = AutoStage.WINDING
        self.state.material_profile_id = material_profile_id

    def set_calibration_mode(self, material_profile_id: int) -> None:
        if material_profile_id <= 0:
            raise ValueError("Material profile ID must be greater than zero")

        self._stop_for_mode_change()

        self.state.mode = OperationMode.CALIBRATION
        self.state.auto_stage = None
        self.state.material_profile_id = material_profile_id

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

    def set_manual_roller_speed(self, speed_percent: float) -> None:
        self._require_manual_mode()
        self._validate_speed_percent(speed_percent)
        self.state.roller_speed_percent = speed_percent

    def set_manual_brush_speed(self, speed_percent: float) -> None:
        self._require_manual_mode()
        self._validate_speed_percent(speed_percent)
        self.state.brush_speed_percent = speed_percent

    def start_manual_roller_forward(self) -> None:
        self._require_manual_mode()

        frequency_hz = self.get_manual_roller_frequency()

        self.machine.start_roller_forward(frequency_hz)

        self.state.roller_running = True

    def start_manual_roller_reverse(self) -> None:
        self._require_manual_mode()

        frequency_hz = self.get_manual_roller_frequency()

        self.machine.start_roller_reverse(frequency_hz)

        self.state.roller_running = True

    def stop_manual_roller(self) -> None:
        self._require_manual_mode()

        self.machine.stop_roller()

        self.state.roller_running = False

    def start_manual_brush(self) -> None:
        self._require_manual_mode()

        frequency_hz = self.get_manual_brush_frequency()

        self.machine.start_brush(frequency_hz)

        self.state.brush_running = True

    def stop_manual_brush(self) -> None:
        self._require_manual_mode()

        self.machine.stop_brush()

        self.state.brush_running = False

    def _stop_for_mode_change(self) -> None:
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
