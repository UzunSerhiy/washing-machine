from app.services.machine.calibration.position import (
    RollerPositionTracker,
)
from app.services.machine.calibration.winding import WindingCalibration
from app.services.machine.controller.winding import (
    WindingAction,
    WindingController,
)
from app.services.machine.trajectory.winding import WindingPhase
from app.services.winding.rotation import RollerRotationCalculator


class FakeMachine:
    def __init__(self):
        self.calls = []

    def start_roller_forward(self, frequency_hz: float):
        self.calls.append(("start_roller_forward", frequency_hz))


def create_controller() -> WindingController:
    calibration = WindingCalibration()

    calibration.set_belt_start(100.0)
    calibration.set_material_wound(180.0)

    position_tracker = RollerPositionTracker()

    rotation_calculator = RollerRotationCalculator(
        motor_rpm_at_50hz=905.0,
        gear_ratio=100.0,
    )

    machine = FakeMachine()

    return WindingController(
        machine=machine,
        calibration=calibration,
        position_tracker=position_tracker,
        rotation_calculator=rotation_calculator,
    )


def create_controller_with_machine():
    calibration = WindingCalibration()

    calibration.set_belt_start(100.0)
    calibration.set_material_wound(180.0)

    position_tracker = RollerPositionTracker()

    rotation_calculator = RollerRotationCalculator(
        motor_rpm_at_50hz=905.0, gear_ratio=100.0
    )

    machine = FakeMachine()

    controller = WindingController(
        machine=machine,
        calibration=calibration,
        position_tracker=position_tracker,
        rotation_calculator=rotation_calculator,
    )

    return controller, machine


def test_initial_position_is_belts():
    controller = create_controller()

    assert controller.position_turns == 0.0
    assert controller.phase == WindingPhase.BELTS
    assert controller.action == WindingAction.RUN_FORWARD


def test_position_before_belt_start_is_belts():
    controller = create_controller()

    controller.position_tracker.move_forward(50.0)

    assert controller.position_turns == 50.0
    assert controller.phase == WindingPhase.BELTS
    assert controller.action == WindingAction.RUN_FORWARD


def test_position_at_belt_start_is_material():
    controller = create_controller()

    controller.position_tracker.move_forward(100.0)

    assert controller.position_turns == 100.0
    assert controller.phase == WindingPhase.MATERIAL
    assert controller.action == WindingAction.RUN_FORWARD


def test_position_inside_material_is_material():
    controller = create_controller()

    controller.position_tracker.move_forward(140.0)

    assert controller.position_turns == 140.0
    assert controller.phase == WindingPhase.MATERIAL
    assert controller.action == WindingAction.RUN_FORWARD


def test_position_at_material_wound_waits():
    controller = create_controller()

    controller.position_tracker.move_forward(180.0)

    assert controller.position_turns == 180.0
    assert controller.phase == WindingPhase.MATERIAL_WOUND
    assert controller.action == WindingAction.WAIT


def test_update_moves_position_forward():
    controller = create_controller()
    controller.update(
        frequency_hz=50.0,
        elapsed_seconds=60.0,
    )

    assert controller.position_turns == 9.05
    assert controller.phase == WindingPhase.BELTS


def test_controller_is_not_completed_before_material_wound():
    controller = create_controller()

    controller.update(
        frequency_hz=50.0,
        elapsed_seconds=60.0,
    )

    assert controller.position_turns == 9.05
    assert controller.completed is False


def test_controller_becomes_completed_after_material_wound():
    controller = create_controller()

    controller.position_tracker.move_forward(175.0)

    controller.update(frequency_hz=50.0, elapsed_seconds=60.0)

    assert controller.position_turns == 184.05
    assert controller.completed is True


def test_completed_controller_does_not_continue_moving():
    controller = create_controller()

    controller.position_tracker.move_forward(180.0)

    controller.update(
        frequency_hz=50.0,
        elapsed_seconds=1.0,
    )

    completed_position = controller.position_turns

    controller.update(
        frequency_hz=50.0,
        elapsed_seconds=60.0,
    )

    assert controller.completed is True
    assert controller.position_turns == completed_position


def test_reset_returns_controller_to_initial_state():
    controller = create_controller()

    controller.position_tracker.move_forward(180.0)

    controller.update(
        frequency_hz=50.0,
        elapsed_seconds=1.0,
    )

    assert controller.completed is True

    controller.reset()

    assert controller.position_turns == 0.0
    assert controller.completed is False
    assert controller.phase == WindingPhase.BELTS
    assert controller.action == WindingAction.RUN_FORWARD


def test_controller_can_run_again_after_reset():
    controller = create_controller()

    controller.position_tracker.move_forward(180.0)

    controller.update(frequency_hz=50, elapsed_seconds=60.0)

    assert controller.completed is True

    controller.reset()

    controller.update(
        frequency_hz=50.0,
        elapsed_seconds=60.0,
    )

    assert controller.position_turns == 9.05
    assert controller.completed is False


def test_apply_runs_roller_forward():
    controller, machine = create_controller_with_machine()

    controller.apply(25.0)

    assert machine.calls == [("start_roller_forward", 25.0)]


def test_apply_does_nothing_when_material_is_wound():
    controller, machine = create_controller_with_machine()

    controller.position_tracker.move_forward(180.0)

    controller.apply(25.0)

    assert machine.calls == []
