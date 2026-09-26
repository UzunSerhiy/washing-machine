from app.services.machine.calibration.winding import WindingCalibration
from app.services.machine.trajectory.winding import (
    WindingPhase,
    WindingTrajectory,
)
from app.services.machine.calibration.points import CalibrationPoint


def create_calibration() -> WindingCalibration:
    calibration = WindingCalibration()

    calibration.set_belt_start(100.0)
    calibration.set_material_wound(180.0)

    return calibration


def test_position_before_belt_start_is_belts():
    trajectory = WindingTrajectory(create_calibration())

    assert trajectory.phase_at(50.0) == WindingPhase.BELTS


def test_position_at_belt_start_is_material():
    trajectory = WindingTrajectory(create_calibration())

    assert trajectory.phase_at(100.0) == WindingPhase.MATERIAL


def test_position_inside_material_phase_is_material():
    trajectory = WindingTrajectory(create_calibration())

    assert trajectory.phase_at(140.0) == WindingPhase.MATERIAL


def test_position_at_material_wound_is_material_wound():
    trajectory = WindingTrajectory(create_calibration())

    assert trajectory.phase_at(180.0) == WindingPhase.MATERIAL_WOUND


def test_position_after_material_wound_is_material_wound():
    trajectory = WindingTrajectory(create_calibration())

    assert trajectory.phase_at(200.0) == WindingPhase.MATERIAL_WOUND


def test_next_point_before_belt_start():
    trajectory = WindingTrajectory(create_calibration())

    assert trajectory.next_point_at(50.0) == CalibrationPoint.WINDING_BELT_START


def test_next_point_at_belt_start():
    trajectory = WindingTrajectory(create_calibration())

    assert trajectory.next_point_at(100.0) == CalibrationPoint.WINDING_MATERIAL_WOUND


def test_next_point_inside_material_phase():
    trajectory = WindingTrajectory(create_calibration())

    assert trajectory.next_point_at(140.0) == CalibrationPoint.WINDING_MATERIAL_WOUND


def test_next_point_at_material_wound():
    trajectory = WindingTrajectory(create_calibration())

    assert trajectory.next_point_at(180.0) is None


def test_next_point_after_material_wound():
    trajectory = WindingTrajectory(create_calibration())

    assert trajectory.next_point_at(200.0) is None
