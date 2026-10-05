import pytest

from app.services.machine.operation import AutoStage
from app.services.machine.auto_stage import AutoStageConfig


@pytest.mark.parametrize(
    ("stage", "expected_mode_code"),
    [
        (AutoStage.WINDING, "winding"),
        (AutoStage.WASHING, "washing"),
        (AutoStage.DRYING, "drying"),
        (AutoStage.UNWINDING, "unwinding"),
    ],
)
def test_auto_stage_maps_to_machine_mode(
    stage: AutoStage,
    expected_mode_code: str,
) -> None:
    config = AutoStageConfig(stage)

    assert config.machine_mode_code == expected_mode_code


def test_each_auto_stage_has_its_own_mode_code() -> None:
    codes = {AutoStageConfig(stage).machine_mode_code for stage in AutoStage}

    assert len(codes) == len(AutoStage)
