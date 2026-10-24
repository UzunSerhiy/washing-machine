import pytest

from app.services.speed.layer import SpeedLayer
from app.services.winding.calculator import WindingCalculator
from app.services.speed.settings import RuntimeSpeedSettings
from app.services.speed.context import SpeedContext


def test_belt_frequency():
    layer = SpeedLayer(max_frequency_hz=50)

    assert layer.belt_frequency(100) == 50
    assert layer.belt_frequency(70) == 35
    assert layer.belt_frequency(30) == 15


def test_brush_frequency():
    layer = SpeedLayer(max_frequency_hz=50)

    assert layer.brush_frequency(100) == 50
    assert layer.brush_frequency(90) == 45
    assert layer.brush_frequency(30) == 15


def test_material_frequency_uses_winding_curve():
    layer = SpeedLayer(max_frequency_hz=50)

    calculator = WindingCalculator(
        core_diameter_mm=100,
        material_thickness_mm=1,
    )

    assert layer.material_frequency(calculator, 100) == calculator.frequency_hz(100)
    assert layer.material_frequency(calculator, 70) == calculator.frequency_hz(70)


@pytest.mark.parametrize("speed_percent", [0, -1, 101])
def test_invalid_belt_speed_percent(speed_percent):
    layer = SpeedLayer()

    with pytest.raises(ValueError):
        layer.belt_frequency(speed_percent)


@pytest.mark.parametrize("speed_percent", [0, -1, 101])
def test_invalid_brush_speed_percent(speed_percent):
    layer = SpeedLayer()

    with pytest.raises(ValueError):
        layer.brush_frequency(speed_percent)


@pytest.mark.parametrize("speed_percent", [0, -1, 101])
def test_invalid_material_speed_percent(speed_percent):
    layer = SpeedLayer()

    calculator = WindingCalculator(
        core_diameter_mm=100,
        material_thickness_mm=1,
    )

    with pytest.raises(ValueError):
        layer.material_frequency(calculator, speed_percent)


def test_invalid_max_frequency():
    with pytest.raises(ValueError):
        SpeedLayer(max_frequency_hz=0)


def test_calculate_speed_values():
    layer = SpeedLayer(max_frequency_hz=50)

    settings = RuntimeSpeedSettings(
        belt_speed_percent=70,
        material_speed_percent=60,
        brush_speed_percent=90,
    )

    calculator = WindingCalculator(
        core_diameter_mm=100,
        material_thickness_mm=1,
    )

    context = SpeedContext(
        settings=settings,
        winding_calculator=calculator,
    )

    values = layer.calculate(context)

    assert values.belt_frequency_hz == 35
    assert values.brush_frequency_hz == 45
    assert values.material_frequency_hz == calculator.frequency_hz(60)


def test_calculate_without_brush():
    layer = SpeedLayer(max_frequency_hz=50)

    settings = RuntimeSpeedSettings(
        belt_speed_percent=80,
        material_speed_percent=75,
        brush_speed_percent=None,
    )

    calculator = WindingCalculator(
        core_diameter_mm=100,
        material_thickness_mm=1,
    )

    context = SpeedContext(
        settings=settings,
        winding_calculator=calculator,
    )

    values = layer.calculate(context)

    assert values.belt_frequency_hz == 40
    assert values.material_frequency_hz == calculator.frequency_hz(75)
    assert values.brush_frequency_hz is None
