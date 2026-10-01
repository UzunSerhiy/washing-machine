from app.services.machine.operation import AutoStage, OperationMode
from app.services.machine.state import MachineOperationState
from app.services.speed.layer import SpeedLayer


class MachineOperationService:
    def __init__(self, speed_layer: SpeedLayer | None = None):
        self.state = MachineOperationState()
        self.speed_layer = speed_layer or SpeedLayer()

    def get_manual_roller_frequency(self) -> float:
        return self.speed_layer.belt_frequency(self.state.roller_speed_percent)

    def get_manual_brush_frequency(self) -> float:
        return self.speed_layer.brush_frequency(self.state.brush_speed_percent)

    def set_manual_mode(self) -> None:
        self.state.mode = OperationMode.MANUAL
        self.state.auto_stage = None
        self.state.material_profile_id = None
        self.state.running = False
        self.state.paused = False

    def set_auto_mode(self, material_profile_id: int) -> None:
        if material_profile_id <= 0:
            raise ValueError("Material profile ID must be greater than zero")

        self.state.mode = OperationMode.AUTO
        self.state.auto_stage = AutoStage.WINDING
        self.state.material_profile_id = material_profile_id
        self.state.running = False
        self.state.paused = False

    def set_calibration_mode(self, material_profile_id: int) -> None:
        if material_profile_id <= 0:
            raise ValueError("Material profile ID must be greater than zero")

        self.state.mode = OperationMode.CALIBRATION
        self.state.auto_stage = None
        self.state.material_profile_id = material_profile_id
        self.state.running = False
        self.state.paused = False

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
        self._validate_speed_percent(speed_percent)
        self.state.roller_speed_percent = speed_percent

    def set_manual_brush_speed(self, speed_percent: float) -> None:
        self._validate_speed_percent(speed_percent)
        self.state.brush_speed_percent = speed_percent

    @staticmethod
    def _validate_speed_percent(speed_percent: float) -> None:
        if not 0 < speed_percent <= 100:
            raise ValueError(
                "Speed percent must be greater than 0 and no more than 100"
            )
