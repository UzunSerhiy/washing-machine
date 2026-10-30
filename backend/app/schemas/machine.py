from pydantic import BaseModel
from app.services.machine.operation import AutoStage, OperationMode
from app.services.machine.calibration.points import CalibrationPoint
from app.services.machine.calibration.stage import CalibrationStage


class MachineDriveResponse(BaseModel):
    id: int
    name: str
    address: int
    type: str
    position: str | None
    enabled: bool

    status: int
    frequency_hz: float
    fault: int


class MachineResponse(BaseModel):
    id: int
    name: str
    description: str | None
    is_active: bool
    drives: list[MachineDriveResponse]


class MachineOperationResponse(BaseModel):
    mode: OperationMode
    auto_stage: AutoStage | None
    material_profile_id: int | None

    roller_speed_percent: float | None
    brush_speed_percent: float | None

    roller_running: bool
    brush_running: bool

    running: bool
    paused: bool


class ManualSpeedRequest(BaseModel):
    speed_percent: float


class MaterialModeRequest(BaseModel):
    material_profile_id: int


class CalibrationStartRequest(BaseModel):
    material_profile_id: int


class CalibrationSessionResponse(BaseModel):
    active: bool
    material_profile_id: int | None = None
    stage: CalibrationStage | None = None

    position_turns: float = 0.0
    running: bool = False
    paused: bool = False
    direction: str | None = None
    frequency_hz: float | None = None

    brush_running: bool = False
    brush_frequency_hz: float | None = None

    washing_stop_turns: float | None = None
    material_start_turns: float | None = None
    material_end_turns: float | None = None
    saved: bool = False
    auto_mode: str | None = None
    water_start_turns: float | None = None
    editing: bool = False
    edit_target: str | None = None
    edit_adjusting: bool = False


class CalibrationNextRequest(BaseModel):
    roller_frequency_hz: float
    brush_frequency_hz: float


class CalibrationJogRequest(BaseModel):
    frequency_hz: float
    brush_frequency_hz: float | None = None


class CalibrationMarkRequest(BaseModel):
    point: CalibrationPoint
    brush_frequency_hz: float | None = None


class AutoSpeedSettingsResponse(BaseModel):
    stage: AutoStage
    speed_percent: float
    brush_speed_percent: float | None


class AutoSpeedRequest(BaseModel):
    speed_percent: float
