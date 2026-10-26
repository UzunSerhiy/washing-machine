import pytest

from app.services.drives.gain import GainDrive


class StubModbus:
    def __init__(self, fault=0):
        self.fault = fault
        self.writes = []

    def read_register(self, *, address, device_id):
        assert address == GainDrive.REG_FAULT
        assert device_id == 1
        if isinstance(self.fault, Exception):
            raise self.fault
        return self.fault

    def write_register(self, *, address, value, device_id):
        self.writes.append((address, value, device_id))


@pytest.mark.parametrize("command", ["run_forward", "run_reverse"])
@pytest.mark.parametrize("fault", [15, 2, -1, None, True, RuntimeError("offline")])
def test_start_blocked_on_fault_or_unavailable_telemetry(command, fault):
    client = StubModbus(fault)
    drive = GainDrive(client, 1)
    with pytest.raises(RuntimeError, match="cannot start"):
        getattr(drive, command)()
    assert client.writes == []


@pytest.mark.parametrize("command,code", [
    ("run_forward", GainDrive.CMD_FORWARD),
    ("run_reverse", GainDrive.CMD_REVERSE),
])
def test_start_allowed_when_fault_zero(command, code):
    client = StubModbus(0)
    getattr(GainDrive(client, 1), command)()
    assert client.writes == [(GainDrive.REG_COMMAND, code, 1)]


def test_stop_allowed_even_when_fault_active():
    client = StubModbus(15)
    GainDrive(client, 1).stop()
    assert client.writes == [(GainDrive.REG_COMMAND, GainDrive.CMD_DECEL_STOP, 1)]


def test_no_automatic_fault_reset():
    client = StubModbus(15)
    with pytest.raises(RuntimeError):
        GainDrive(client, 1).run_forward()
    assert all(value != GainDrive.CMD_FAULT_RESET for _, value, _ in client.writes)
