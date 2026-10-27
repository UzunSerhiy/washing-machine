"""Step 31G: API diagnostics agree on the software motion latch (mock hardware)."""
from types import SimpleNamespace

import app.main as main
from app.api import machine as api


class StoppedDrive:
    def get_fault(self): return 0
    def get_status(self): return 3
    def get_frequency(self): return 0.0


class OfflineDrive(StoppedDrive):
    def get_fault(self): raise TimeoutError("RS485 timeout")


def _configure(monkeypatch, *, reason, drive=None, runtime=None):
    monkeypatch.setattr(main, "machine", SimpleNamespace(motion_fault_latched=reason))
    monkeypatch.setattr(main, "motion_fault_runtime", runtime)
    service = SimpleNamespace(
        configs={1: SimpleNamespace(enabled=True, name="Roller", type="ROLLER")},
        drives={1: drive or StoppedDrive()},
    )
    monkeypatch.setattr(api, "get_drive_service", lambda: service)
    monkeypatch.setattr(api, "get_roller_homing_service", lambda: SimpleNamespace(get_status=lambda: {"faulted": False}))
    return service


def test_api_readiness_and_fault_diagnostics_agree_on_latch(monkeypatch):
    _configure(monkeypatch, reason="RS485 timeout")
    readiness = api.get_machine_readiness()
    fault = api.get_motion_fault_diagnostics()
    assert fault["latched"] is True
    assert fault["reason"] == "RS485 timeout"
    assert readiness["ready"] is False
    assert "MOTION_FAULT_LATCHED" in readiness["reasons"]
    assert readiness["diagnostic_only"] and fault["diagnostic_only"]


def test_stopped_drives_do_not_override_latched_fault(monkeypatch):
    _configure(monkeypatch, reason="E15")
    result = api.get_machine_readiness()
    assert result["drives"][0]["ready"] is True
    assert result["ready"] is False
    assert "MOTION_FAULT_LATCHED" in result["reasons"]


def test_rs485_telemetry_timeout_is_not_reported_ready(monkeypatch):
    _configure(monkeypatch, reason="RS485 timeout", drive=OfflineDrive())
    result = api.get_machine_readiness()
    assert result["ready"] is False
    assert result["drives"][0]["connected"] is False
    assert "drive_1:VFD_TELEMETRY_UNAVAILABLE" in result["reasons"]
    assert "MOTION_FAULT_LATCHED" in result["reasons"]


def test_monitor_not_running_does_not_hide_latched_fault(monkeypatch):
    _configure(monkeypatch, reason="E15", runtime=SimpleNamespace(
        running=False, last_poll_error="monitor offline", last_fault="E15"
    ))
    fault = api.get_motion_fault_diagnostics()
    assert fault["latched"] is True
    assert fault["monitor_running"] is False
    assert fault["last_poll_error"] == "monitor offline"
    assert api.get_machine_readiness()["ready"] is False
