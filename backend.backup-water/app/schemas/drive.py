from pydantic import BaseModel, Field


class DriveFrequencyRequest(BaseModel):
    frequency_hz: float = Field(ge=0, le=100)


class DriveResponse(BaseModel):
    id: int
    name: str
    address: int
    type: str
    position: str | None
    enabled: bool

    status: int
    frequency_hz: float
    fault: int
