from types import SimpleNamespace
from unittest.mock import Mock
import pytest

from app.services.machine.motion_fault_recovery import MotionFaultRecoveryService


def make_service():
    drives = {i: Mock() for i in (1, 2, 3)}
    for drive in drives.values():
        drive.get_fault.return_value = 0
        drive.get_status.return_value = 3
        drive.get_frequency.return_value = 0.0
    machine = SimpleNamespace(motion_fault_latched="roller: fault 15")
    drive_service = SimpleNamespace(drives=drives, configs={i: SimpleNamespace(enabled=True) for i in drives})
    auto = SimpleNamespace(get_status=lambda: {"status": "FAULT", "running": False, "paused": False})
    calibration = SimpleNamespace(active=False, auto_mode=None)
    home = SimpleNamespace(get_status=lambda: {"state": "FAULT", "searching": False, "awaiting_stop": False})
    return MotionFaultRecoveryService(machine, drive_service, auto, calibration, home), drives, calibration


def test_verifies_three_samples_without_writes():
    service, drives, _ = make_service()
    result = service.verify(operator_confirmed_stopped=True)
    assert result.verified and result.consecutive_stop_samples == 3
    for drive in drives.values():
        assert drive.get_fault.call_count == 3
        assert drive.get_status.call_count == 3
        assert drive.get_frequency.call_count == 3
        drive.stop.assert_not_called()
        drive.run_forward.assert_not_called()


def test_requires_operator_confirmation():
    service, drives, _ = make_service()
    with pytest.raises(RuntimeError, match="Operator"):
        service.verify(operator_confirmed_stopped=False)
    for drive in drives.values():
        drive.get_fault.assert_not_called()


@pytest.mark.parametrize("field,value", [("get_fault", 15), ("get_status", 1), ("get_frequency", 0.1), ("get_frequency", float("nan"))])
def test_rejects_nonstopped_or_faulted_drive(field, value):
    service, drives, _ = make_service()
    getattr(drives[2], field).return_value = value
    with pytest.raises(RuntimeError):
        service.verify(operator_confirmed_stopped=True)


def test_rejects_missing_drive():
    service, _, _ = make_service()
    del service.drive_service.drives[3]
    with pytest.raises(RuntimeError, match="three GAIN"):
        service.verify(operator_confirmed_stopped=True)


def test_rejects_active_calibration():
    service, drives, calibration = make_service()
    calibration.active = True
    with pytest.raises(RuntimeError, match="CALIBRATION"):
        service.verify(operator_confirmed_stopped=True)
    for drive in drives.values():
        drive.get_fault.assert_not_called()


def test_rejects_telemetry_failure():
    service, drives, _ = make_service()
    drives[1].get_fault.side_effect = OSError("RS485 disconnected")
    with pytest.raises(RuntimeError, match="telemetry unavailable"):
        service.verify(operator_confirmed_stopped=True)
