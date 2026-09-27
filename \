from enum import Enum

from app.services.machine.calibration.machine import MachineCalibration
from app.services.machine.calibration.position import RollerPositionTracker
from app.services.machine.calibration.winding import WindingCalibration
from app.services.machine.trajectory.winding import (
    WindingPhase,
    WindingTrajectory,
)
from app.services.winding.calculator import WindingCalculator
from app.services.winding.rotation import RollerRotationCalculator


class WindingAction(str, Enum):
    RUN_FORWARD = "run_forward"
    STOP = "stop"
    WAIT = "wait"


class WindingController:
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

        self.trajectory = WindingTrajectory(
            machine_calibration=machine_calibration,
            winding_calibration=winding_calibration,
        )

        self._completed = False
        self._stop_applied = False

    @property
    def phase(self) -> WindingPhase:
        return self.trajectory.phase_at(self.position_tracker.position_turns)

    @property
    def position_turns(self) -> float:
        return self.position_tracker.position_turns

    @property
    def completed(self) -> bool:
        return self._completed

    @property
    def stop_applied(self) -> bool:
        return self._stop_applied

    @property
    def action(self) -> WindingAction:
        if self._stop_applied:
            return WindingAction.WAIT

        if self._completed:
            return WindingAction.STOP

        if self.phase in (
            WindingPhase.BELTS,
            WindingPhase.MATERIAL,
        ):
            return WindingAction.RUN_FORWARD

        return WindingAction.STOP

    def update(
        self,
        belt_frequency_hz: float,
        speed_percent: float,
        elapsed_seconds: float,
    ) -> None:
        self._validate_frequency(belt_frequency_hz)

        if elapsed_seconds < 0:
            raise ValueError("Elapsed seconds cannot be negative")

        if not 0 < speed_percent <= 100:
            raise ValueError(
                "Speed percent must be greater than 0 and no more than 100"
            )

        if self._completed:
            return

        self.machine_calibration.validate()
        self.winding_calibration.validate()

        material_end = self.winding_calibration.material_end_turns

        if material_end is None:
            raise RuntimeError("Winding calibration is incomplete")

        phase = self.phase

        if phase == WindingPhase.BELTS:
            frequency_hz = belt_frequency_hz

        elif phase == WindingPhase.MATERIAL:
            self._update_winding_calculator()

            frequency_hz = self.winding_calculator.frequency_hz(speed_percent)

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

    def apply(
        self,
        belt_frequency_hz: float,
        speed_percent: float,
    ) -> None:
        self._validate_frequency(belt_frequency_hz)

        if not 0 < speed_percent <= 100:
            raise ValueError(
                "Speed percent must be greater than 0 and no more than 100"
            )

        if self.action == WindingAction.RUN_FORWARD:
            if self.phase == WindingPhase.BELTS:
                self.machine.start_roller_forward(belt_frequency_hz)
                return

            if self.phase == WindingPhase.MATERIAL:
                self._update_winding_calculator()

                frequency_hz = self.winding_calculator.frequency_hz(speed_percent)

                self.machine.start_roller_forward(frequency_hz)
                return

        if self.action == WindingAction.STOP:
            self.machine.stop_roller()
            self._stop_applied = True
            return

    def _update_winding_calculator(self) -> None:
        material_start = self.machine_calibration.material_start_turns

        if material_start is None:
            raise RuntimeError("Machine calibration is incomplete")

        material_turns = self.position_tracker.position_turns - material_start

        if material_turns < 0:
            material_turns = 0.0

        self.winding_calculator.set_turns(material_turns)

    @staticmethod
    def _validate_frequency(frequency_hz: float) -> None:
        if frequency_hz < 0:
            raise ValueError("Frequency cannot be negative")
