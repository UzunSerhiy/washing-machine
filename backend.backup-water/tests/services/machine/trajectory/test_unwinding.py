import pytest

from app.services.machine.calibration.machine import MachineCalibration
from app.services.machine.calibration.winding import WindingCalibration
from app.services.machine.trajectory.unwinding import (
    UnwindingPhase,
    UnwindingTrajectory,
)


def create_trajectory() -> UnwindingTrajectory:
    machine_calibration = MachineCalibration()
    machine_calibration.set_material_start(20.0)
    machine_calibration.set_washing_stop(5.0)

    winding_calibration = WindingCalibration()
    winding_calibration.set_material_end(50.0)

    return UnwindingTrajectory(
        machine_calibration=machine_calibration,
        winding_calibration=winding_calibration,
    )


def test_position_at_material_end_is_material():
    trajectory = create_trajectory()

    assert trajectory.phase_at(50.0) == UnwindingPhase.MATERIAL


def test_position_inside_material_phase():
    trajectory = create_trajectory()

    assert trajectory.phase_at(35.0) == UnwindingPhase.MATERIAL


def test_position_at_material_start_is_belts():
    trajectory = create_trajectory()

    assert trajectory.phase_at(20.0) == UnwindingPhase.BELTS


def test_position_between_material_start_and_point_zero_is_belts():
    trajectory = create_trajectory()

    assert trajectory.phase_at(10.0) == UnwindingPhase.BELTS


def test_position_at_point_zero_is_point_zero():
    trajectory = create_trajectory()

    assert trajectory.phase_at(0.0) == UnwindingPhase.POINT_0


def test_unwinding_trajectory_requires_machine_calibration():
    machine_calibration = MachineCalibration()

    winding_calibration = WindingCalibration()
    winding_calibration.set_material_end(50.0)

    trajectory = UnwindingTrajectory(
        machine_calibration=machine_calibration,
        winding_calibration=winding_calibration,
    )

    with pytest.raises(
        ValueError,
        match="Material start point is not calibrated",
    ):
        trajectory.phase_at(10.0)


def test_unwinding_trajectory_requires_winding_calibration():
    machine_calibration = MachineCalibration()
    machine_calibration.set_material_start(20.0)
    machine_calibration.set_washing_stop(5.0)

    winding_calibration = WindingCalibration()

    trajectory = UnwindingTrajectory(
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
