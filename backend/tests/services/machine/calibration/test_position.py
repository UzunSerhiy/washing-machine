import pytest

from app.services.machine.calibration.position import RollerPositionTracker


def test_initial_position_is_zero():
    tracker = RollerPositionTracker()

    assert tracker.position_turns == 0.0


def test_forward_increases_position():
    tracker = RollerPositionTracker()

    tracker.move_forward(10.0)

    assert tracker.position_turns == 10.0


def test_reverse_decreases_position():
    tracker = RollerPositionTracker()

    tracker.move_forward(10.0)
    tracker.move_reverse(3.0)

    assert tracker.position_turns == 7.0


def test_multiple_movements():
    tracker = RollerPositionTracker()

    tracker.move_forward(10.0)
    tracker.move_reverse(2.0)
    tracker.move_forward(1.0)

    assert tracker.position_turns == 9.0


def test_position_can_be_negative():
    tracker = RollerPositionTracker()

    tracker.move_reverse(5.0)

    assert tracker.position_turns == -5.0


def test_reset():
    tracker = RollerPositionTracker()

    tracker.move_forward(10.0)
    tracker.move_reverse(2.0)

    tracker.reset()

    assert tracker.position_turns == 0.0


def test_zero_movement_is_allowed():
    tracker = RollerPositionTracker()

    tracker.move_forward(0.0)
    tracker.move_reverse(0.0)

    assert tracker.position_turns == 0.0


def test_negative_forward_revolutions_are_invalid():
    tracker = RollerPositionTracker()

    with pytest.raises(
        ValueError,
        match="Revolutions cannot be negative",
    ):
        tracker.move_forward(-1.0)


def test_negative_reverse_revolutions_are_invalid():
    tracker = RollerPositionTracker()

    with pytest.raises(
        ValueError,
        match="Revolutions cannot be negative",
    ):
        tracker.move_reverse(-1.0)
