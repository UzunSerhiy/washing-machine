from enum import Enum

from app.services.machine.calibration.winding import WindingCalibration
from app.services.machine.calibration.position import RollerPositionTracker
from app.services.machine.trajectory.winding import WindingPhase, WindingTrajectory
from app.services.winding.rotation import RollerRotationCalculator


class WindingAction(str, Enum):
    RUN_FORWARD = "run_forward"
    STOP = "stop"
    WAIT = "wait"


class WindingController:
    def __init__(
        self,
        machine,
        calibration: WindingCalibration,
        position_tracker: RollerPositionTracker,
        rotation_calculator: RollerRotationCalculator,
    ):
        self.machine = machine
        self.calibration = calibration
        self.position_tracker = position_tracker
        self.rotation_calculator = rotation_calculator
        self.trajectory = WindingTrajectory(calibration)

        self._completed = False

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
    def action(self) -> WindingAction:
        phase = self.phase

        if phase in (
            WindingPhase.BELTS,
            WindingPhase.MATERIAL,
        ):
            return WindingAction.RUN_FORWARD

        return WindingAction.WAIT

    def update(
        self,
        frequency_hz: float,
        elapsed_seconds: float,
    ) -> None:
        if frequency_hz <= 0:
            raise ValueError("Frequency must be greater than zero")

        if elapsed_seconds < 0:
            raise ValueError("Elapsed seconds cannot be negative")

        if self._completed:
            return

        revolutions = self.rotation_calculator.revolutions_for_time(
            frequency_hz,
            elapsed_seconds,
        )

        self.position_tracker.move_forward(revolutions)

        if self.calibration.material_wound_turns is None:
            raise RuntimeError("Winding calibration is incomplete")

        if self.position_turns >= self.calibration.material_wound_turns:
            self._completed = True

    def reset(self) -> None:
        self.position_tracker.reset()
        self._completed = False

    def apply(self, frequency_hz: float) -> None:
        if frequency_hz <= 0:
            raise ValueError("Frequency must be greqter than zero")

        if self.action == WindingAction.RUN_FORWARD:
            self.machine.start_roller_forward(frequency_hz)
            return

        if self.action == WindingAction.WAIT:
            return
