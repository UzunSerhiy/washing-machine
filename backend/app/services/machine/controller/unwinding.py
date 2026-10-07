from enum import Enum

from app.services.machine.calibration.machine import MachineCalibration
from app.services.machine.calibration.position import RollerPositionTracker
from app.services.machine.calibration.winding import WindingCalibration
from app.services.machine.trajectory.unwinding import (
    UnwindingPhase,
    UnwindingTrajectory,
)
from app.services.winding.calculator import WindingCalculator
from app.services.winding.rotation import RollerRotationCalculator


class UnwindingAction(str, Enum):
    RUN_REVERSE = "run_reverse"
    STOP = "stop"
    WAIT = "wait"


class UnwindingController:
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

        self.trajectory = UnwindingTrajectory(
            machine_calibration=machine_calibration,
            winding_calibration=winding_calibration,
        )

        self._completed = False
        self._stop_applied = False

    @property
    def phase(self) -> UnwindingPhase:
        return self.trajectory.phase_at(self.position_tracker.position_turns)

    @property
    def position_turns(self) -> float:
        return self.position_tracker.position_turns

    @property
    def completed(self) -> bool:
        return self._completed

    @property
    def action(self) -> UnwindingAction:
        if self._stop_applied:
            return UnwindingAction.WAIT

        if self._completed:
            return UnwindingAction.STOP

        if self.phase in (
            UnwindingPhase.MATERIAL,
            UnwindingPhase.BELTS,
        ):
            return UnwindingAction.RUN_REVERSE

        return UnwindingAction.STOP

    def apply(
        self,
        material_speed_percent: float,
        belt_frequency_hz: float,
    ) -> None:
        self._validate_speed_percent(material_speed_percent)
        self._validate_frequency(belt_frequency_hz)

        if self.action == UnwindingAction.RUN_REVERSE:
            if self.phase == UnwindingPhase.MATERIAL:
                self._update_winding_calculator()

                frequency_hz = self.winding_calculator.frequency_hz(
                    material_speed_percent
                )

                self.machine.start_roller_reverse(frequency_hz)
                return

            if self.phase == UnwindingPhase.BELTS:
                self.machine.start_roller_reverse(belt_frequency_hz)
                return

        if self.action == UnwindingAction.STOP:
            self.machine.stop_roller()
            self._stop_applied = True

    def update(
        self,
        material_speed_percent: float,
        belt_frequency_hz: float,
        elapsed_seconds: float,
    ) -> None:
        self._validate_speed_percent(material_speed_percent)
        self._validate_frequency(belt_frequency_hz)

        if elapsed_seconds < 0:
            raise ValueError("Elapsed seconds cannot be negative")

        if self._completed:
            return

        self.machine_calibration.validate()
        self.winding_calibration.validate()

        phase = self.phase

        if phase == UnwindingPhase.MATERIAL:
            self._update_winding_calculator()

            frequency_hz = self.winding_calculator.frequency_hz(material_speed_percent)

        elif phase == UnwindingPhase.BELTS:
            frequency_hz = belt_frequency_hz

        else:
            self._completed = True
            return

        revolutions = self.rotation_calculator.revolutions_for_time(
            frequency_hz,
            elapsed_seconds,
        )

        revolutions = min(
            revolutions,
            self.position_tracker.position_turns,
        )

        self.position_tracker.move_reverse(revolutions)

        if self.position_turns <= 0:
            self.position_tracker.set_position(0.0)
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
