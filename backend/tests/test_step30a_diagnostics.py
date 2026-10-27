from types import SimpleNamespace

from app.services.machine.readiness_diagnostics import get_readiness_snapshot
from app.api import machine as api
import app.main as main


class Drive:
    def get_fault(self): return 0
    def get_status(self): return 3
    def get_frequency(self): return 0.0


def test_latch_overrides_good_telemetry():
    svc = SimpleNamespace(configs={1: SimpleNamespace(enabled=True, name="Brush Left", type="BRUSH")}, drives={1: Drive()})
    home = SimpleNamespace(get_status=lambda: {"faulted": False})
    result = get_readiness_snapshot(svc, home, "backend restarted")
    assert result["ready"] is False
    assert result["drives"][0]["ready"] is True
    assert "MOTION_FAULT_LATCHED" in result["reasons"]


def test_no_latch_keeps_readiness():
    svc = SimpleNamespace(configs={1: SimpleNamespace(enabled=True, name="Brush Left", type="BRUSH")}, drives={1: Drive()})
    home = SimpleNamespace(get_status=lambda: {"faulted": False})
    assert get_readiness_snapshot(svc, home)["ready"] is True


def test_recovery_availability_means_endpoint_only(monkeypatch):
    monkeypatch.setattr(main, "machine", SimpleNamespace(motion_fault_latched="startup"))
    monkeypatch.setattr(main, "motion_fault_runtime", SimpleNamespace(running=True, last_poll_error=None, last_fault=None))
    for name in ("auto_session_service", "calibration_session_service", "roller_homing_service"):
        monkeypatch.setattr(main, name, object())
    monkeypatch.setattr(api.settings, "DRIVE_MODE", "real")
    result = api.get_motion_fault_diagnostics()
    assert result["recovery_available"] is True
    assert "physical RESET" in result["recovery_note"]
    assert result["latched"] is True


def test_recovery_unavailable_in_fake_mode(monkeypatch):
    monkeypatch.setattr(main, "machine", SimpleNamespace(motion_fault_latched="startup"))
    monkeypatch.setattr(main, "motion_fault_runtime", SimpleNamespace(running=False, last_poll_error=None, last_fault=None))
    monkeypatch.setattr(api.settings, "DRIVE_MODE", "fake")
    assert api.get_motion_fault_diagnostics()["recovery_available"] is False
