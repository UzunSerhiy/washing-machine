from pydantic import BaseModel, Field


class DriveFrequencyRequest(BaseModel):
    frequency_hz: float = Field(ge=0, le=100)
