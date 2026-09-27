import pytest

from app.services.machine.calibration.machine import MachineCalibration
from app.services.machine.calibration.points import CalibrationPoint
from app.services.machine.calibration.winding import WindingCalibration
from app.services.machine.trajectory.winding import (
    WindingPhase,
    WindingTrajectory,
)


def create_trajectory() -> WindingTrajectory:
    machine_calibration = MachineCalibration()
    machine_calibration.set_material_start(20.0)
    machine_calibration.set_washing_stop(5.0)

    winding_calibration = WindingCalibration()
    winding_calibration.set_material_end(50.0)

    return WindingTrajectory(
        machine_calibration=machine_calibration,
        winding_calibration=winding_calibration,
    )


def test_position_before_material_start_is_belts():
    trajectory = create_trajectory()

    assert trajectory.phase_at(10.0) == WindingPhase.BELTS


def test_position_at_material_start_is_material():
    trajectory = create_trajectory()

    assert trajectory.phase_at(20.0) == WindingPhase.MATERIAL


def test_position_inside_material_phase():
    trajectory = create_trajectory()

    assert trajectory.phase_at(35.0) == WindingPhase.MATERIAL


def test_position_at_material_end_is_material_end():
    trajectory = create_trajectory()

    assert trajectory.phase_at(50.0) == WindingPhase.MATERIAL_END


def test_position_after_material_end_is_material_end():
    trajectory = create_trajectory()

    assert trajectory.phase_at(60.0) == WindingPhase.MATERIAL_END


def test_next_point_before_material_start():
    trajectory = create_trajectory()

    assert trajectory.next_point_at(10.0) == CalibrationPoint.MATERIAL_START


def test_next_point_inside_material_phase():
    trajectory = create_trajectory()

    assert trajectory.next_point_at(30.0) == CalibrationPoint.MATERIAL_END


def test_next_point_at_material_end_is_none():
    trajectory = create_trajectory()

    assert trajectory.next_point_at(50.0) is None


def test_winding_trajectory_requires_machine_calibration():
    machine_calibration = MachineCalibration()

    winding_calibration = WindingCalibration()
    winding_calibration.set_material_end(50.0)

    trajectory = WindingTrajectory(
        machine_calibration=machine_calibration,
        winding_calibration=winding_calibration,
    )

    with pytest.raises(
        ValueError,
        match="Material start point is not calibrated",
    ):
        trajectory.phase_at(10.0)


def test_winding_trajectory_requires_winding_calibration():
    machine_calibration = MachineCalibration()
    machine_calibration.set_material_start(20.0)
    machine_calibration.set_washing_stop(5.0)

    winding_calibration = WindingCalibration()

    trajectory = WindingTrajectory(
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
