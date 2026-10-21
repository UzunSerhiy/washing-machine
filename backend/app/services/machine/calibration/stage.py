from enum import Enum


class CalibrationStage(str, Enum):
    SET_ZERO = "set_zero"
    MATERIAL_START = "material_start"
    MATERIAL_END = "material_end"
    READY_TO_UNWIND = "ready_to_unwind"
