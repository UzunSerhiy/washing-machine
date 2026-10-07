from enum import Enum

from app.services.machine.calibration.machine import MachineCalibration
from app.services.machine.calibration.position import RollerPositionTracker
from app.services.machine.calibration.winding import WindingCalibration
from app.services.machine.trajectory.drying import (
    DryingPhase,
    DryingTrajectory,
)
from app.services.winding.calculator import WindingCalculator
from app.services.winding.rotation import RollerRotationCalculator


class DryingAction(str, Enum):
    RUN_FORWARD = "run_forward"
    STOP = "stop"
    WAIT = "wait"


class DryingController:
    def __init__(
        self,
        machine,
        machine_calibration: MachineCalibration,
        winding_calibration: WindingCalibration,
        position_tracker: RollerPositionTracker,
        rotation_calculator: RollerRotationCalculator,
        winding_calculator: WindingCalculator,
    ):
        self.machine = machine
        self.machine_calibration = machine_calibration
        self.winding_calibration = winding_calibration
        self.position_tracker = position_tracker
        self.rotation_calculator = rotation_calculator
        self.winding_calculator = winding_calculator

        self.trajectory = DryingTrajectory(
            machine_calibration=machine_calibration,
            winding_calibration=winding_calibration,
        )

        self._completed = False
        self._stop_applied = False

    @property
    def phase(self) -> DryingPhase:
        return self.trajectory.phase_at(self.position_tracker.position_turns)

    @property
    def position_turns(self) -> float:
        return self.position_tracker.position_turns

    @property
    def completed(self) -> bool:
        return self._completed

    @property
    def action(self) -> DryingAction:
        if self._stop_applied:
            return DryingAction.WAIT

        if self._completed:
            return DryingAction.STOP

        if self.phase in (
            DryingPhase.BELTS,
            DryingPhase.MATERIAL,
        ):
            return DryingAction.RUN_FORWARD

        return DryingAction.STOP

    def apply(
        self,
        material_speed_percent: float,
        belt_frequency_hz: float,
        brush_frequency_hz: float,
    ) -> None:
        self._validate_speed_percent(material_speed_percent)
        self._validate_frequency(belt_frequency_hz)
        self._validate_frequency(brush_frequency_hz)

        if self.action == DryingAction.RUN_FORWARD:
            if self.phase == DryingPhase.BELTS:
                self.machine.start_roller_forward(belt_frequency_hz)
                self.machine.start_brush(brush_frequency_hz)
                return

            if self.phase == DryingPhase.MATERIAL:
                self._update_winding_calculator()

                frequency_hz = self.winding_calculator.frequency_hz(
                    material_speed_percent
                )

                self.machine.start_roller_forward(frequency_hz)
                self.machine.start_brush(brush_frequency_hz)
                return

        if self.action == DryingAction.STOP:
            self.machine.stop_all()
            self._stop_applied = True

    def update(
        self,
        material_speed_percent: float,
        belt_frequency_hz: float,
        brush_frequency_hz: float,
        elapsed_seconds: float,
    ) -> None:
        self._validate_speed_percent(material_speed_percent)
        self._validate_frequency(belt_frequency_hz)
        self._validate_frequency(brush_frequency_hz)

        if elapsed_seconds < 0:
            raise ValueError("Elapsed seconds cannot be negative")

        if self._completed:
            return

        self.machine_calibration.validate()
        self.winding_calibration.validate()

        material_end = self.winding_calibration.material_end_turns

        if material_end is None:
            raise RuntimeError("Winding calibration is incomplete")

        phase = self.phase

        if phase == DryingPhase.BELTS:
            frequency_hz = belt_frequency_hz

        elif phase == DryingPhase.MATERIAL:
            self._update_winding_calculator()

            frequency_hz = self.winding_calculator.frequency_hz(material_speed_percent)

        else:
            self._completed = True
            return

        revolutions = self.rotation_calculator.revolutions_for_time(
            frequency_hz,
            elapsed_seconds,
        )

        remaining_revolutions = material_end - self.position_tracker.position_turns

        revolutions = min(
            revolutions,
            max(0.0, remaining_revolutions),
        )

        self.position_tracker.move_forward(revolutions)

        if self.position_turns >= material_end:
            self.position_tracker.set_position(material_end)
            self._completed = True

    def reset(self) -> None:
        self.position_tracker.reset()
        self._completed = False
        self._stop_applied = False

    def _update_winding_calculator(self) -> None:
        material_start = self.machine_calibration.material_start_turns

        if material_start is None:
            raise RuntimeError("Machine calibration is incomplete")

        material_turns = self.position_tracker.position_turns - material_start

        if material_turns < 0:
            material_turns = 0.0

        self.winding_calculator.set_turns(material_turns)

    @staticmethod
    def _validate_frequency(
        frequency_hz: float,
    ) -> None:
        if frequency_hz < 0:
            raise ValueError("Frequency cannot be negative")

    @staticmethod
    def _validate_speed_percent(
        speed_percent: float,
    ) -> None:
        if not 0 < speed_percent <= 100:
            raise ValueError(
                "Speed percent must be greater than 0 and no more than 100"
            )
