import pytest

from app.services.machine.operation import AutoStage, OperationMode
from app.services.machine.operation_service import MachineOperationService


class FakeMachine:
    def __init__(self):
        self.calls = []

    def start_roller_forward(self, frequency_hz: float) -> None:
        self.calls.append(("forward", frequency_hz))

    def start_roller_reverse(self, frequency_hz: float) -> None:
        self.calls.append(("reverse", frequency_hz))

    def stop_roller(self) -> None:
        self.calls.append(("stop",))

    def start_brush(self, frequency_hz: float) -> None:
        self.calls.append(("brush_start", frequency_hz))

    def stop_brush(self) -> None:
        self.calls.append(("brush_stop",))

    def stop_all(self) -> None:
        self.calls.append(("stop_all",))


def test_auto_stage_navigation() -> None:
    machine = FakeMachine()
    service = MachineOperationService(machine=machine)

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
    machine = FakeMachine()
    service = MachineOperationService(machine=machine)

    service.set_auto_mode(material_profile_id=1)

    with pytest.raises(RuntimeError, match="Already at the first auto stage"):
        service.previous_stage()


def test_cannot_go_after_last_stage() -> None:
    machine = FakeMachine()
    service = MachineOperationService(machine=machine)

    service.set_auto_mode(material_profile_id=1)

    service.next_stage()
    service.next_stage()
    service.next_stage()

    with pytest.raises(RuntimeError, match="Already at the last auto stage"):
        service.next_stage()


def test_stage_navigation_only_in_auto_mode() -> None:
    machine = FakeMachine()
    service = MachineOperationService(machine=machine)

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
    machine = FakeMachine()
    service = MachineOperationService(machine=machine)

    service.set_manual_roller_speed(60)
    service.set_manual_brush_speed(75)

    assert service.state.roller_speed_percent == 60
    assert service.state.brush_speed_percent == 75


def test_manual_speed_must_be_between_0_and_100() -> None:
    machine = FakeMachine()
    service = MachineOperationService(machine=machine)

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
    machine = FakeMachine()
    service = MachineOperationService(machine=machine)

    service.set_manual_roller_speed(60)
    service.set_manual_brush_speed(40)

    assert service.get_manual_roller_frequency() == 30
    assert service.get_manual_brush_frequency() == 20


def test_manual_roller_forward_uses_manual_speed() -> None:
    machine = FakeMachine()
    service = MachineOperationService(machine=machine)

    service.set_manual_roller_speed(60)
    service.start_manual_roller_forward()

    assert machine.calls == [("forward", 30.0)]
    assert service.state.roller_running is True


def test_manual_roller_reverse_uses_manual_speed() -> None:
    machine = FakeMachine()
    service = MachineOperationService(machine=machine)

    service.set_manual_roller_speed(40)
    service.start_manual_roller_reverse()

    assert machine.calls == [("reverse", 20.0)]
    assert service.state.roller_running is True


def test_manual_roller_stop() -> None:
    machine = FakeMachine()
    service = MachineOperationService(machine=machine)

    service.set_manual_roller_speed(60)
    service.start_manual_roller_forward()
    service.stop_manual_roller()

    assert machine.calls == [
        ("forward", 30.0),
        ("stop",),
    ]
    assert service.state.roller_running is False


def test_manual_brush_start_uses_manual_speed() -> None:
    machine = FakeMachine()
    service = MachineOperationService(machine=machine)

    service.set_manual_brush_speed(50)
    service.start_manual_brush()

    assert machine.calls == [("brush_start", 25.0)]
    assert service.state.brush_running is True


def test_manual_brush_stop() -> None:
    machine = FakeMachine()
    service = MachineOperationService(machine=machine)

    service.set_manual_brush_speed(50)
    service.start_manual_brush()
    service.stop_manual_brush()

    assert machine.calls == [
        ("brush_start", 25.0),
        ("brush_stop",),
    ]
    assert service.state.brush_running is False


def test_manual_roller_and_brush_state_are_independent() -> None:
    machine = FakeMachine()
    service = MachineOperationService(machine=machine)

    service.set_manual_roller_speed(60)
    service.set_manual_brush_speed(40)

    service.start_manual_roller_forward()
    service.start_manual_brush()

    assert service.state.roller_running is True
    assert service.state.brush_running is True

    service.stop_manual_brush()

    assert service.state.roller_running is True
    assert service.state.brush_running is False


def test_switch_from_manual_to_auto_stops_machine() -> None:
    machine = FakeMachine()
    service = MachineOperationService(machine=machine)

    service.set_manual_roller_speed(60)
    service.set_manual_brush_speed(40)

    service.start_manual_roller_forward()
    service.start_manual_brush()

    machine.calls.clear()

    service.set_auto_mode(material_profile_id=1)

    assert machine.calls == [("stop_all",)]
    assert service.state.mode == OperationMode.AUTO
    assert service.state.auto_stage == AutoStage.WINDING
    assert service.state.material_profile_id == 1
    assert service.state.roller_running is False
    assert service.state.brush_running is False
    assert service.state.running is False
    assert service.state.paused is False


def test_switch_from_manual_to_calibration_stops_machine() -> None:
    machine = FakeMachine()
    service = MachineOperationService(machine=machine)

    service.set_manual_roller_speed(60)
    service.start_manual_roller_forward()

    machine.calls.clear()

    service.set_calibration_mode(material_profile_id=1)

    assert machine.calls == [("stop_all",)]
    assert service.state.mode == OperationMode.CALIBRATION
    assert service.state.auto_stage is None
    assert service.state.material_profile_id == 1
    assert service.state.roller_running is False
    assert service.state.brush_running is False


def test_switch_to_manual_stops_machine_and_clears_process_state() -> None:
    machine = FakeMachine()
    service = MachineOperationService(machine=machine)

    service.set_auto_mode(material_profile_id=1)

    machine.calls.clear()

    service.set_manual_mode()

    assert machine.calls == [("stop_all",)]
    assert service.state.mode == OperationMode.MANUAL
    assert service.state.auto_stage is None
    assert service.state.material_profile_id is None
    assert service.state.roller_running is False
    assert service.state.brush_running is False
    assert service.state.running is False
    assert service.state.paused is False


def test_mode_change_clears_paused_state() -> None:
    machine = FakeMachine()
    service = MachineOperationService(machine=machine)

    service.state.paused = True

    service.set_auto_mode(material_profile_id=1)

    assert service.state.paused is False


def test_manual_roller_cannot_start_without_configured_speed() -> None:
    machine = FakeMachine()
    service = MachineOperationService(machine=machine)

    with pytest.raises(
        RuntimeError,
        match="Manual roller speed is not configured",
    ):
        service.start_manual_roller_forward()

    assert machine.calls == []
    assert service.state.roller_running is False


def test_manual_brush_cannot_start_without_configured_speed() -> None:
    machine = FakeMachine()
    service = MachineOperationService(machine=machine)

    with pytest.raises(
        RuntimeError,
        match="Manual brush speed is not configured",
    ):
        service.start_manual_brush()

    assert machine.calls == []
    assert service.state.brush_running is False


def test_manual_speeds_are_not_configured_initially() -> None:
    machine = FakeMachine()
    service = MachineOperationService(machine=machine)

    assert service.state.roller_speed_percent is None
    assert service.state.brush_speed_percent is None
