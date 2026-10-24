import pytest

from app.services.machine.auto.trajectory_plan import (
    AutoGeometry, frequency_at_position, stage_plan, water_required,
)
from app.services.machine.operation import AutoStage
from app.services.speed.layer import SpeedLayer
from app.services.winding.calculator import WindingCalculator


@pytest.fixture
def geometry():
    return AutoGeometry(1, 3, 7, 12)


@pytest.mark.parametrize('stage,start,stop,direction', [
    (AutoStage.WINDING, 0, 12, 1),
    (AutoStage.WASHING, 12, 1, -1),
    (AutoStage.DRYING, 1, 12, 1),
    (AutoStage.UNWINDING, 12, 0, -1),
])
def test_stage_bounds(geometry, stage, start, stop, direction):
    plan = stage_plan(stage, geometry)
    assert (plan.start_turns, plan.stop_turns, plan.direction) == (start, stop, direction)
    assert plan.reached_end(stop)
    assert not plan.reached_end((start + stop) / 2)


def test_operator_frequency_outside_material_and_continuity(geometry):
    calc = WindingCalculator(core_diameter_mm=140, material_thickness_mm=1)
    layer = SpeedLayer()
    at = lambda x, pct=60: frequency_at_position(x, pct, geometry, calc, layer)
    assert at(0) == at(1) == at(3) == pytest.approx(30)
    assert at(3.000001) == pytest.approx(30, abs=0.0001)
    assert at(12) < at(7) < at(3)
    assert at(12, 30) == pytest.approx(at(12, 60) / 2)


def test_water_windows(geometry):
    assert water_required(AutoStage.WASHING, 12, geometry)
    assert not water_required(AutoStage.WASHING, 1, geometry)
    assert water_required(AutoStage.DRYING, 1, geometry)
    assert water_required(AutoStage.DRYING, 6.9, geometry)
    assert not water_required(AutoStage.DRYING, 7, geometry)
    for stage in (AutoStage.WINDING, AutoStage.UNWINDING):
        assert not water_required(stage, 5, geometry)


def test_invalid_geometry(geometry):
    with pytest.raises(ValueError):
        AutoGeometry(3, 3, 7, 12)
    with pytest.raises(ValueError):
        AutoGeometry(1, 3, 12, 12)
