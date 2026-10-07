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

        return PreparedAutoStage(
            stage=state.auto_stage,
            material_profile_id=state.material_profile_id,
            mode_speed_percent=settings.mode_speed_percent,
            brush_speed_percent=settings.brush_speed_percent,
            calibration=calibration,
            winding_parameters=winding_parameters,
            machine=machine,
            winding_calculator=winding_calculator,
        )
