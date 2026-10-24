from enum import Enum


class CalibrationStage(str, Enum):
    SET_ZERO = "set_zero"
    MATERIAL_START = "material_start"
    MATERIAL_END = "material_end"
    WATER_START = "water_start"
    WASHING_STOP = "washing_stop"
    READY_TO_UNWIND = "ready_to_unwind"
    REWIND_COMPLETE = "rewind_complete"
