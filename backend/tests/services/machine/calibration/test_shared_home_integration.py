"""Regression checks for shared HOME / calibration integration."""
from unittest.mock import Mock

import pytest

from app.services.machine.calibration.session_service import CalibrationSessionService
from app.services.machine.calibration.stage import CalibrationStage
from app.services.winding.rotation import RollerRotationCalculator


def make_service(homing=None):
    machine = Mock()
    service = CalibrationSessionService(
        machine=machine,
        rotation_calculator=RollerRotationCalculator(
            motor_rpm_at_50hz=905.0, gear_ratio=100.0,
        ),
    )
    if homing is not None:
        service.set_roller_homing_service(homing)
    return service, machine


def test_calibration_cannot_start_without_shared_home():
    service, machine = make_service()
    with pytest.raises(RuntimeError, match="not configured"):
        service.start(material_profile_id=1)
    machine.start_roller_forward.assert_not_called()
    machine.start_roller_reverse.assert_not_called()


def test_calibration_cannot_start_without_confirmed_zero():
    homing = Mock(searching=False)
    homing.require_zero.side_effect = RuntimeError("Point 0 is not confirmed")
    service, machine = make_service(homing)
    with pytest.raises(RuntimeError, match="Point 0"):
        service.start(material_profile_id=1)
    assert not service.active
    machine.start_roller_forward.assert_not_called()


def test_calibration_starts_after_shared_home_at_material_start_stage():
    homing = Mock(searching=False)
    service, machine = make_service(homing)
    session = service.start(material_profile_id=1)
    homing.require_zero.assert_called_once()
    assert session.position_turns == 0.0
    assert session.stage == CalibrationStage.MATERIAL_START
    machine.start_roller_reverse.assert_not_called()


def test_calibration_does_not_allow_manual_zero_reset_after_home():
    service, _ = make_service(Mock(searching=False))
    service.start(material_profile_id=1)
    with pytest.raises(RuntimeError, match="already confirmed"):
        service.reset_position()
