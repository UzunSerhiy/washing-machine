from app.services.machine.operation import AutoStage


class AutoStageConfig:
    _MODE_CODES = {
        AutoStage.WINDING: "winding",
        AutoStage.WASHING: "washing",
        AutoStage.DRYING: "drying",
        AutoStage.UNWINDING: "unwinding",
    }

    def __init__(self, stage: AutoStage):
        self.stage = stage

    @property
    def machine_mode_code(self) -> str:
        return self._MODE_CODES[self.stage]
