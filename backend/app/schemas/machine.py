from pydantic import BaseModel


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
