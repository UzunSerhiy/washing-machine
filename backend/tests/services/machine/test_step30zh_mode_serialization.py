"""Deterministic software-only interleaving tests; no VFD communication."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event

from app.services.machine.operation import OperationMode
from app.services.machine.operation_service import MachineOperationService


class BlockingMachine:
    def __init__(self):
        self.entered = Event()
        self.release = Event()
        self.calls = []

    def start_roller_forward(self, frequency_hz):
        self.entered.set()
        assert self.release.wait(3), "test dispatch did not release"
        self.calls.append("RUN")

    def start_brush(self, frequency_hz):
        self.entered.set()
        assert self.release.wait(3), "test dispatch did not release"
        self.calls.append("BRUSH_RUN")

    def stop_all(self):
        self.calls.append("STOP_ALL")


def _exercise(start_name, speed_name, expected):
    machine = BlockingMachine()
    service = MachineOperationService(machine)
    getattr(service, speed_name)(50)
    with ThreadPoolExecutor(max_workers=2) as pool:
        run = pool.submit(getattr(service, start_name))
        assert machine.entered.wait(3)
        switch = pool.submit(service.set_auto_mode, 1)
        # Switching cannot finish while a manual dispatch is in progress.
        assert not switch.done()
        machine.release.set()
        run.result(timeout=3)
        switch.result(timeout=3)
    assert machine.calls == [expected, "STOP_ALL"]
    assert service.state.mode == OperationMode.AUTO
    assert not service.state.roller_running
    assert not service.state.brush_running


def test_mode_change_waits_for_manual_roller_dispatch():
    _exercise("start_manual_roller_forward", "set_manual_roller_speed", "RUN")


def test_mode_change_waits_for_manual_brush_dispatch():
    _exercise("start_manual_brush", "set_manual_brush_speed", "BRUSH_RUN")
