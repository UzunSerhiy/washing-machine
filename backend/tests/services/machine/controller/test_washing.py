import pytest

from app.services.machine.calibration.machine import MachineCalibration
from app.services.machine.calibration.position import (
    RollerPositionTracker,
)
from app.services.machine.calibration.winding import WindingCalibration
from app.services.machine.controller.washing import (
    WashingAction,
    WashingController,
)
from app.services.machine.trajectory.washing import WashingPhase
from app.services.winding.calculator import WindingCalculator
from app.services.winding.rotation import RollerRotationCalculator


class FakeMachine:
    def __init__(self):
        self.calls = []

    def start_roller_reverse(self, frequency_hz: float):
        self.calls.append(("start_roller_reverse", frequency_hz))

    def start_brush(self, frequency_hz: float):
        self.calls.append(("start_brush", frequency_hz))

    def stop_all(self):
        self.calls.append(("stop_all",))


def create_controller() -> WashingController:
    machine_calibration = MachineCalibration()
    machine_calibration.set_material_start(100.0)
    machine_calibration.set_washing_stop(15.0)

    winding_calibration = WindingCalibration()
    winding_calibration.set_material_end(180.0)

    rotation_calculator = RollerRotationCalculator(
        motor_rpm_at_50hz=905.0,
        gear_ratio=100.0,
    )

    winding_calculator = WindingCalculator(
        core_diameter_mm=100.0,
        material_thickness_mm=1.0,
    )

    position_tracker = RollerPositionTracker()

    machine = FakeMachine()

    return WashingController(
        machine=machine,
        machine_calibration=machine_calibration,
        winding_calibration=winding_calibration,
        position_tracker=position_tracker,
        rotation_calculator=rotation_calculator,
        winding_calculator=winding_calculator,
    )


def test_initial_position_is_washing_stop():
    controller = create_controller()

    assert controller.position_turns == 0.0
    assert controller.phase == WashingPhase.WASHING_STOP
    assert controller.action == WashingAction.STOP


def test_position_inside_belts_phase():
    controller = create_controller()

    controller.position_tracker.move_forward(50.0)

    assert controller.position_turns == 50.0
    assert controller.phase == WashingPhase.BELTS
    assert controller.action == WashingAction.RUN_REVERSE


def test_position_at_material_start_is_belts():
    controller = create_controller()

    controller.position_tracker.move_forward(100.0)

    assert controller.position_turns == 100.0
    assert controller.phase == WashingPhase.BELTS
    assert controller.action == WashingAction.RUN_REVERSE


def test_position_inside_material_phase():
    controller = create_controller()

    controller.position_tracker.move_forward(120.0)

    assert controller.position_turns == 120.0
    assert controller.phase == WashingPhase.MATERIAL
    assert controller.action == WashingAction.RUN_REVERSE


def test_position_at_material_end_is_material_phase():
    controller = create_controller()

    controller.position_tracker.move_forward(180.0)

    assert controller.position_turns == 180.0
    assert controller.phase == WashingPhase.MATERIAL
    assert controller.action == WashingAction.RUN_REVERSE


def test_position_at_washing_stop_requires_stop():
    controller = create_controller()

    controller.position_tracker.move_forward(15.0)

    assert controller.position_turns == 15.0
    assert controller.phase == WashingPhase.WASHING_STOP
    assert controller.action == WashingAction.STOP


def test_stop_action_becomes_wait_after_stop_is_applied():
    controller = create_controller()

    controller.position_tracker.move_forward(15.0)

    assert controller.action == WashingAction.STOP

    controller._stop_applied = True

    assert controller.action == WashingAction.WAIT


def test_reset_returns_controller_to_initial_state():
    controller = create_controller()

    controller.position_tracker.move_forward(120.0)
    controller._completed = True
    controller._stop_applied = True

    controller.reset()

    assert controller.position_turns == 0.0
    assert controller.completed is False
    assert controller.phase == WashingPhase.WASHING_STOP
    assert controller.action == WashingAction.STOP


def test_apply_runs_roller_reverse_and_brush_in_material_phase():
    controller = create_controller()
    machine = controller.machine

    controller.position_tracker.move_forward(120.0)

    controller.apply(
        material_speed_percent=100.0,
        belt_frequency_hz=20.0,
        brush_frequency_hz=8.0,
    )

    expected_frequency = controller.winding_calculator.frequency_hz(
        speed_percent=100.0,
    )

    assert machine.calls == [
        ("start_roller_reverse", expected_frequency),
        ("start_brush", 8.0),
    ]


def test_apply_runs_roller_reverse_and_brush_in_belts_phase():
    controller = create_controller()
    machine = controller.machine

    controller.position_tracker.move_forward(50.0)

    controller.apply(
        material_speed_percent=100.0,
        belt_frequency_hz=20.0,
        brush_frequency_hz=8.0,
    )

    assert machine.calls == [
        ("start_roller_reverse", 20.0),
        ("start_brush", 8.0),
    ]


def test_apply_stops_machine_at_washing_stop():
    controller = create_controller()
    machine = controller.machine

    controller.position_tracker.move_forward(15.0)

    controller.apply(
        material_speed_percent=100.0,
        belt_frequency_hz=20.0,
        brush_frequency_hz=8.0,
    )

    assert machine.calls == [
        ("stop_all",),
    ]
    assert controller.action == WashingAction.WAIT


def test_apply_does_nothing_after_stop():
    controller = create_controller()
    machine = controller.machine

    controller.position_tracker.move_forward(15.0)

    controller.apply(
        material_speed_percent=100.0,
        belt_frequency_hz=20.0,
        brush_frequency_hz=8.0,
    )

    controller.apply(
        material_speed_percent=100.0,
        belt_frequency_hz=20.0,
        brush_frequency_hz=8.0,
    )

    assert machine.calls == [
        ("stop_all",),
    ]


def test_update_moves_position_reverse_in_belts_phase():
    controller = create_controller()

    controller.position_tracker.move_forward(50.0)

    controller.update(
        material_speed_percent=60.0,
        belt_frequency_hz=20.0,
        brush_frequency_hz=8.0,
        elapsed_seconds=60.0,
    )

    assert controller.position_turns == pytest.approx(46.38)
    assert controller.phase == WashingPhase.BELTS
    assert controller.completed is False


def test_update_crosses_material_start_and_enters_belts_phase():
    controller = create_controller()

    controller.position_tracker.move_forward(101.0)

    controller.winding_calculator.set_turns(180.0 - 101.0)

    frequency_hz = controller.winding_calculator.frequency_hz(
        speed_percent=100.0,
    )

    roller_rpm = controller.rotation_calculator.roller_rpm(frequency_hz)

    elapsed_seconds = 1.0 / roller_rpm * 60.0

    controller.update(
        material_speed_percent=100.0,
        belt_frequency_hz=20.0,
        brush_frequency_hz=8.0,
        elapsed_seconds=elapsed_seconds,
    )

    assert controller.position_turns == pytest.approx(100.0)
    assert controller.phase == WashingPhase.BELTS
    assert controller.completed is False


def test_apply_material_frequency_depends_on_remaining_material():
    controller = create_controller()
    machine = controller.machine

    controller.position_tracker.move_forward(120.0)

    controller.apply(
        material_speed_percent=100.0,
        belt_frequency_hz=20.0,
        brush_frequency_hz=8.0,
    )

    first_frequency = machine.calls[0][1]

    controller.reset()
    machine.calls.clear()

    controller.position_tracker.move_forward(160.0)

    controller.apply(
        material_speed_percent=100.0,
        belt_frequency_hz=20.0,
        brush_frequency_hz=8.0,
    )

    second_frequency = machine.calls[0][1]

    assert first_frequency != second_frequency
    assert second_frequency > first_frequency


def test_update_does_not_overshoot_washing_stop():
    controller = create_controller()

    controller.position_tracker.move_forward(16.0)

    controller.update(
        material_speed_percent=100.0,
        belt_frequency_hz=20.0,
        brush_frequency_hz=8.0,
        elapsed_seconds=60.0,
    )

    assert controller.position_turns == pytest.approx(15.0)
    assert controller.completed is True


def test_update_to_material_start_then_apply_starts_belt_phase():
    controller = create_controller()
    machine = controller.machine

    controller.position_tracker.move_forward(101.0)

    controller.winding_calculator.set_turns(180.0 - 101.0)

    frequency_hz = controller.winding_calculator.frequency_hz(
        speed_percent=100.0,
    )

    roller_rpm = controller.rotation_calculator.roller_rpm(frequency_hz)

    elapsed_seconds = 60.0 / roller_rpm

    controller.update(
        material_speed_percent=100.0,
        belt_frequency_hz=20.0,
        brush_frequency_hz=8.0,
        elapsed_seconds=elapsed_seconds,
    )

    assert controller.position_turns == pytest.approx(100.0)
    assert controller.phase == WashingPhase.BELTS
    assert controller.completed is False

    controller.apply(
        material_speed_percent=100.0,
        belt_frequency_hz=20.0,
        brush_frequency_hz=8.0,
    )

    assert machine.calls == [
        ("start_roller_reverse", 20.0),
        ("start_brush", 8.0),
    ]


def test_update_does_not_overshoot_washing_stop_from_belts_phase():
    controller = create_controller()

    controller.position_tracker.move_forward(16.0)

    controller.update(
        material_speed_percent=100.0,
        belt_frequency_hz=20.0,
        brush_frequency_hz=8.0,
        elapsed_seconds=60.0,
    )

    assert controller.position_turns == pytest.approx(15.0)
    assert controller.phase == WashingPhase.WASHING_STOP
    assert controller.completed is True


def test_completed_washing_requires_stop_then_wait():
    controller = create_controller()
    machine = controller.machine

    controller.position_tracker.move_forward(16.0)

    controller.update(
        material_speed_percent=100.0,
        belt_frequency_hz=20.0,
        brush_frequency_hz=8.0,
        elapsed_seconds=60.0,
    )

    assert controller.position_turns == pytest.approx(15.0)
    assert controller.completed is True
    assert controller.action == WashingAction.STOP

    controller.apply(
        material_speed_percent=100.0,
        belt_frequency_hz=20.0,
        brush_frequency_hz=8.0,
    )

    assert machine.calls == [
        ("stop_all",),
    ]
    assert controller.action == WashingAction.WAIT

    controller.apply(
        material_speed_percent=100.0,
        belt_frequency_hz=20.0,
        brush_frequency_hz=8.0,
    )

    assert machine.calls == [
        ("stop_all",),
    ]
