import pytest

from app.services.machine.calibration.points import CalibrationPoint

from app.services.machine.calibration.session_service import (
    CalibrationSessionService,
)
from app.services.winding.rotation import RollerRotationCalculator


class FakeClock:
    def __init__(self):
        self.current = 0.0

    def now(self) -> float:
        return self.current

    def advance(self, seconds: float) -> None:
        if seconds < 0:
            raise ValueError("Seconds cannot be negative")

        self.current += seconds


class FakeMachine:
    def __init__(self):
        self.calls = []

    def start_roller_forward(self, frequency_hz: float) -> None:
        self.calls.append(("forward", frequency_hz))

    def start_roller_reverse(self, frequency_hz: float) -> None:
        self.calls.append(("reverse", frequency_hz))

    def stop_roller(self) -> None:
        self.calls.append(("stop",))


def create_service():
    machine = FakeMachine()

    service = CalibrationSessionService(
        machine=machine,
        rotation_calculator=RollerRotationCalculator(
            motor_rpm_at_50hz=905,
            gear_ratio=100,
        ),
    )

    return service, machine


def create_service_with_clock():
    machine = FakeMachine()
    clock = FakeClock()

    service = CalibrationSessionService(
        machine=machine,
        rotation_calculator=RollerRotationCalculator(
            motor_rpm_at_50hz=905,
            gear_ratio=100,
        ),
        clock=clock,
    )

    return service, machine, clock


def test_session_is_not_active_initially() -> None:
    service, _ = create_service()

    assert service.active is False


def test_start_creates_calibration_session() -> None:
    service, _ = create_service()

    session = service.start(material_profile_id=3)

    assert service.active is True
    assert session.material_profile_id == 3
    assert service.get_current() is session


def test_cannot_start_second_session() -> None:
    service, _ = create_service()

    service.start(material_profile_id=1)

    with pytest.raises(
        RuntimeError,
        match="Calibration session is already active",
    ):
        service.start(material_profile_id=2)


def test_get_current_requires_active_session() -> None:
    service, _ = create_service()

    with pytest.raises(
        RuntimeError,
        match="Calibration session is not active",
    ):
        service.get_current()


def test_cancel_removes_session() -> None:
    service, machine = create_service()

    service.start(material_profile_id=1)

    machine.calls.clear()

    service.cancel()

    assert service.active is False
    assert machine.calls == [("stop",)]


def test_cancel_without_session_does_nothing() -> None:
    service, machine = create_service()

    service.cancel()

    assert service.active is False
    assert machine.calls == []


def test_can_start_new_session_after_cancel() -> None:
    service, _ = create_service()

    first = service.start(material_profile_id=1)
    service.cancel()

    second = service.start(material_profile_id=2)

    assert second is not first
    assert second.material_profile_id == 2
    assert service.active is True


def test_jog_forward_delegates_to_player() -> None:
    service, machine = create_service()
    service.start(material_profile_id=1)

    service.jog_forward(20.0)

    assert machine.calls == [("forward", 20.0)]

    session = service.get_current()
    assert session.player.running is True
    assert session.player.direction == "forward"
    assert session.player.frequency_hz == 20.0


def test_jog_reverse_delegates_to_player() -> None:
    service, machine = create_service()
    service.start(material_profile_id=1)

    service.jog_reverse(15.0)

    assert machine.calls == [("reverse", 15.0)]

    session = service.get_current()
    assert session.player.running is True
    assert session.player.direction == "reverse"
    assert session.player.frequency_hz == 15.0


def test_pause_delegates_to_player() -> None:
    service, machine = create_service()
    service.start(material_profile_id=1)

    service.jog_forward(20.0)
    machine.calls.clear()

    service.pause()

    assert machine.calls == [("stop",)]

    session = service.get_current()
    assert session.player.running is False
    assert session.player.paused is True


def test_stop_delegates_to_player() -> None:
    service, machine = create_service()
    service.start(material_profile_id=1)

    service.jog_forward(20.0)
    machine.calls.clear()

    service.stop()

    assert machine.calls == [("stop",)]

    session = service.get_current()
    assert session.player.running is False
    assert session.player.paused is False


def test_reset_position_sets_point_zero() -> None:
    service, _ = create_service()
    session = service.start(material_profile_id=1)

    session.position_tracker.set_position(12.5)

    service.reset_position()

    assert session.position_turns == 0.0


def test_mark_washing_stop_uses_current_position() -> None:
    service, _ = create_service()
    session = service.start(material_profile_id=1)

    session.position_tracker.set_position(3.0)

    service.mark(CalibrationPoint.WASHING_STOP)

    assert session.machine_calibration.washing_stop_turns == 3.0


def test_mark_material_start_uses_current_position() -> None:
    service, _ = create_service()
    session = service.start(material_profile_id=1)

    session.position_tracker.set_position(10.0)

    service.mark(CalibrationPoint.MATERIAL_START)

    assert session.machine_calibration.material_start_turns == 10.0


def test_mark_material_end_uses_current_position() -> None:
    service, _ = create_service()
    session = service.start(material_profile_id=1)

    session.position_tracker.set_position(35.0)

    service.mark(CalibrationPoint.MATERIAL_END)

    assert session.winding_calibration.material_end_turns == 35.0


def test_commands_require_active_session() -> None:
    service, _ = create_service()

    with pytest.raises(
        RuntimeError,
        match="Calibration session is not active",
    ):
        service.jog_forward(20.0)

    with pytest.raises(
        RuntimeError,
        match="Calibration session is not active",
    ):
        service.mark(CalibrationPoint.WASHING_STOP)


def test_forward_position_is_updated_before_mark() -> None:
    service, _, clock = create_service_with_clock()
    session = service.start(material_profile_id=1)

    service.jog_forward(20.0)

    clock.advance(10.0)

    service.mark(CalibrationPoint.WASHING_STOP)

    expected_turns = 3.62 * 10 / 60

    assert session.position_turns == pytest.approx(expected_turns)
    assert session.machine_calibration.washing_stop_turns == pytest.approx(
        expected_turns
    )


def test_reverse_position_is_updated_before_mark() -> None:
    service, _, clock = create_service_with_clock()
    session = service.start(material_profile_id=1)

    session.position_tracker.set_position(2.0)

    service.jog_reverse(20.0)

    clock.advance(10.0)

    service.mark(CalibrationPoint.WASHING_STOP)

    expected_turns = 2.0 - (3.62 * 10 / 60)

    assert session.position_turns == pytest.approx(expected_turns)
    assert session.machine_calibration.washing_stop_turns == pytest.approx(
        expected_turns
    )


def test_pause_updates_position() -> None:
    service, _, clock = create_service_with_clock()
    session = service.start(material_profile_id=1)

    service.jog_forward(20.0)

    clock.advance(5.0)

    service.pause()

    expected_turns = 3.62 * 5 / 60

    assert session.position_turns == pytest.approx(expected_turns)


def test_stop_updates_position() -> None:
    service, _, clock = create_service_with_clock()
    session = service.start(material_profile_id=1)

    service.jog_forward(20.0)

    clock.advance(5.0)

    service.stop()

    expected_turns = 3.62 * 5 / 60

    assert session.position_turns == pytest.approx(expected_turns)


def test_changing_direction_preserves_previous_movement() -> None:
    service, _, clock = create_service_with_clock()
    session = service.start(material_profile_id=1)

    service.jog_forward(20.0)

    clock.advance(10.0)

    service.jog_reverse(20.0)

    forward_turns = 3.62 * 10 / 60

    assert session.position_turns == pytest.approx(forward_turns)

    clock.advance(5.0)

    service.stop()

    reverse_turns = 3.62 * 5 / 60

    assert session.position_turns == pytest.approx(forward_turns - reverse_turns)


def test_reset_position_syncs_before_setting_point_zero() -> None:
    service, _, clock = create_service_with_clock()
    session = service.start(material_profile_id=1)

    service.jog_forward(20.0)

    clock.advance(10.0)

    service.reset_position()

    assert session.position_turns == 0.0


def test_complete_returns_completed_session() -> None:
    service, _ = create_service()
    session = service.start(material_profile_id=1)

    session.position_tracker.set_position(3.0)
    service.mark(CalibrationPoint.WASHING_STOP)

    session.position_tracker.set_position(10.0)
    service.mark(CalibrationPoint.MATERIAL_START)

    session.position_tracker.set_position(35.0)
    service.mark(CalibrationPoint.MATERIAL_END)

    completed = service.complete()

    assert completed is session
    assert completed.is_complete()
    assert service.active is False


def test_complete_stops_player() -> None:
    service, machine = create_service()
    session = service.start(material_profile_id=1)

    session.position_tracker.set_position(3.0)
    service.mark(CalibrationPoint.WASHING_STOP)

    session.position_tracker.set_position(10.0)
    service.mark(CalibrationPoint.MATERIAL_START)

    session.position_tracker.set_position(35.0)
    service.mark(CalibrationPoint.MATERIAL_END)

    service.jog_forward(20.0)

    machine.calls.clear()

    service.complete()

    assert machine.calls == [("stop",)]


def test_complete_requires_complete_calibration() -> None:
    service, machine = create_service()
    service.start(material_profile_id=1)

    machine.calls.clear()

    with pytest.raises(
        ValueError,
        match="Material start point is not calibrated",
    ):
        service.complete()

    assert service.active is True


def test_complete_requires_active_session() -> None:
    service, _ = create_service()

    with pytest.raises(
        RuntimeError,
        match="Calibration session is not active",
    ):
        service.complete()


# def test_tick_updates_running_player_position() -> None:
#     service, _ = create_service()
#     session = service.start(material_profile_id=1)
#
#     service.jog_forward(20.0)
#
#     initial_position = session.position_turns
#
#     service.clock.advance(1.0)
#
#     service.tick()
#
#     assert session.position_turns > initial_position


# def test_tick_without_active_session_does_nothing() -> None:
#     service, _ = create_service()
#
#     service.tick()


def test_tick_clears_update_time_when_player_stops_at_point_zero() -> None:
    service, _, clock = create_service_with_clock()
    session = service.start(material_profile_id=1)

    session.position_tracker.set_position(0.01)

    service.jog_reverse(20.0)

    assert service._last_update_time is not None

    clock.advance(1.0)
    service.tick()

    assert session.position_turns == 0.0
    assert session.player.running is False
    assert service._last_update_time is None


def test_tick_updates_running_player_position() -> None:
    service, _, clock = create_service_with_clock()
    session = service.start(material_profile_id=1)

    service.jog_forward(20.0)

    assert session.position_turns == 0.0

    clock.advance(1.0)
    service.tick()

    assert session.position_turns > 0.0
    assert session.player.running is True


def test_tick_without_active_session_does_nothing() -> None:
    service, _, _ = create_service_with_clock()

    service.tick()

    assert service.active is False


def test_tick_stops_reverse_at_point_zero() -> None:
    service, machine, clock = create_service_with_clock()
    session = service.start(material_profile_id=1)

    session.position_tracker.set_position(0.01)

    service.jog_reverse(20.0)

    machine.calls.clear()

    clock.advance(1.0)
    service.tick()

    assert session.position_turns == 0.0
    assert session.player.running is False
    assert service._last_update_time is None
    assert machine.calls == [("stop",)]
