import pytest

from app.services.machine.calibration.machine import MachineCalibration
from app.services.machine.calibration.winding import WindingCalibration
from app.services.machine.trajectory.drying import (
    DryingPhase,
    DryingTrajectory,
)


def create_trajectory() -> DryingTrajectory:
    machine_calibration = MachineCalibration()
    machine_calibration.set_material_start(20.0)
    machine_calibration.set_washing_stop(5.0)

    winding_calibration = WindingCalibration()
    winding_calibration.set_material_end(50.0)

    return DryingTrajectory(
        machine_calibration=machine_calibration,
        winding_calibration=winding_calibration,
    )


def test_position_at_washing_stop_is_belts():
    trajectory = create_trajectory()

    assert trajectory.phase_at(5.0) == DryingPhase.BELTS


def test_position_between_washing_stop_and_material_start_is_belts():
    trajectory = create_trajectory()

    assert trajectory.phase_at(10.0) == DryingPhase.BELTS


def test_position_at_material_start_is_material():
    trajectory = create_trajectory()

    assert trajectory.phase_at(20.0) == DryingPhase.MATERIAL


def test_position_inside_material_phase():
    trajectory = create_trajectory()

    assert trajectory.phase_at(35.0) == DryingPhase.MATERIAL


def test_position_at_material_end_is_material_end():
    trajectory = create_trajectory()

    assert trajectory.phase_at(50.0) == DryingPhase.MATERIAL_END


def test_position_after_material_end_is_material_end():
    trajectory = create_trajectory()

    assert trajectory.phase_at(60.0) == DryingPhase.MATERIAL_END


def test_drying_trajectory_requires_machine_calibration():
    machine_calibration = MachineCalibration()

    winding_calibration = WindingCalibration()
    winding_calibration.set_material_end(50.0)

    trajectory = DryingTrajectory(
        machine_calibration=machine_calibration,
        winding_calibration=winding_calibration,
    )

    with pytest.raises(
        ValueError,
        match="Material start point is not calibrated",
    ):
        trajectory.phase_at(10.0)


def test_drying_trajectory_requires_winding_calibration():
    machine_calibration = MachineCalibration()
    machine_calibration.set_material_start(20.0)
    machine_calibration.set_washing_stop(5.0)

    winding_calibration = WindingCalibration()

    trajectory = DryingTrajectory(
        machine_calibration=machine_calibration,
        winding_calibration=winding_calibration,
    )

    with pytest.raises(
        ValueError,
        match="Material end point is not calibrated",
    ):
        trajectory.phase_at(10.0)


def test_negative_position_is_invalid():
    trajectory = create_trajectory()

    with pytest.raises(
        ValueError,
        match="Position cannot be negative",
    ):
        trajectory.phase_at(-1.0)
