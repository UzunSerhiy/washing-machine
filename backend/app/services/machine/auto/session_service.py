from dataclasses import dataclass

from app.services.machine.auto.position_loop import AutoPositionLoop
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
        safety_service=None,
        drive_diagnostics_service=None,
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
        self.safety_service = safety_service
        self.drive_diagnostics_service = drive_diagnostics_service
        self._prepared: PreparedAutoStage | None = None
        self._session_generation: int | None = None
        self._faulted = False
        self.roller_homing_service = None
        # Reserved for the future position-driven AUTO path. Legacy tick remains active.
        self._position_loop: AutoPositionLoop | None = None

    def set_roller_homing_service(self, service) -> None:
        self.roller_homing_service = service

    def bind_position_loop(self, loop: AutoPositionLoop) -> None:
        """Register a referenced loop while idle; do not activate it yet."""
        if self._prepared is not None or self.operation_service.state.running or self.operation_service.state.paused:
            raise RuntimeError("Cannot bind AUTO position loop during a session")
        if self._faulted:
            raise RuntimeError("Cannot bind AUTO position loop in fault state")
        if not loop.position.snapshot.valid:
            raise RuntimeError("Position must be HOME referenced")
        self._position_loop = loop

    @property
    def position_loop(self) -> AutoPositionLoop | None:
        return self._position_loop

    async def prepare(
        self,
        session: Any,
    ) -> PreparedAutoStage:
        if self._faulted:
            raise RuntimeError("Cannot prepare AUTO: controller is in fault state")

        if self._prepared is not None:
            raise RuntimeError(
                "AUTO session already exists; stop it before preparing again"
            )

        state = self.operation_service.state

        if state.mode != OperationMode.AUTO:
            raise RuntimeError("Machine is not in auto mode")

        if state.auto_stage is None:
            raise RuntimeError("Auto stage is not selected")

        if state.material_profile_id is None:
            raise RuntimeError("Material profile is not selected")

        motion_machine = self.operation_service.machine
        generation = motion_machine.capture_session_generation()

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

        if calibration.water_start_turns is None:
            raise RuntimeError("Water Start is not calibrated")

        machine_calibration.set_water_start(calibration.water_start_turns)

        machine_calibration.validate()

        winding_calibration = WindingCalibration()

        winding_calibration.set_material_end(calibration.material_end_turns)

        winding_calibration.validate()

        if self.roller_homing_service is None:
            raise RuntimeError("Roller homing service is not configured")

        self.roller_homing_service.require_zero()

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

        motion_machine.require_session_generation(generation)
        if self._faulted or self._prepared is not None:
            raise RuntimeError("AUTO preparation was invalidated")
        prepared.controller.session_generation = generation
        self._session_generation = generation
        self._prepared = prepared

        return prepared

    def _require_session_generation(self) -> None:
        generation = self._session_generation
        if generation is None or self._prepared is None:
            raise RuntimeError("AUTO session generation is not initialized")
        self.operation_service.machine.require_session_generation(generation)

    def start(self) -> None:
        if self._faulted:
            raise RuntimeError("Cannot start AUTO: controller is in fault state")

        self.require_current_mode()
        self._require_session_generation()

        state = self.operation_service.state

        if state.running:
            raise RuntimeError("AUTO session is already running")

        if state.paused:
            raise RuntimeError("AUTO session is paused; use resume()")

        prepared = self._prepared

        if prepared.controller.completed:
            raise RuntimeError("AUTO session is already completed")

        if self.roller_homing_service is None:
            raise RuntimeError("Roller homing service is not configured")

        self.roller_homing_service.require_zero()

        belt_frequency_hz = self.speed_layer.belt_frequency(prepared.mode_speed_percent)

        try:
            self._require_session_generation()
            prepared.controller.apply(
                belt_frequency_hz=belt_frequency_hz,
                speed_percent=prepared.mode_speed_percent,
            )
        except Exception:
            self._handle_controller_fault()
            raise

        state.running = True
        state.paused = False

    def tick(self, elapsed_seconds: float = 0.1) -> None:
        if elapsed_seconds < 0:
            raise ValueError("Elapsed_seconds cannot be negative")

        if self._prepared is None or self._faulted:
            return

        try:
            self.require_current_mode()
        except Exception:
            self._handle_controller_fault()
            raise

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

            self._require_session_generation()
            prepared.controller.apply(
                belt_frequency_hz=belt_frequency_hz,
                speed_percent=prepared.mode_speed_percent,
            )

        except Exception:
            self._handle_controller_fault()
            raise

        if prepared.controller.completed:
            state.running = False
            state.paused = False

    def pause(self) -> None:
        self.require_current_mode()

        state = self.operation_service.state

        if not state.running or state.paused:
            return

        try:
            self._prepared.controller.machine.stop_roller()

        except Exception:
            self._handle_controller_fault()
            raise

        state.running = False
        state.paused = True

    def resume(self) -> None:
        if self._faulted:
            raise RuntimeError("Cannot resume AUTO: controller is in fault state")

        self.require_current_mode()

        if self._prepared is None:
            raise RuntimeError("Auto stage is not prepared")
        self._require_session_generation()

        state = self.operation_service.state

        if not state.paused:
            raise RuntimeError("Auto stage is not paused")

        prepared = self._prepared

        if prepared.controller.completed:
            raise RuntimeError("Auto stage is already completed")

        belt_frequency_hz = self.speed_layer.belt_frequency(prepared.mode_speed_percent)

        try:
            self._require_session_generation()
            prepared.controller.apply(
                belt_frequency_hz=belt_frequency_hz,
                speed_percent=prepared.mode_speed_percent,
            )
        except Exception:
            self._handle_controller_fault()
            raise

        state.running = True
        state.paused = False

    def stop(self) -> None:
        state = self.operation_service.state

        try:
            if self._prepared is not None:
                self._prepared.controller.machine.stop_roller()
        except Exception:
            self._handle_controller_fault()
            raise
        finally:
            state.running = False
            state.paused = False
            self._prepared = None
            self._session_generation = None
            self._position_loop = None

    def reset_fault(self) -> None:
        if self._prepared is not None:
            raise RuntimeError("Cannot reset fault: AUTO session must be stopped")

        if self.operation_service.state.running:
            raise RuntimeError("Cannot reset fault: machine session is running")

        if self.safety_service is None:
            raise RuntimeError("Cannot reset fault: safety service is not configured")

        self.safety_service.require_safe_state()

        if self.drive_diagnostics_service is None:
            raise RuntimeError(
                "Cannot reset fault: drive diagnostics service is not configured"
            )

        self.drive_diagnostics_service.require_drives_ready()

        raise RuntimeError("Cannot reset fault: recovery checks are incomplete")

    def complete_motion_fault_recovery(self) -> None:
        """Called only by the coordinated recovery transaction."""
        if self._prepared is not None or self.operation_service.state.running or self.operation_service.state.paused:
            raise RuntimeError("AUTO still active")
        self._position_loop = None
        self._faulted = False

    def get_status(self) -> dict:
        state = self.operation_service.state
        if self._faulted:
            status = "FAULT"
        elif self._prepared is None:
            status = "IDLE"
        elif state.running:
            status = "RUNNING"
        elif state.paused:
            status = "PAUSED"
        elif self._prepared.controller.completed:
            status = "COMPLETED"
        else:
            status = "PREPARED"

        return {
            "status": status,
            "stage": (
                self._prepared.stage.value if self._prepared is not None else None
            ),
            "material_profile_id": (
                self._prepared.material_profile_id
                if self._prepared is not None
                else None
            ),
            "speed_percent": (
                self._prepared.mode_speed_percent
                if self._prepared is not None
                else None
            ),
            "running": state.running,
            "paused": state.paused,
            "position_turns": (
                self._prepared.controller.position_turns
                if self._prepared is not None
                else None
            ),
            "phase": (
                self._prepared.controller.phase.value
                if self._prepared is not None
                else None
            ),
            "completed": (
                self._prepared.controller.completed
                if self._prepared is not None
                else False
            ),
        }

    def external_motion_fault(self, reason: str) -> None:
        """Latch a monitored VFD fault without issuing another STOP."""
        self._faulted = True
        if self._position_loop is not None:
            self._position_loop.position.invalidate()
            self._position_loop = None
        state = self.operation_service.state
        state.running = False
        state.paused = False

    def _handle_controller_fault(self) -> None:
        self._faulted = True
        if self._position_loop is not None:
            self._position_loop.position.invalidate()
            self._position_loop = None

        state = self.operation_service.state
        state.running = False
        state.paused = False

        try:
            self.operation_service.machine.stop_all()
        except Exception:
            import logging

            logging.getLogger(__name__).exception(
                "Failed to stop machine after AUTO fault"
            )

    def require_current_mode(self) -> None:
        if self._prepared is None:
            raise RuntimeError("AUTO session is not prepared")

        state = self.operation_service.state

        if state.mode != OperationMode.AUTO:
            raise RuntimeError("Machine is not in AUTO mode")

        if state.auto_stage != self._prepared.stage:
            raise RuntimeError("AUTO stage has changed")

        if state.material_profile_id != self._prepared.material_profile_id:
            raise RuntimeError("Material profile has changed")
