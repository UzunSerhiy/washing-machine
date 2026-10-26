from types import SimpleNamespace

from app.services.machine.readiness_diagnostics import get_readiness_snapshot


class Drive:
    def __init__(self, fault=0, status=3, frequency=0.0):
        self.fault, self.status, self.frequency = fault, status, frequency

    def get_fault(self):
        if isinstance(self.fault, Exception):
            raise self.fault
        return self.fault

    def get_status(self):
        return self.status

    def get_frequency(self):
        return self.frequency


class Home:
    def __init__(self, faulted=False):
        self.faulted = faulted

    def get_status(self):
        return {"faulted": self.faulted}


def snapshot(drive=None, home=False):
    service = SimpleNamespace(configs={3: SimpleNamespace(enabled=True, name="Roller", type="ROLLER")},
                              drives={3: drive} if drive else {})
    return get_readiness_snapshot(service, Home(home))


def test_ready():
    assert snapshot(Drive())["ready"] is True


def test_external_fault():
    result = snapshot(Drive(fault=15))
    assert not result["ready"]
    assert "drive_3:VFD_EXTERNAL_FAULT" in result["reasons"]


def test_other_fault():
    assert "drive_3:VFD_FAULT" in snapshot(Drive(fault=7))["reasons"]


def test_unavailable():
    assert "drive_3:VFD_TELEMETRY_UNAVAILABLE" in snapshot(Drive(fault=RuntimeError()))["reasons"]


def test_running():
    assert "drive_3:DRIVE_NOT_STOPPED" in snapshot(Drive(status=1))["reasons"]


def test_nonzero_frequency():
    assert "drive_3:DRIVE_NOT_STOPPED" in snapshot(Drive(frequency=1))["reasons"]


def test_invalid_telemetry():
    assert "drive_3:VFD_TELEMETRY_UNAVAILABLE" in snapshot(Drive(fault=True))["reasons"]


def test_home_fault():
    assert "HOME_FAULT_LATCHED" in snapshot(Drive(), True)["reasons"]


def test_missing_drive():
    assert "drive_3:DRIVE_NOT_CONFIGURED" in snapshot()["reasons"]
