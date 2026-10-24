from dataclasses import dataclass

from app.services.speed.settings import RuntimeSpeedSettings
from app.services.winding.calculator import WindingCalculator


@dataclass
class SpeedContext:
    settings: RuntimeSpeedSettings
    winding_calculator: WindingCalculator
