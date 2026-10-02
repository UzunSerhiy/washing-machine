from dataclasses import dataclass

from app.services.machine.operation import AutoStage, OperationMode


@dataclass
class MachineOperationState:
    mode: OperationMode = OperationMode.MANUAL
    auto_stage: AutoStage | None = None
    material_profile_id: int | None = None

    roller_speed_percent: float | None = None
    brush_speed_percent: float | None = None

    roller_running: bool = False
    brush_running: bool = False

    running: bool = False
    paused: bool = False
