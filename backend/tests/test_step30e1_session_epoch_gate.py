
from unittest.mock import Mock
import pytest
from app.services.machine.brush import Brush
from app.services.machine.roller import Roller
from app.services.machine.machine import Machine


def build():
    drives = [Mock() for _ in range(3)]
    for drive in drives:
        drive.get_fault.return_value = 0
    return Machine(Brush(*drives[:2]), Roller(drives[2]), enforce_motion_preflight=True), drives


@pytest.mark.parametrize("method", ["start_brush", "start_roller_forward", "start_roller_reverse"])
def test_old_session_cannot_dispatch_after_recovery(method):
    machine, drives = build()
    epoch = machine.capture_session_generation()
    machine._motion_fault_latched = "E15"
    machine.complete_motion_fault_recovery()
    with pytest.raises(RuntimeError, match="Stale motion session"):
        getattr(machine, method)(10, session_generation=epoch)
    for drive in drives:
        drive.set_frequency.assert_not_called()
        drive.run_forward.assert_not_called()
        drive.run_reverse.assert_not_called()


@pytest.mark.parametrize("method", ["start_brush", "start_roller_forward", "start_roller_reverse"])
def test_current_session_dispatches(method):
    machine, drives = build()
    epoch = machine.capture_session_generation()
    getattr(machine, method)(10, session_generation=epoch)
    assert any(d.set_frequency.called for d in drives)


def test_cannot_create_session_while_latched():
    machine, _ = build()
    machine._motion_fault_latched = "E15"
    with pytest.raises(RuntimeError, match="Motion fault latched"):
        machine.capture_session_generation()


def test_old_session_rejected_by_validation():
    machine, _ = build()
    epoch = machine.capture_session_generation()
    machine._motion_fault_latched = "E15"
    machine.complete_motion_fault_recovery()
    with pytest.raises(RuntimeError, match="Stale motion session"):
        machine.require_session_generation(epoch)
