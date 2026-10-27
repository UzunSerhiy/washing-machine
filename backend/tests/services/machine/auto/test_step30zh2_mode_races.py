"""Software-only AUTO/mode interleaving tests. Never talk to VFDs."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.services.machine.auto.session_service import AutoSessionService
from app.services.machine.operation_service import MachineOperationService
from app.services.machine.operation import OperationMode, AutoStage


class FakeMachine:
    def __init__(self):
        self.calls = []

    def stop_all(self):
        self.calls.append("STOP")

    def require_session_generation(self, generation):
        assert generation == 0


def test_auto_tick_finishes_before_mode_stop():
    machine = FakeMachine()
    op = MachineOperationService(machine)
    op.set_auto_mode(1)
    entered, release = Event(), Event()
    controller = Mock()
    controller.completed = False
    def update(**kwargs):
        entered.set()
        assert release.wait(3)
    controller.update.side_effect = update
    controller.apply.side_effect = lambda **kwargs: machine.calls.append("RUN")
    auto = AutoSessionService.__new__(AutoSessionService)
    auto.operation_service = op
    auto._prepared = SimpleNamespace(stage=AutoStage.WINDING, material_profile_id=1,
                                      mode_speed_percent=50, controller=controller)
    auto._session_generation = 0
    auto._faulted = False
    auto._position_loop = None
    auto.speed_layer = Mock()
    auto.speed_layer.belt_frequency.return_value = 20
    op.state.running = True
    with ThreadPoolExecutor(max_workers=2) as pool:
        tick = pool.submit(auto.tick)
        assert entered.wait(3)
        switch = pool.submit(op.set_manual_mode)
        assert not switch.done()
        release.set()
        tick.result(timeout=3)
        switch.result(timeout=3)
    assert machine.calls == ["STOP", "RUN", "STOP"]
    assert op.state.mode == OperationMode.MANUAL


def test_auto_old_tick_after_switch_does_not_dispatch():
    machine = FakeMachine()
    op = MachineOperationService(machine)
    op.set_auto_mode(1)
    controller = Mock()
    controller.completed = False
    auto = AutoSessionService.__new__(AutoSessionService)
    auto.operation_service = op
    auto._prepared = SimpleNamespace(stage=AutoStage.WINDING, material_profile_id=1,
                                      mode_speed_percent=50, controller=controller)
    auto._session_generation = 0
    auto._faulted = False
    auto._position_loop = None
    auto.speed_layer = Mock()
    op.state.running = True
    op.set_manual_mode()
    with pytest.raises(RuntimeError, match="AUTO mode"):
        auto.tick()
    controller.apply.assert_not_called()
