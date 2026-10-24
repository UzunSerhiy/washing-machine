from app.services.machine.calibration.machine import MachineCalibration
from app.services.machine.calibration.position import (
    RollerPositionTracker,
)
from app.services.machine.calibration.winding import WindingCalibration
from app.services.machine.controller.winding import (
    WindingAction,
    WindingController,
)
from app.services.machine.trajectory.winding import WindingPhase
from app.services.winding.calculator import WindingCalculator
from app.services.winding.rotation import RollerRotationCalculator


class FakeMachine:
    def __init__(self):
        self.calls = []

    def start_roller_forward(self, frequency_hz: float):
        self.calls.append(("start_roller_forward", frequency_hz))

    def stop_roller(self):
        self.calls.append(("stop_roller",))


def create_controller() -> WindingController:
    machine_calibration = MachineCalibration()
    machine_calibration.set_material_start(100.0)
    machine_calibration.set_washing_stop(5.0)

    winding_calibration = WindingCalibration()
    winding_calibration.set_material_end(180.0)

    winding_calculator = WindingCalculator(
        core_diameter_mm=100.0,
        material_thickness_mm=1.0,
    )

    position_tracker = RollerPositionTracker()

    rotation_calculator = RollerRotationCalculator(
        motor_rpm_at_50hz=905.0,
        gear_ratio=100.0,
    )

    machine = FakeMachine()

    return WindingController(
        machine=machine,
        machine_calibration=machine_calibration,
        winding_calibration=winding_calibration,
        position_tracker=position_tracker,
        rotation_calculator=rotation_calculator,
        winding_calculator=winding_calculator,
    )


def create_controller_with_machine():
    controller = create_controller()

    return controller, controller.machine


def test_initial_position_is_belts():
    controller = create_controller()

    assert controller.position_turns == 0.0
    assert controller.phase == WindingPhase.BELTS
    assert controller.action == WindingAction.RUN_FORWARD


def test_position_before_material_start_is_belts():
    controller = create_controller()

    controller.position_tracker.move_forward(50.0)

    assert controller.position_turns == 50.0
    assert controller.phase == WindingPhase.BELTS
    assert controller.action == WindingAction.RUN_FORWARD


def test_position_at_material_start_is_material():
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


def test_position_at_material_end_is_material_end():
    controller = create_controller()

    controller.position_tracker.move_forward(180.0)

    assert controller.position_turns == 180.0
    assert controller.phase == WindingPhase.MATERIAL_END
    assert controller.action == WindingAction.STOP


def test_update_moves_position_forward_in_belts_phase():
    controller = create_controller()

    controller.update(
        belt_frequency_hz=50.0,
        speed_percent=100.0,
        elapsed_seconds=60.0,
    )

    assert controller.position_turns == 9.05
    assert controller.phase == WindingPhase.BELTS
    assert controller.completed is False


def test_controller_is_not_completed_before_material_end():
    controller = create_controller()

    controller.position_tracker.move_forward(150.0)

    controller.update(
        belt_frequency_hz=20.0,
        speed_percent=100.0,
        elapsed_seconds=1.0,
    )

    assert controller.position_turns > 150.0
    assert controller.position_turns < 180.0
    assert controller.completed is False


def test_controller_completes_at_material_end():
    controller = create_controller()

    controller.position_tracker.move_forward(175.0)

    controller.update(
        belt_frequency_hz=20.0,
        speed_percent=100.0,
        elapsed_seconds=120.0,
    )

    assert controller.position_turns == 180.0
    assert controller.phase == WindingPhase.MATERIAL_END
    assert controller.completed is True
    assert controller.action == WindingAction.STOP


def test_completed_controller_does_not_continue_moving():
    controller = create_controller()

    controller.position_tracker.move_forward(175.0)

    controller.update(
        belt_frequency_hz=20.0,
        speed_percent=100.0,
        elapsed_seconds=120.0,
    )

    assert controller.completed is True

    completed_position = controller.position_turns

    controller.update(
        belt_frequency_hz=20.0,
        speed_percent=100.0,
        elapsed_seconds=60.0,
    )

    assert controller.completed is True
    assert controller.position_turns == completed_position


def test_reset_returns_controller_to_initial_state():
    controller = create_controller()

    controller.position_tracker.move_forward(175.0)

    controller.update(
        belt_frequency_hz=20.0,
        speed_percent=100.0,
        elapsed_seconds=120.0,
    )

    assert controller.completed is True

    controller.reset()

    assert controller.position_turns == 0.0
    assert controller.completed is False
    assert controller.phase == WindingPhase.BELTS
    assert controller.action == WindingAction.RUN_FORWARD


def test_controller_can_run_again_after_reset():
    controller = create_controller()

    controller.position_tracker.move_forward(175.0)

    controller.update(
        belt_frequency_hz=20.0,
        speed_percent=100.0,
        elapsed_seconds=120.0,
    )

    assert controller.completed is True

    controller.reset()

    controller.update(
        belt_frequency_hz=50.0,
        speed_percent=100.0,
        elapsed_seconds=60.0,
    )

    assert controller.position_turns == 9.05
    assert controller.completed is False


def test_apply_runs_roller_forward():
    controller, machine = create_controller_with_machine()

    controller.apply(
        belt_frequency_hz=20.0,
        speed_percent=100.0,
    )

    assert machine.calls == [
        ("start_roller_forward", 20.0),
    ]


def test_apply_uses_winding_curve_in_material_phase():
    controller, machine = create_controller_with_machine()

    controller.position_tracker.move_forward(120.0)

    controller.apply(
        belt_frequency_hz=20.0,
        speed_percent=100.0,
    )

    expected_frequency = controller.winding_calculator.frequency_hz(100.0)

    assert machine.calls == [
        ("start_roller_forward", expected_frequency),
    ]


def test_update_crosses_material_start_and_enters_material():
    controller = create_controller()

    controller.position_tracker.move_forward(95.0)

    controller.update(
        belt_frequency_hz=50.0,
        speed_percent=100.0,
        elapsed_seconds=60.0,
    )

    assert controller.position_turns == 104.05
    assert controller.phase == WindingPhase.MATERIAL
    assert controller.completed is False


def test_update_crosses_material_end_and_completes():
    controller = create_controller()

    controller.position_tracker.move_forward(175.0)

    controller.update(
        belt_frequency_hz=20.0,
        speed_percent=100.0,
        elapsed_seconds=120.0,
    )

    assert controller.position_turns == 180.0
    assert controller.phase == WindingPhase.MATERIAL_END
    assert controller.completed is True
    assert controller.action == WindingAction.STOP


def test_position_at_material_end_requires_stop():
    controller, _ = create_controller_with_machine()

    controller.position_tracker.move_forward(180.0)

    assert controller.phase == WindingPhase.MATERIAL_END
    assert controller.completed is False
    assert controller.action == WindingAction.STOP


def test_apply_stops_at_material_end():
    controller, machine = create_controller_with_machine()

    controller.position_tracker.move_forward(180.0)

    controller.apply(
        belt_frequency_hz=20.0,
        speed_percent=100.0,
    )

    assert controller.stop_applied is True
    assert controller.action == WindingAction.WAIT

    controller.apply(
        belt_frequency_hz=20.0,
        speed_percent=100.0,
    )

    assert machine.calls == [
        ("stop_roller",),
    ]


def test_material_phase_sets_winding_turns_from_position():
    controller, _ = create_controller_with_machine()

    controller.position_tracker.move_forward(120.0)

    controller.apply(
        belt_frequency_hz=20.0,
        speed_percent=100.0,
    )

    assert controller.winding_calculator.wound_turns == 20.0


def test_material_phase_calculates_frequency_from_winding_curve():
    controller, machine = create_controller_with_machine()

    controller.position_tracker.move_forward(120.0)

    controller.apply(
        belt_frequency_hz=20.0,
        speed_percent=100.0,
    )

    expected_frequency = controller.winding_calculator.frequency_hz(100.0)

    assert machine.calls == [
        ("start_roller_forward", expected_frequency),
    ]


def test_update_uses_current_winding_frequency():
    controller, _ = create_controller_with_machine()

    controller.position_tracker.move_forward(120.0)
    controller.winding_calculator.set_turns(20.0)

    expected_frequency = controller.winding_calculator.frequency_hz(100.0)

    expected_revolutions = controller.rotation_calculator.revolutions_for_time(
        expected_frequency,
        1.0,
    )

    controller.update(
        belt_frequency_hz=20.0,
        speed_percent=100.0,
        elapsed_seconds=1.0,
    )

    assert controller.position_turns == (120.0 + expected_revolutions)
