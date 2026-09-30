from app.services.speed.context import SpeedContext
from app.services.speed.settings import RuntimeSpeedSettings
from app.services.winding.calculator import WindingCalculator


def test_speed_context():
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

    assert context.settings is settings
    assert context.winding_calculator is calculator
