from enum import Enum

from app.services.machine.calibration.machine import MachineCalibration
from app.services.machine.calibration.position import RollerPositionTracker
from app.services.machine.calibration.winding import WindingCalibration
from app.services.machine.trajectory.washing import (
    WashingPhase,
    WashingTrajectory,
)
from app.services.winding.calculator import WindingCalculator
from app.services.winding.rotation import RollerRotationCalculator


class WashingAction(str, Enum):
    RUN_REVERSE = "run_reverse"
    STOP = "stop"
    WAIT = "wait"


class WashingController:
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

        self.trajectory = WashingTrajectory(
            machine_calibration=machine_calibration,
            winding_calibration=winding_calibration,
        )

        self._completed = False
        self._stop_applied = False

    @property
    def phase(self) -> WashingPhase:
        return self.trajectory.phase_at(self.position_tracker.position_turns)

    @property
    def position_turns(self) -> float:
        return self.position_tracker.position_turns

    @property
    def completed(self) -> bool:
        return self._completed

    @property
    def action(self) -> WashingAction:
        if self._stop_applied:
            return WashingAction.WAIT

        if self._completed:
            return WashingAction.STOP

        if self.phase in (
            WashingPhase.MATERIAL,
            WashingPhase.BELTS,
        ):
            return WashingAction.RUN_REVERSE

        return WashingAction.STOP

    def apply(
        self,
        material_speed_percent: float,
        belt_frequency_hz: float,
        brush_frequency_hz: float,
    ) -> None:
        if not 0 < material_speed_percent <= 100:
            raise ValueError(
                "Material speed percent must be greater than 0 and no more than 100"
            )

        if self.action == WashingAction.RUN_REVERSE:
            if self.phase == WashingPhase.MATERIAL:
                self._update_winding_calculator()

                frequency_hz = self.winding_calculator.frequency_hz(
                    speed_percent=material_speed_percent
                )

                self.machine.start_roller_reverse(frequency_hz)
                self.machine.start_brush(brush_frequency_hz)
                return

            if self.phase == WashingPhase.BELTS:
                self.machine.start_roller_reverse(belt_frequency_hz)
                self.machine.start_brush(brush_frequency_hz)
                return

        if self.action == WashingAction.STOP:
            self.machine.stop_all()
            self._stop_applied = True
            return

    def update(
        self,
        material_speed_percent: float,
        belt_frequency_hz: float,
        brush_frequency_hz: float,
        elapsed_seconds: float,
    ) -> None:
        if elapsed_seconds < 0:
            raise ValueError("Elapsed seconds cannot be negative")

        if not 0 < material_speed_percent <= 100:
            raise ValueError(
                "Material speed percent must be greater than 0 and no more than 100"
            )

        if self._completed:
            return

        if self.phase == WashingPhase.MATERIAL:
            self._update_winding_calculator()

            frequency_hz = self.winding_calculator.frequency_hz(
                speed_percent=material_speed_percent,
            )

        elif self.phase == WashingPhase.BELTS:
            frequency_hz = belt_frequency_hz

        else:
            self._completed = True
            return

        revolutions = self.rotation_calculator.revolutions_for_time(
            frequency_hz,
            elapsed_seconds,
        )

        washing_stop = self.machine_calibration.washing_stop_turns

        if washing_stop is None:
            raise RuntimeError("Machine calibration is incomplete")

        max_revolutions = max(
            0.0,
            self.position_tracker.position_turns - washing_stop,
        )

        revolutions = min(revolutions, max_revolutions)

        self.position_tracker.move_reverse(revolutions)

        if self.position_turns <= washing_stop:
            self.position_tracker.set_position(washing_stop)
            self._completed = True

    def _update_winding_calculator(self) -> None:
        material_end = self.winding_calibration.material_end_turns

        if material_end is None:
            raise RuntimeError("Winding calibration is incomplete")

        material_turns = material_end - self.position_tracker.position_turns

        if material_turns < 0:
            material_turns = 0.0

        self.winding_calculator.set_turns(material_turns)

    def reset(self) -> None:
        self.position_tracker.reset()
        self._completed = False
        self._stop_applied = False
