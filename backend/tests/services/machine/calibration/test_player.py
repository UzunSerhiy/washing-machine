import pytest

from app.services.machine.calibration.player import CalibrationPlayer
from app.services.machine.calibration.position import RollerPositionTracker
from app.services.machine.machine import Machine
from app.services.winding.rotation import RollerRotationCalculator
from app.services.machine.calibration.points import CalibrationPoint
from app.services.machine.calibration.store import CalibrationPointStore


class FakeMachine:
    def __init__(self):
        self.calls = []

    def start_roller_forward(self, frequency_hz: float) -> None:
        self.calls.append(("forward", frequency_hz))

    def start_roller_reverse(self, frequency_hz: float) -> None:
        self.calls.append(("reverse", frequency_hz))

    def stop_roller(self) -> None:
        self.calls.append(("stop",))


@pytest.fixture
def machine():
    return FakeMachine()


@pytest.fixture
def player(machine):
    tracker = RollerPositionTracker()

    calculator = RollerRotationCalculator(
        motor_rpm_at_50hz=905,
        gear_ratio=100,
    )

    return CalibrationPlayer(
        machine=machine, position_tracker=tracker, rotation_calculator=calculator
    )


def test_new_player_is_stopped(player):
    assert player.running is False
    assert player.paused is False
    assert player.direction is None
    assert player.frequency_hz is None
    assert player.position_turns == 0.0


def test_jog_forward(player, machine):
    player.start_jog_forward(5.0)

    assert player.running is True
    assert player.paused is False
    assert player.direction == "forward"
    assert player.frequency_hz == 5.0

    assert machine.calls == [
        ("forward", 5.0),
    ]


def test_jog_reverse(player, machine):
    player.start_jog_reverse(7.5)

    assert player.running is True
    assert player.paused is False
    assert player.direction == "reverse"
    assert player.frequency_hz == 7.5

    assert machine.calls == [
        ("reverse", 7.5),
    ]


def test_stop(player, machine):
    player.start_jog_forward(5.0)

    player.stop()

    assert player.running is False
    assert player.paused is False
    assert player.direction is None
    assert player.frequency_hz is None

    assert machine.calls == [
        ("forward", 5.0),
        ("stop",),
    ]


def test_pause(player, machine):
    player.start_jog_forward(5.0)

    player.pause()

    assert player.running is False
    assert player.paused is True
    assert player.direction == "forward"
    assert player.frequency_hz == 5.0

    assert machine.calls == [
        ("forward", 5.0),
        ("stop",),
    ]


def test_pause_when_not_running_does_nothing(player, machine):
    player.pause()

    assert player.running is False
    assert player.paused is False
    assert player.direction is None
    assert player.frequency_hz is None
    assert machine.calls == []


def test_position_is_preserved_after_pause(player):
    player.position_tracker.move_forward(10.0)

    player.start_jog_forward(5.0)
    player.pause()

    assert player.position_turns == 10.0


def test_reset_position(player):
    player.position_tracker.move_forward(15.0)

    player.reset_position()

    assert player.position_turns == 0.0


def test_start_forward_after_pause(player, machine):
    player.start_jog_forward(5.0)
    player.pause()

    player.start_jog_forward(3.0)

    assert player.running is True
    assert player.paused is False
    assert player.direction == "forward"
    assert player.frequency_hz == 3.0

    assert machine.calls == [
        ("forward", 5.0),
        ("stop",),
        ("forward", 3.0),
    ]


def test_switch_from_forward_to_reverse(player, machine):
    player.start_jog_forward(5.0)
    player.start_jog_reverse(4.0)

    assert player.running is True
    assert player.paused is False
    assert player.direction == "reverse"
    assert player.frequency_hz == 4.0

    assert machine.calls == [
        ("forward", 5.0),
        ("reverse", 4.0),
    ]


def test_update_moves_position_forward(player):
    player.start_jog_forward(5.0)

    player.update(10.0)

    expected = 5.0 * 905 / 50 / 100 * 10 / 60

    assert player.position_turns == pytest.approx(expected)


def test_update_moves_position_reverse(player):
    player.start_jog_reverse(5.0)

    player.update(10.0)

    expected = -(5.0 * 905 / 50 / 100 * 10 / 60)

    assert player.position_turns == pytest.approx(expected)


def test_update_multiple_times(player):
    player.start_jog_forward(5.0)

    player.update(5.0)
    player.update(5.0)

    expected = 5.0 * 905 / 50 / 100 * 10 / 60

    assert player.position_turns == pytest.approx(expected)


def test_update_preserves_position_when_paused(player):
    player.start_jog_forward(5.0)

    player.update(10.0)

    position_before_pause = player.position_turns

    player.pause()
    player.update(10.0)

    assert player.position_turns == pytest.approx(position_before_pause)


def test_update_preserves_position_when_stopped(player):
    player.start_jog_forward(5.0)

    player.update(10.0)

    position_before_stop = player.position_turns

    player.stop()
    player.update(10.0)

    assert player.position_turns == pytest.approx(position_before_stop)


def test_update_after_direction_change(player):
    player.start_jog_forward(5.0)
    player.update(10.0)

    forward_position = player.position_turns

    player.start_jog_reverse(5.0)
    player.update(5.0)

    expected_reverse = 5.0 * 905 / 50 / 100 * 5 / 60

    assert player.position_turns == pytest.approx(forward_position - expected_reverse)


def test_update_zero_time_does_not_change_position(player):
    player.start_jog_forward(5.0)

    player.update(0.0)

    assert player.position_turns == 0.0


def test_update_negative_time_is_invalid(player):
    player.start_jog_forward(5.0)

    with pytest.raises(
        ValueError,
        match="Elapsed seconds cannot be negative",
    ):
        player.update(-1.0)


def test_save_current_position_as_calibration_point(player):
    store = CalibrationPointStore()

    player.calibration_store = store

    player.start_jog_forward(5.0)
    player.update(10.0)

    player.save_point(CalibrationPoint.WINDING_BELT_START)

    assert store.get(CalibrationPoint.WINDING_BELT_START) == player.position_turns


def test_save_point_does_not_change_player_position(player):
    store = CalibrationPointStore()

    player.calibration_store = store

    player.start_jog_forward(5.0)
    player.update(10.0)

    position_before = player.position_turns

    player.save_point(CalibrationPoint.WINDING_BELT_START)

    assert player.position_turns == position_before


@pytest.mark.parametrize(
    "frequency_hz",
    [0, -1, -5.0],
)
def test_invalid_frequency(frequency_hz, player):
    with pytest.raises(
        ValueError,
        match="Frequency must be greater than zero",
    ):
        player.start_jog_forward(frequency_hz)
