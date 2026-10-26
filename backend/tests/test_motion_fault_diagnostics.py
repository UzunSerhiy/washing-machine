from types import SimpleNamespace

from fastapi import HTTPException
import pytest

from app.api.machine import get_motion_fault_diagnostics
import app.main as main


def test_motion_fault_diagnostics_latched(monkeypatch):
    monkeypatch.setattr(main, "machine", SimpleNamespace(motion_fault_latched="roller: fault 15"))
    monkeypatch.setattr(main, "motion_fault_runtime", SimpleNamespace(running=True, last_poll_error=None, last_fault="roller: fault 15"))
    result = get_motion_fault_diagnostics()
    assert result["latched"] is True
    assert result["reason"] == "roller: fault 15"
    assert result["recovery_available"] is False
    assert result["diagnostic_only"] is True


def test_motion_fault_diagnostics_clear(monkeypatch):
    monkeypatch.setattr(main, "machine", SimpleNamespace(motion_fault_latched=None))
    monkeypatch.setattr(main, "motion_fault_runtime", None)
    result = get_motion_fault_diagnostics()
    assert result["latched"] is False
    assert result["monitor_running"] is False


def test_motion_fault_diagnostics_uninitialized(monkeypatch):
    monkeypatch.setattr(main, "machine", None)
    with pytest.raises(HTTPException) as exc:
        get_motion_fault_diagnostics()
    assert exc.value.status_code == 503
