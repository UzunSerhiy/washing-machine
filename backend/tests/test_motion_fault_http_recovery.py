"""Step 29ZH: ASGI HTTP recovery contract with simulated GAIN; no hardware."""
import asyncio
import json
from threading import RLock
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.services.machine.motion_fault_runtime import MotionFaultRuntime


class FakeMachine:
    def __init__(self):
        self._roller_lock = RLock()
        self.motion_fault_latched = "E15"
        self._roller_stop_fault = False
        self._external_stop_pending = 0
        self.roller_owner = None
        self.clears = 0

    def complete_motion_fault_recovery(self):
        self.clears += 1
        self.motion_fault_latched = None


async def post_json(app, path, payload):
    """Exercise the actual FastAPI ASGI HTTP route without httpx or lifespan."""
    body = json.dumps(payload).encode()
    sent = []
    consumed = False

    async def receive():
        nonlocal consumed
        if not consumed:
            consumed = True
            return {"type": "http.request", "body": body, "more_body": False}
        return {"type": "http.disconnect"}

    async def send(message):
        sent.append(message)

    await app({"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
               "method": "POST", "scheme": "http", "path": path, "raw_path": path.encode(),
               "query_string": b"", "root_path": "", "headers": [
                   (b"content-type", b"application/json"),
                   (b"content-length", str(len(body)).encode()),
               ], "client": ("test", 1234), "server": ("test", 80)}, receive, send)
    status = next(m["status"] for m in sent if m["type"] == "http.response.start")
    response = b"".join(m.get("body", b"") for m in sent if m["type"] == "http.response.body")
    return status, json.loads(response)


@pytest.fixture
def rig(monkeypatch):
    import app.main as main
    import app.api.machine as api

    machine = FakeMachine()
    drives = {i: Mock() for i in (1, 2, 3)}
    for drive in drives.values():
        drive.get_fault.return_value = 0
        drive.get_status.return_value = 3
        drive.get_frequency.return_value = 0.0
    drive_service = SimpleNamespace(drives=drives, configs={i: SimpleNamespace(enabled=True) for i in drives})
    auto = Mock()
    auto.get_status.return_value = {"status": "FAULT", "running": False, "paused": False}
    auto._prepared = None
    calibration = Mock()
    calibration.active = False
    calibration.auto_mode = None
    home = Mock()
    home.OWNER = "homing"
    home.get_status.return_value = {"state": "FAULT", "searching": False, "awaiting_stop": False}
    runtime = MotionFaultRuntime(machine)
    runtime._notified = True
    for name, value in {
        "machine": machine, "motion_fault_runtime": runtime, "drive_service": drive_service,
        "auto_session_service": auto, "calibration_session_service": calibration,
        "roller_homing_service": home,
    }.items():
        monkeypatch.setattr(main, name, value)
    monkeypatch.setattr(api.settings, "DRIVE_MODE", "real")
    return SimpleNamespace(app=main.app, machine=machine, drives=drives, auto=auto,
                           calibration=calibration, home=home, runtime=runtime)


def request(rig, confirmed=True):
    return asyncio.run(post_json(rig.app, "/api/machine/motion-fault/acknowledge",
                                 {"operator_confirmed_stopped": confirmed}))


def assert_no_commands(rig):
    for drive in rig.drives.values():
        for method in ("run_forward", "run_reverse", "stop", "set_frequency"):
            getattr(drive, method).assert_not_called()


@pytest.mark.parametrize("failure", ["operator", "e15", "timeout", "moving", "frequency", "prepared", "cleanup"])
def test_http_recovery_failure_keeps_latch(rig, failure):
    if failure == "e15":
        rig.drives[2].get_fault.return_value = 15
    elif failure == "timeout":
        rig.drives[3].get_status.side_effect = OSError("RS485 timeout")
    elif failure == "moving":
        rig.drives[1].get_status.return_value = 1
    elif failure == "frequency":
        rig.drives[2].get_frequency.return_value = 2.0
    elif failure == "prepared":
        rig.auto._prepared = object()
    elif failure == "cleanup":
        rig.home.complete_motion_fault_recovery.side_effect = RuntimeError("cleanup failed")
    status, response = request(rig, confirmed=failure != "operator")
    assert status == 409, response
    assert rig.machine.motion_fault_latched == "E15"
    assert rig.machine.clears == 0
    assert rig.runtime._notified is True
    assert_no_commands(rig)


def test_http_recovery_success_no_restart_and_point0_not_homed(rig):
    status, response = request(rig)
    assert status == 200, response
    assert response == {"acknowledged": True, "drives_verified": [1, 2, 3],
                        "stop_samples": 3, "homed": False, "automatic_restart": False}
    assert rig.machine.motion_fault_latched is None
    assert rig.machine.clears == 1
    assert rig.runtime._notified is False
    rig.home.complete_motion_fault_recovery.assert_called_once()
    assert_no_commands(rig)


def test_http_recovery_rejects_repeat_without_new_fault(rig):
    assert request(rig)[0] == 200
    status, response = request(rig)
    assert status == 409, response
    assert rig.machine.clears == 1
    assert_no_commands(rig)
