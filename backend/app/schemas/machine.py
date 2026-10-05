from pydantic import BaseModel
from app.services.machine.operation import AutoStage, OperationMode
from app.services.machine.calibration.points import CalibrationPoint


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
    material_profile_id: int
    position_turns: float
    running: bool
    paused: bool
    direction: str | None
    frequency_hz: float | None


class CalibrationJogRequest(BaseModel):
    frequency_hz: float


class CalibrationMarkRequest(BaseModel):
    point: CalibrationPoint


class AutoSpeedSettingsResponse(BaseModel):
    stage: AutoStage
    speed_percent: float
    brush_speed_percent: float | None


class AutoSpeedRequest(BaseModel):
    speed_percent: float
