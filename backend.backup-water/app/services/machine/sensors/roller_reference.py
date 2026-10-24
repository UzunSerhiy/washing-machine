from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class RollerReferenceState:
    connected: bool
    triggered: bool
    pulses: int
    sequence: int
    generation: int = 0


class RollerReferenceSensor(Protocol):
    def read(self) -> RollerReferenceState: ...
