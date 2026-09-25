from enum import Enum


class CalibrationPoint(str, Enum):
    WINDING_BELT_START = "winding_belt_start"
    WINDING_MATERIAL_WOUND = "winding_material_wound"

    WASHING_MATERIAL_REACHES_BRUSHES = "washing_material_reaches_brushes"

    WASHING_MATERIAL_END = "washing_material_end"
    WASHING_BELT_SAFE = "washing_belt_safe"
