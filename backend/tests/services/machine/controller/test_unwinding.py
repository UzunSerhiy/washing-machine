import pytest

from app.services.machine.calibration.machine import MachineCalibration
from app.services.machine.calibration.position import RollerPositionTracker
from app.services.machine.calibration.winding import WindingCalibration
from app.services.machine.controller.unwinding import (
    UnwindingAction,
    UnwindingController,
)
from app.services.machine.trajectory.unwinding import UnwindingPhase
from app.services.winding.calculator import WindingCalculator
from app.services.winding.rotation import RollerRotationCalculator


class FakeMachine:
    def __init__(self):
        self.calls = []

    def start_roller_reverse(self, frequency_hz: float):
        self.calls.append(("start_roller_reverse", frequency_hz))

    def stop_roller(self):
        self.calls.append(("stop_roller",))


def create_controller() -> UnwindingController:
    machine_calibration = MachineCalibration()
    machine_calibration.set_material_start(100.0)
    machine_calibration.set_washing_stop(15.0)

    winding_calibration = WindingCalibration()
    winding_calibration.set_material_end(180.0)

    return UnwindingController(
        machine=FakeMachine(),
        machine_calibration=machine_calibration,
        winding_calibration=winding_calibration,
        position_tracker=RollerPositionTracker(),
        rotation_calculator=RollerRotationCalculator(
            motor_rpm_at_50hz=905.0,
            gear_ratio=100.0,
        ),
        winding_calculator=WindingCalculator(
            core_diameter_mm=100.0,
            material_thickness_mm=1.0,
        ),
    )


def test_unwinding_runs_reverse_from_material_end():
    controller = create_controller()

    controller.position_tracker.set_position(180.0)

    assert controller.phase == UnwindingPhase.MATERIAL
    assert controller.action == UnwindingAction.RUN_REVERSE


def test_unwinding_uses_material_curve_inside_material():
    controller = create_controller()

    controller.position_tracker.set_position(160.0)

    controller.apply(
        material_speed_percent=80.0,
        belt_frequency_hz=40.0,
    )

    expected_frequency = controller.winding_calculator.frequency_hz(80.0)

    assert controller.machine.calls == [
        ("start_roller_reverse", expected_frequency),
    ]


def test_unwinding_material_curve_uses_remaining_wound_turns():
    controller = create_controller()

    controller.position_tracker.set_position(160.0)

    controller.apply(
        material_speed_percent=80.0,
        belt_frequency_hz=40.0,
    )

    assert controller.winding_calculator.wound_turns == pytest.approx(60.0)


def test_unwinding_frequency_increases_as_roll_shrinks():
    controller = create_controller()

    controller.position_tracker.set_position(160.0)

    controller.apply(
        material_speed_percent=80.0,
        belt_frequency_hz=40.0,
    )

    first_frequency = controller.machine.calls[-1][1]

    controller.machine.calls.clear()

    controller.position_tracker.set_position(120.0)

    controller.apply(
        material_speed_percent=80.0,
        belt_frequency_hz=40.0,
    )

    second_frequency = controller.machine.calls[-1][1]

    assert second_frequency > first_frequency


def test_unwinding_uses_belt_speed_after_material_start():
    controller = create_controller()

    controller.position_tracker.set_position(50.0)

    controller.apply(
        material_speed_percent=80.0,
        belt_frequency_hz=40.0,
    )

    assert controller.machine.calls == [
        ("start_roller_reverse", 40.0),
    ]


def test_unwinding_stops_at_point_zero():
    controller = create_controller()

    controller.position_tracker.set_position(0.0)

    assert controller.action == UnwindingAction.STOP

    controller.apply(
        material_speed_percent=80.0,
        belt_frequency_hz=40.0,
    )

    assert controller.machine.calls == [
        ("stop_roller",),
    ]

    assert controller.action == UnwindingAction.WAIT


def test_unwinding_update_moves_reverse():
    controller = create_controller()

    controller.position_tracker.set_position(50.0)

    controller.update(
        material_speed_percent=80.0,
        belt_frequency_hz=40.0,
        elapsed_seconds=60.0,
    )

    assert controller.position_turns < 50.0


def test_unwinding_does_not_overshoot_point_zero():
    controller = create_controller()

    controller.position_tracker.set_position(1.0)

    controller.update(
        material_speed_percent=80.0,
        belt_frequency_hz=40.0,
        elapsed_seconds=120.0,
    )

    assert controller.position_turns == pytest.approx(0.0)
    assert controller.completed is True
    assert controller.action == UnwindingAction.STOP
