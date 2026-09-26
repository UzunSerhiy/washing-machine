from app.services.machine.calibration.washing import WashingCalibration
from app.services.machine.trajectory.washing import (
    WashingPhase,
    WashingTrajectory,
)


def create_calibration() -> WashingCalibration:
    calibration = WashingCalibration()

    calibration.set_material_reaches_brushes(70.0)
    calibration.set_material_end(40.0)
    calibration.set_belt_safe(15.0)

    return calibration


def test_position_before_material_reaches_brushes_is_material():
    trajectory = WashingTrajectory(create_calibration())

    assert trajectory.phase_at(100.0) == WashingPhase.MATERIAL


def test_position_at_material_reaches_brushes_is_belts():
    trajectory = WashingTrajectory(create_calibration())

    assert trajectory.phase_at(70.0) == WashingPhase.BELTS


def test_position_between_brushes_and_belt_safe_is_belts():
    trajectory = WashingTrajectory(create_calibration())

    assert trajectory.phase_at(40.0) == WashingPhase.BELTS


def test_position_at_belt_safe_is_belt_safe():
    trajectory = WashingTrajectory(create_calibration())

    assert trajectory.phase_at(15.0) == WashingPhase.BELT_SAFE


def test_position_after_belt_safe_is_belts():
    trajectory = WashingTrajectory(create_calibration())

    assert trajectory.phase_at(20.0) == WashingPhase.BELTS
