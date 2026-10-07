import pytest

from app.services.machine.calibration.machine import MachineCalibration
from app.services.machine.calibration.position import RollerPositionTracker
from app.services.machine.calibration.winding import WindingCalibration
from app.services.machine.controller.drying import (
    DryingAction,
    DryingController,
)
from app.services.machine.trajectory.drying import DryingPhase
from app.services.winding.calculator import WindingCalculator
from app.services.winding.rotation import RollerRotationCalculator


class FakeMachine:
    def __init__(self):
        self.calls = []

    def start_roller_forward(self, frequency_hz: float):
        self.calls.append(("start_roller_forward", frequency_hz))

    def start_brush(self, frequency_hz: float):
        self.calls.append(("start_brush", frequency_hz))

    def stop_all(self):
        self.calls.append(("stop_all",))


def create_controller() -> DryingController:
    machine_calibration = MachineCalibration()
    machine_calibration.set_material_start(100.0)
    machine_calibration.set_washing_stop(15.0)

    winding_calibration = WindingCalibration()
    winding_calibration.set_material_end(180.0)

    return DryingController(
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


def test_drying_runs_forward_from_washing_stop():
    controller = create_controller()

    controller.position_tracker.set_position(15.0)

    assert controller.phase == DryingPhase.BELTS
    assert controller.action == DryingAction.RUN_FORWARD


def test_drying_uses_belt_speed_before_material():
    controller = create_controller()

    controller.position_tracker.set_position(50.0)

    controller.apply(
        material_speed_percent=30.0,
        belt_frequency_hz=15.0,
        brush_frequency_hz=15.0,
    )

    assert controller.machine.calls == [
        ("start_roller_forward", 15.0),
        ("start_brush", 15.0),
    ]


def test_drying_uses_material_curve_inside_material():
    controller = create_controller()

    controller.position_tracker.set_position(120.0)

    controller.apply(
        material_speed_percent=30.0,
        belt_frequency_hz=15.0,
        brush_frequency_hz=15.0,
    )

    expected_frequency = controller.winding_calculator.frequency_hz(30.0)

    assert controller.machine.calls == [
        ("start_roller_forward", expected_frequency),
        ("start_brush", 15.0),
    ]


def test_drying_material_curve_uses_wound_turns():
    controller = create_controller()

    controller.position_tracker.set_position(120.0)

    controller.apply(
        material_speed_percent=30.0,
        belt_frequency_hz=15.0,
        brush_frequency_hz=15.0,
    )

    assert controller.winding_calculator.wound_turns == pytest.approx(20.0)


def test_drying_stops_at_material_end():
    controller = create_controller()

    controller.position_tracker.set_position(180.0)

    assert controller.action == DryingAction.STOP

    controller.apply(
        material_speed_percent=30.0,
        belt_frequency_hz=15.0,
        brush_frequency_hz=15.0,
    )

    assert controller.machine.calls == [
        ("stop_all",),
    ]

    assert controller.action == DryingAction.WAIT


def test_drying_update_moves_forward_using_belt_speed():
    controller = create_controller()

    controller.position_tracker.set_position(50.0)

    controller.update(
        material_speed_percent=30.0,
        belt_frequency_hz=15.0,
        brush_frequency_hz=15.0,
        elapsed_seconds=60.0,
    )

    assert controller.position_turns > 50.0


def test_drying_does_not_overshoot_material_end():
    controller = create_controller()

    controller.position_tracker.set_position(179.0)

    controller.update(
        material_speed_percent=30.0,
        belt_frequency_hz=15.0,
        brush_frequency_hz=15.0,
        elapsed_seconds=120.0,
    )

    assert controller.position_turns == pytest.approx(180.0)
    assert controller.completed is True
    assert controller.action == DryingAction.STOP
