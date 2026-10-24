import pytest
from app.services.machine.auto.stage_controller import AutoStageController
from app.services.machine.auto.trajectory_plan import AutoGeometry
from app.services.machine.operation import AutoStage
from app.services.speed.layer import SpeedLayer
from app.services.winding.calculator import WindingCalculator
from app.services.winding.rotation import RollerRotationCalculator

G = AutoGeometry(1, 3, 7, 12)


def controller(stage, position, speed=60):
    return AutoStageController(stage, G, speed, position,
        WindingCalculator(140, 1), RollerRotationCalculator(3000, 10), SpeedLayer())


@pytest.mark.parametrize('stage,start,stop', [
    (AutoStage.WINDING, 0, 12), (AutoStage.WASHING, 12, 1),
    (AutoStage.DRYING, 1, 12), (AutoStage.UNWINDING, 12, 0),
])
def test_stage_reaches_exact_target(stage, start, stop):
    c = controller(stage, start)
    c.advance(10000)
    assert c.completed
    assert c.position_turns == stop
    old = c.position_turns
    c.advance(10)
    assert c.position_turns == old
    assert not c.water_on


def test_reverse_speed_increases_and_stage_speed_is_independent():
    c = controller(AutoStage.WASHING, 12, 40)
    initial = c.frequency_hz
    assert initial < 20
    c.advance(1)
    assert c.frequency_hz > initial
    c.position_turns = 3
    assert c.frequency_hz == pytest.approx(20)
    c.position_turns = 1.5
    assert c.frequency_hz == pytest.approx(20)
    assert controller(AutoStage.WASHING, 12, 80).frequency_hz == pytest.approx(initial * 2)


def test_water_cutoffs():
    washing = controller(AutoStage.WASHING, 12)
    assert washing.water_on
    washing.position_turns = 1
    assert not washing.water_on
    drying = controller(AutoStage.DRYING, 1)
    assert drying.water_on
    drying.position_turns = 7
    assert not drying.water_on


def test_stage_requires_correct_start():
    with pytest.raises(ValueError):
        controller(AutoStage.DRYING, 0)


def test_no_negative_elapsed():
    with pytest.raises(ValueError):
        controller(AutoStage.WINDING, 0).advance(-1)


@pytest.mark.parametrize('stage,start,near,end', [
    (AutoStage.WINDING, 0, 11.8, 12),
    (AutoStage.WASHING, 12, 1.2, 1),
    (AutoStage.DRYING, 1, 11.8, 12),
    (AutoStage.UNWINDING, 12, 0.2, 0),
])
def test_observed_position_completes_stage(stage, start, near, end):
    c = controller(stage, start)
    c.observe_position(near)
    assert not c.completed
    c.observe_position(end)
    assert c.completed
    assert c.position_turns == end
    with pytest.raises(RuntimeError, match="moved after"):
        c.observe_position(near)


def test_observed_position_controls_water():
    c = controller(AutoStage.DRYING, 1)
    assert c.water_on
    c.observe_position(7)
    assert not c.water_on
    assert not c.completed


def test_observed_position_rejects_invalid_values():
    c = controller(AutoStage.WINDING, 0)
    for value in (-0.1, 12.1, float('nan'), float('inf')):
        with pytest.raises(ValueError):
            c.observe_position(value)
