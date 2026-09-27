from enum import Enum


class CalibrationPoint(str, Enum):
    POINT_0 = "point_0"

    MATERIAL_START = "material_start"
    MATERIAL_END = "material_end"

    WASHING_STOP = "washing_stop"
