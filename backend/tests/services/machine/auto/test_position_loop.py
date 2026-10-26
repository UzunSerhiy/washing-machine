import pytest

from app.services.machine.auto.position_loop import AutoPositionLoop, AppliedRollerMotion
from app.services.machine.auto.stage_controller import AutoStageController
from app.services.machine.auto.trajectory_plan import AutoGeometry
from app.services.machine.operation import AutoStage
from app.services.machine.position.roller_position_service import RollerPositionService
from app.services.machine.sensors.roller_reference import RollerReferenceState
from app.services.speed.layer import SpeedLayer
from app.services.winding.rotation import RollerRotationCalculator


def sensor(pulses=0, *, triggered=False, connected=True):
    return RollerReferenceState(connected, triggered, pulses, pulses, 1)


class Curve:
    def __init__(self):
        self.turns = 0
    def set_turns(self, turns):
        self.turns = turns
    def frequency_hz(self, percent):
        return percent / 2 - self.turns


def make_loop():
    rotation = RollerRotationCalculator(905, 100)
    position = RollerPositionService(rotation)
    position.home(sensor(triggered=True))
    geometry = AutoGeometry(0.5, 2, 3, 5)
    stage = AutoStageController(AutoStage.WINDING, geometry, 80, 0, Curve(), rotation, SpeedLayer())
    return AutoPositionLoop(position, stage)


def test_variable_frequency_accumulates_each_interval_once():
    loop = make_loop()
    first = loop.tick(elapsed_seconds=1, applied_frequency_hz=40, applied_direction=1, sensor=sensor())
    second = loop.tick(elapsed_seconds=1, applied_frequency_hz=20, applied_direction=1, sensor=sensor())
    expected = 9.05 * (40 / 50 + 20 / 50) / 60
    assert second.position.position_turns == pytest.approx(expected)
    assert loop.stage.position_turns == pytest.approx(expected)
    assert second.next_frequency_hz == pytest.approx(40)
    assert first.position.position_turns < second.position.position_turns


def test_pulse_correction_propagates_to_stage():
    loop = make_loop()
    result = loop.tick(elapsed_seconds=6.63, applied_frequency_hz=50, applied_direction=1, sensor=sensor(1))
    assert result.position.position_turns == 1
    assert loop.stage.position_turns == 1


def test_disconnect_fails_closed():
    loop = make_loop()
    with pytest.raises(RuntimeError, match="HOME required"):
        loop.tick(elapsed_seconds=1, applied_frequency_hz=20, applied_direction=1,
                  sensor=sensor(connected=False))
    assert not loop.position.snapshot.valid


def test_requires_home():
    rotation = RollerRotationCalculator(905, 100)
    position = RollerPositionService(rotation)
    stage = AutoStageController(AutoStage.WINDING, AutoGeometry(.5, 2, 3, 5),
                                80, 0, Curve(), rotation, SpeedLayer())
    with pytest.raises(RuntimeError, match="HOME"):
        AutoPositionLoop(position, stage)


def test_out_of_bounds_position_invalidates_home():
    loop = make_loop()
    with pytest.raises(ValueError, match="outside calibrated travel"):
        loop.tick(elapsed_seconds=40, applied_frequency_hz=50,
                  applied_direction=1, sensor=sensor())
    assert not loop.position.snapshot.valid
    with pytest.raises(RuntimeError, match="HOME required"):
        loop.tick(elapsed_seconds=0, applied_frequency_hz=0,
                  applied_direction=0, sensor=sensor())


def test_movement_after_completion_invalidates_home():
    loop = make_loop()
    loop.tick(elapsed_seconds=0, applied_frequency_hz=50,
              applied_direction=1, sensor=sensor(5))
    assert loop.stage.completed
    with pytest.raises(ValueError, match="outside calibrated travel"):
        loop.tick(elapsed_seconds=1, applied_frequency_hz=20,
                  applied_direction=1, sensor=sensor(5))
    assert not loop.position.snapshot.valid


def test_applied_motion_sample_uses_actual_frequency_and_direction():
    loop = make_loop()
    result = loop.tick_applied_motion(AppliedRollerMotion(
        elapsed_seconds=1, frequency_hz=25, direction=1, sensor=sensor(),
    ))
    assert result.position.position_turns == pytest.approx(9.05 * .5 / 60)
    assert loop.stage.position_turns == pytest.approx(result.position.position_turns)


def test_applied_motion_stopped_interval_does_not_move():
    loop = make_loop()
    result = loop.tick_applied_motion(AppliedRollerMotion(
        elapsed_seconds=1, frequency_hz=0, direction=0, sensor=sensor(),
    ))
    assert result.position.position_turns == 0


def test_applied_motion_rejects_invalid_direction():
    loop = make_loop()
    with pytest.raises(ValueError, match="direction"):
        loop.tick_applied_motion(AppliedRollerMotion(
            elapsed_seconds=1, frequency_hz=20, direction=2, sensor=sensor(),
        ))
