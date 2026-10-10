from dataclasses import dataclass
from typing import Any

from app.services.machine.operation import AutoStage, OperationMode
from app.services.machine.operation_service import MachineOperationService
from app.services.speed.auto_settings import AutoSpeedSettingsService
from app.services.machine.calibration.data import CalibrationData
from app.services.machine.calibration.repository import CalibrationRepository
from app.models.winding_parameters import WindingParameters
from app.services.winding.repository import WindingParametersRepository
from app.models.machine import Machine as MachineModel
from app.services.machine.repository import MachineRepository
from app.services.winding.calculator import WindingCalculator
from app.services.winding.factory import WindingCalculatorFactory

from app.core.config import settings as app_settings
from app.services.machine.calibration.machine import MachineCalibration
from app.services.machine.calibration.position import RollerPositionTracker
from app.services.machine.calibration.winding import WindingCalibration
from app.services.machine.controller.winding import WindingController
from app.services.winding.rotation import RollerRotationCalculator
from app.services.speed.layer import SpeedLayer


@dataclass(frozen=True)
class PreparedAutoStage:
    stage: AutoStage
    material_profile_id: int
    mode_speed_percent: float
    brush_speed_percent: float | None
    calibration: CalibrationData
    winding_parameters: WindingParameters
    machine: MachineModel
    winding_calculator: WindingCalculator
    controller: WindingController


class AutoSessionService:
    def __init__(
        self,
        machine_id: int,
        operation_service: MachineOperationService,
        speed_settings_service: AutoSpeedSettingsService,
        calibration_repository: CalibrationRepository | None = None,
        winding_parameters_repository: WindingParametersRepository | None = None,
        machine_repository: MachineRepository | None = None,
    ):
        self.machine_id = machine_id
        self.operation_service = operation_service
        self.speed_settings_service = speed_settings_service

        self.calibration_repository = calibration_repository or CalibrationRepository()

        self.winding_parameters_repository = (
            winding_parameters_repository or WindingParametersRepository()
        )
        self.machine_repository = machine_repository or MachineRepository()

        self.speed_layer = SpeedLayer()
        self._prepared: PreparedAutoStage | None = None
        self._faulted = False

    async def prepare(
        self,
        session: Any,
    ) -> PreparedAutoStage:
        state = self.operation_service.state

        if state.mode != OperationMode.AUTO:
            raise RuntimeError("Machine is not in auto mode")

        if state.auto_stage is None:
            raise RuntimeError("Auto stage is not selected")

        if state.material_profile_id is None:
            raise RuntimeError("Material profile is not selected")

        calibration = await self.calibration_repository.load(
            db=session,
            machine_id=self.machine_id,
            material_profile_id=state.material_profile_id,
        )

        winding_parameters = await self.winding_parameters_repository.load(
            session=session,
            material_profile_id=state.material_profile_id,
        )

        settings = await self.speed_settings_service.load(
            session=session,
            machine_id=self.machine_id,
            stage=state.auto_stage,
        )

        machine = await self.machine_repository.load(
            session=session,
            machine_id=self.machine_id,
        )

        winding_calculator = WindingCalculatorFactory.create(
            machine=machine, parameters=winding_parameters
        )

        machine_calibration = MachineCalibration()
        machine_calibration.set_washing_stop(calibration.washing_stop_turns)
        machine_calibration.set_material_start(calibration.material_start_turns)

        winding_calibration = WindingCalibration()
        winding_calibration.set_material_end(calibration.material_end_turns)

        position_tracker = RollerPositionTracker()

        rotation_calculator = RollerRotationCalculator(
            motor_rpm_at_50hz=app_settings.ROLLER_MOTOR_RPM_AT_50HZ,
            gear_ratio=app_settings.ROLLER_GEAR_RATIO,
        )

        if state.auto_stage != AutoStage.WINDING:
            raise NotImplementedError(
                f"Auto stage {state.auto_stage.value} is not implemented yet"
            )

        controller = WindingController(
            machine=self.operation_service.machine,
            machine_calibration=machine_calibration,
            winding_calibration=winding_calibration,
            position_tracker=position_tracker,
            rotation_calculator=rotation_calculator,
            winding_calculator=winding_calculator,
        )

        prepared = PreparedAutoStage(
            stage=state.auto_stage,
            material_profile_id=state.material_profile_id,
            mode_speed_percent=settings.mode_speed_percent,
            brush_speed_percent=settings.brush_speed_percent,
            calibration=calibration,
            winding_parameters=winding_parameters,
            machine=machine,
            winding_calculator=winding_calculator,
            controller=controller,
        )

        self._prepared = prepared

        return prepared

    def start(self) -> None:
        if self._faulted:
            raise RuntimeError("Cannot start AUTO: controller is in fault state")

        if self._prepared is None:
            raise RuntimeError("Auto stage is not prepared")

        prepared = self._prepared

        belt_frequency_hz = self.speed_layer.belt_frequency(prepared.mode_speed_percent)

        state = self.operation_service.state

        try:
            prepared.controller.apply(
                belt_frequency_hz=belt_frequency_hz,
                speed_percent=prepared.mode_speed_percent,
            )
        except Exception:
            self._faulted = True
            state.running = False
            state.paused = False
            raise

        state.running = True
        state.paused = False

    def tick(self, elapsed_seconds: float = 0.1) -> None:
        if elapsed_seconds < 0:
            raise ValueError("Elapsed_seconds cannot be negative")

        if self._prepared is None:
            return

        state = self.operation_service.state

        if not state.running or state.paused:
            return

        prepared = self._prepared

        try:
            belt_frequency_hz = self.speed_layer.belt_frequency(
                prepared.mode_speed_percent
            )

            prepared.controller.update(
                belt_frequency_hz=belt_frequency_hz,
                speed_percent=prepared.mode_speed_percent,
                elapsed_seconds=elapsed_seconds,
            )

            prepared.controller.apply(
                belt_frequency_hz=belt_frequency_hz,
                speed_percent=prepared.mode_speed_percent,
            )

        except Exception:
            self._faulted = True
            state.running = False
            state.paused = False
            raise

        if prepared.controller.completed:
            state.running = False
            state.paused = False

    def pause(self) -> None:
        if self._prepared is None:
            raise RuntimeError("Auto stage is not prepared")

        state = self.operation_service.state

        if not state.running or state.paused:
            return

        try:
            self._prepared.controller.machine.stop_roller()

        except Exception:
            self._faulted = True
            state.running = False
            state.paused = False
            raise

        state.running = False
        state.paused = True

    def resume(self) -> None:
        if self._faulted:
            raise RuntimeError("Cannot resume AUTO: controller is in fault state")

        if self._prepared is None:
            raise RuntimeError("Auto stage is not prepared")

        state = self.operation_service.state

        if not state.paused:
            raise RuntimeError("Auto stage is not paused")

        prepared = self._prepared

        if prepared.controller.completed:
            raise RuntimeError("Auto stage is already completed")

        belt_frequency_hz = self.speed_layer.belt_frequency(prepared.mode_speed_percent)

        try:
            prepared.controller.apply(
                belt_frequency_hz=belt_frequency_hz,
                speed_percent=prepared.mode_speed_percent,
            )
        except Exception:
            self._faulted = True
            state.running = False
            state.paused = False
            raise

        state.running = True
        state.paused = False

    def stop(self) -> None:
        state = self.operation_service.state

        try:
            if self._prepared is not None:
                self._prepared.controller.machine.stop_roller()

        except Exception:
            self._faulted = True
            raise

        finally:
            state.running = False
            state.paused = False
            self._prepared = None
