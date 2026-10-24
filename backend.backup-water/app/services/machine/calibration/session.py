from app.services.machine.calibration.machine import MachineCalibration
from app.services.machine.calibration.player import CalibrationPlayer
from app.services.machine.calibration.points import CalibrationPoint
from app.services.machine.calibration.position import RollerPositionTracker
from app.services.machine.calibration.store import CalibrationPointStore
from app.services.machine.calibration.winding import WindingCalibration
from app.services.machine.machine import Machine
from app.services.winding.rotation import RollerRotationCalculator
from app.services.machine.calibration.stage import CalibrationStage


class CalibrationSession:
    def __init__(
        self,
        machine: Machine,
        rotation_calculator: RollerRotationCalculator,
        material_profile_id: int,
    ):
        if material_profile_id <= 0:
            raise ValueError("Material profile ID must be greater than zero")

        self.material_profile_id = material_profile_id
        self.store = CalibrationPointStore()
        self.position_tracker = RollerPositionTracker()
        self.machine_calibration = MachineCalibration(store=self.store)
        self.winding_calibration = WindingCalibration(store=self.store)
        self.stage = CalibrationStage.SET_ZERO
        self.player = CalibrationPlayer(
            machine=machine,
            position_tracker=self.position_tracker,
            rotation_calculator=rotation_calculator,
            calibration_store=self.store,
            stage_getter=lambda: self.stage,
        )

    @property
    def position_turns(self) -> float:
        return self.position_tracker.position_turns

    def set_point(self, point: CalibrationPoint) -> None:
        if self.player.running:
            raise RuntimeError("Stop roller before marking a point")

        turns = self.position_turns

        if self.stage == CalibrationStage.MATERIAL_START:
            if point != CalibrationPoint.MATERIAL_START:
                raise ValueError("Expected material_start point")

            if turns <= 0:
                raise ValueError("Material start must be after zero")

            self.machine_calibration.set_material_start(turns)
            self.stage = CalibrationStage.MATERIAL_END
            return

        if self.stage == CalibrationStage.MATERIAL_END:
            if point != CalibrationPoint.MATERIAL_END:
                raise ValueError("Expected material_end point")

            material_start = self.machine_calibration.material_start_turns

            if material_start is None or turns <= material_start:
                raise ValueError("Material end must be after material start")

            self.winding_calibration.set_material_end(turns)
            self.stage = CalibrationStage.READY_TO_UNWIND
            return

        raise RuntimeError(f"Cannot mark calibration point at stage {self.stage.value}")

    def is_complete(self) -> bool:
        return (
            self.machine_calibration.is_complete()
            and self.winding_calibration.is_complete()
        )

    def validate(self) -> None:
        self.machine_calibration.validate()
        self.winding_calibration.validate()

        washing_stop = self.machine_calibration.washing_stop_turns
        material_start = self.machine_calibration.material_start_turns
        material_end = self.winding_calibration.material_end_turns

        if washing_stop is None or material_start is None or material_end is None:
            raise ValueError("Calibration is incomplete")

        if material_end <= material_start:
            raise ValueError("Material end point must be after material start point")

    def confirm_zero(self) -> None:
        if self.stage != CalibrationStage.SET_ZERO:
            raise RuntimeError("Zero position is already confirmed")

        if self.player.running:
            raise RuntimeError("Stop roller before setting zero")

        if self.player.brush_running:
            raise RuntimeError("Stop brushes before setting zero")

        self.player.reset_position()
        self.stage = CalibrationStage.MATERIAL_START
