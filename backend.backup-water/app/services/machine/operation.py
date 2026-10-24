from enum import Enum


class OperationMode(str, Enum):
    MANUAL = "manual"
    AUTO = "auto"
    CALIBRATION = "calibration"


class AutoStage(str, Enum):
    WINDING = "winding"
    WASHING = "washing"
    DRYING = "drying"
    UNWINDING = "unwinding"
