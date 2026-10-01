import pytest

from app.services.machine.operation import AutoStage, OperationMode
from app.services.machine.operation_service import MachineOperationService


def test_auto_stage_navigation() -> None:
    service = MachineOperationService()

    service.set_auto_mode(material_profile_id=1)

    assert service.state.mode == OperationMode.AUTO
    assert service.state.auto_stage == AutoStage.WINDING

    service.next_stage()
    assert service.state.auto_stage == AutoStage.WASHING

    service.next_stage()
    assert service.state.auto_stage == AutoStage.DRYING

    service.next_stage()
    assert service.state.auto_stage == AutoStage.UNWINDING

    service.previous_stage()
    assert service.state.auto_stage == AutoStage.DRYING


def test_cannot_go_before_first_stage() -> None:
    service = MachineOperationService()
    service.set_auto_mode(material_profile_id=1)

    with pytest.raises(RuntimeError, match="Already at the first auto stage"):
        service.previous_stage()


def test_cannot_go_after_last_stage() -> None:
    service = MachineOperationService()
    service.set_auto_mode(material_profile_id=1)

    service.next_stage()
    service.next_stage()
    service.next_stage()

    with pytest.raises(RuntimeError, match="Already at the last auto stage"):
        service.next_stage()


def test_stage_navigation_only_in_auto_mode() -> None:
    service = MachineOperationService()

    with pytest.raises(
        RuntimeError,
        match="Stage navigation is available only in auto mode",
    ):
        service.next_stage()

    service.set_calibration_mode(material_profile_id=1)

    with pytest.raises(
        RuntimeError,
        match="Stage navigation is available only in auto mode",
    ):
        service.next_stage()


def test_set_manual_speeds() -> None:
    service = MachineOperationService()

    service.set_manual_roller_speed(60)
    service.set_manual_brush_speed(75)

    assert service.state.roller_speed_percent == 60
    assert service.state.brush_speed_percent == 75


def test_manual_speed_must_be_between_0_and_100() -> None:
    service = MachineOperationService()

    with pytest.raises(
        ValueError,
        match="Speed percent must be greater than 0 and no more than 100",
    ):
        service.set_manual_roller_speed(0)

    with pytest.raises(
        ValueError,
        match="Speed percent must be greater than 0 and no more than 100",
    ):
        service.set_manual_brush_speed(101)


def test_manual_speed_is_converted_to_frequency() -> None:
    service = MachineOperationService()

    service.set_manual_roller_speed(60)
    service.set_manual_brush_speed(40)

    assert service.get_manual_roller_frequency() == 30
    assert service.get_manual_brush_frequency() == 20
