"""CALIBRATION motion epoch checks with fake drives only."""
import pytest
from unittest.mock import Mock

from app.services.machine.calibration.session_service import CalibrationSessionService
from app.services.winding.rotation import RollerRotationCalculator


class FakeMachine:
    def __init__(self):
        self.generation = 3
        self.calls = []

    def capture_session_generation(self):
        return self.generation

    def require_session_generation(self, generation):
        if generation != self.generation:
            raise RuntimeError("Stale motion session")

    def start_roller_forward(self, hz, *, session_generation=None):
        self.require_session_generation(session_generation)
        self.calls.append(("forward", hz))

    def start_roller_reverse(self, hz, *, session_generation=None):
        self.require_session_generation(session_generation)
        self.calls.append(("reverse", hz))

    def start_brush(self, hz, *, session_generation=None):
        self.require_session_generation(session_generation)
        self.calls.append(("brush", hz))

    def stop_all(self):
        self.calls.append(("stop",))

    def stop_roller(self):
        self.calls.append(("stop_roller",))


def setup():
    machine = FakeMachine()
    service = CalibrationSessionService(
        machine=machine,
        rotation_calculator=RollerRotationCalculator(motor_rpm_at_50hz=905, gear_ratio=100),
    )
    service.set_roller_homing_service(Mock(searching=False))
    session = service.start(1)
    return service, machine, session


def test_stale_generation_blocks_jog():
    service, machine, _ = setup()
    machine.generation += 1
    with pytest.raises(RuntimeError, match="Stale motion session"):
        service.jog_forward(15)
    assert machine.calls == []


def test_stale_generation_blocks_brush():
    service, machine, _ = setup()
    machine.generation += 1
    with pytest.raises(RuntimeError, match="Stale motion session"):
        service.start_brush(15)
    assert machine.calls == []


def test_stale_generation_blocks_direct_player_dispatch():
    _, machine, session = setup()
    machine.generation += 1
    with pytest.raises(RuntimeError, match="Stale motion session"):
        session.player.start_jog_reverse(15)
    assert machine.calls == []
    assert not session.player.running


def test_stale_tick_cannot_update_position():
    service, machine, session = setup()
    service.jog_forward(15)
    before = session.position_turns
    machine.generation += 1
    with pytest.raises(RuntimeError, match="Stale motion session"):
        service.tick()
    assert session.position_turns == before


def test_fault_recovery_cannot_reuse_calibration_session():
    service, machine, _ = setup()
    service.external_motion_fault("E15")
    machine.generation += 2
    service.complete_motion_fault_recovery()
    with pytest.raises(RuntimeError, match="not active"):
        service.jog_forward(15)
    assert machine.calls == []
