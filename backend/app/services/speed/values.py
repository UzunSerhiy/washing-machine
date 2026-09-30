from dataclasses import dataclass


@dataclass(frozen=True)
class SpeedValues:
    belt_frequency_hz: float
    material_frequency_hz: float
    brush_frequency_hz: float | None
