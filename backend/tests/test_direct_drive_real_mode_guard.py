"""Direct drive write routes must not bypass the Machine latch in REAL mode."""
import pytest
from fastapi import HTTPException

from app.api import drives as api


@pytest.mark.parametrize("drive_id", [1, 2, 3])
def test_direct_access_rejected_before_service_lookup_in_real_mode(monkeypatch, drive_id):
    monkeypatch.setattr("app.core.config.settings.DRIVE_MODE", "real")
    monkeypatch.setattr(api, "get_drive_service", lambda: pytest.fail("Drive service accessed"))
    with pytest.raises(HTTPException) as error:
        api.require_direct_drive_access(drive_id)
    assert error.value.status_code == 409


def test_fake_mode_keeps_existing_direct_brush_behavior(monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr("app.core.config.settings.DRIVE_MODE", "fake")
    service = SimpleNamespace(configs={1: SimpleNamespace(type="BRUSH")})
    monkeypatch.setattr(api, "get_drive_service", lambda: service)
    assert api.require_direct_drive_access(1) is None


def test_fake_mode_still_blocks_direct_roller(monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr("app.core.config.settings.DRIVE_MODE", "fake")
    service = SimpleNamespace(configs={3: SimpleNamespace(type="ROLLER")})
    monkeypatch.setattr(api, "get_drive_service", lambda: service)
    with pytest.raises(HTTPException) as error:
        api.require_direct_drive_access(3)
    assert error.value.status_code == 409
