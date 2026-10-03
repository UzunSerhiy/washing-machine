from app.services.machine.calibration.machine import MachineCalibration
from app.services.machine.calibration.player import CalibrationPlayer
from app.services.machine.calibration.points import CalibrationPoint
from app.services.machine.calibration.position import RollerPositionTracker
from app.services.machine.calibration.store import CalibrationPointStore
from app.services.machine.calibration.winding import WindingCalibration
from app.services.machine.machine import Machine
from app.services.winding.rotation import RollerRotationCalculator


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
        self.player = CalibrationPlayer(
            machine=machine,
            position_tracker=self.position_tracker,
            rotation_calculator=rotation_calculator,
            calibration_store=self.store,
        )

    @property
    def position_turns(self) -> float:
        return self.position_tracker.position_turns

    def set_point(self, point: CalibrationPoint) -> None:
        turns = self.position_turns

        if point in (
            CalibrationPoint.MATERIAL_START,
            CalibrationPoint.WASHING_STOP,
        ):
            self.machine_calibration.set_point(
                point,
                turns,
            )
            return
        if point == CalibrationPoint.MATERIAL_END:
            self.winding_calibration.set_point(
                point,
                turns,
            )
            return

        raise ValueError("Unsupported calibration point")

    def is_complete(self) -> bool:
        return (
            self.machine_calibration.is_complete()
            and self.winding_calibration.is_complete()
        )

    def validate(self) -> None:
        self.machine_calibration.validate()
        self.winding_calibration.validate()
