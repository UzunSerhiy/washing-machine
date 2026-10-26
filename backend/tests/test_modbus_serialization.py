"""Step 29B: one physical RS-485 client must not run parallel transactions."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event, Lock
from time import sleep
from unittest.mock import patch

import pytest

from app.services.modbus.client import ModbusClient


class Response:
    registers = [1234]

    def isError(self):
        return False


class TrackingSerial:
    def __init__(self, **kwargs):
        self.guard = Lock()
        self.active = 0
        self.peak = 0
        self.calls = []
        self.entered = Event()

    def _transaction(self, name):
        with self.guard:
            self.active += 1
            self.peak = max(self.peak, self.active)
        self.entered.set()
        sleep(0.003)
        with self.guard:
            self.calls.append(name)
            self.active -= 1
        return Response()

    def read_holding_registers(self, *, address, count, device_id):
        return self._transaction(("read", device_id, address))

    def write_register(self, *, address, value, device_id):
        return self._transaction(("write", device_id, address))

    def connect(self):
        self._transaction(("connect",))
        return True

    def close(self):
        self._transaction(("close",))


def make_client():
    with patch("app.services.modbus.client.ModbusSerialClient", TrackingSerial):
        return ModbusClient(port="/dev/not-a-real-device")


def test_parallel_reads_and_writes_share_single_serial_transaction():
    client = make_client()

    def operation(index):
        if index % 2:
            client.write_register(address=0x1000, value=index, device_id=index % 3 + 1)
        else:
            assert client.read_register(address=0x3000, device_id=index % 3 + 1) == 1234

    with ThreadPoolExecutor(max_workers=12) as pool:
        list(pool.map(operation, range(60)))

    assert client.client.peak == 1
    assert len(client.client.calls) == 60


def test_connect_and_close_use_same_lock_as_transactions():
    client = make_client()
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [
            pool.submit(client.read_register, 0x3000, 1),
            pool.submit(client.connect),
            pool.submit(client.write_register, 0x1000, 100, 2),
            pool.submit(client.close),
        ]
        for future in futures:
            future.result()
    assert client.client.peak == 1


def test_failed_modbus_call_releases_lock():
    client = make_client()
    original = client.client.read_holding_registers

    def failing_read(**kwargs):
        raise OSError("simulated RS-485 disconnect")

    client.client.read_holding_registers = failing_read
    with pytest.raises(OSError, match="disconnect"):
        client.read_register(0x3000, 1)
    client.client.read_holding_registers = original
    assert client.read_register(0x3000, 1) == 1234
