from dataclasses import dataclass

from app.services.machine.operation import AutoStage, OperationMode


@dataclass
class MachineOperationState:
    mode: OperationMode = OperationMode.MANUAL
    auto_stage: AutoStage | None = None
    material_profile_id: int | None = None

    roller_speed_percent: float = 0.0
    brush_speed_percent: float = 0.0

    running: bool = False
    paused: bool = False
