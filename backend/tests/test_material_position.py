import pytest

from app.services.winding.material_position import (
    MaterialPositionState,
    MaterialPositionTracker,
)


def create_tracker() -> MaterialPositionTracker:
    return MaterialPositionTracker(
        belt_start_turns=3.5,
        material_turns=23.5,
        brush_clear_turns=2.5,
    )


def test_initial_position_is_before_material():
    tracker = create_tracker()

    assert tracker.position_turns == 0
    assert tracker.state == MaterialPositionState.BELT_BEFORE_MATERIAL


def test_reaching_material_start():
    tracker = create_tracker()

    tracker.move_forward(3.5)

    assert tracker.position_turns == pytest.approx(3.5)
    assert tracker.state == MaterialPositionState.MATERIAL


def test_inside_material_zone():
    tracker = create_tracker()

    tracker.move_forward(10)

    assert tracker.position_turns == pytest.approx(10)
    assert tracker.state == MaterialPositionState.MATERIAL


def test_reaching_material_end():
    tracker = create_tracker()

    tracker.move_forward(3.5 + 23.5)

    assert tracker.position_turns == pytest.approx(27.0)
    assert tracker.state == MaterialPositionState.BRUSH_CLEAR


def test_inside_brush_clear_zone():
    tracker = create_tracker()

    tracker.move_forward(28)

    assert tracker.position_turns == pytest.approx(28)
    assert tracker.state == MaterialPositionState.BRUSH_CLEAR


def test_reaching_cycle_end():
    tracker = create_tracker()

    tracker.move_forward(29.5)

    assert tracker.position_turns == pytest.approx(29.5)
    assert tracker.state == MaterialPositionState.CYCLE_END


def test_position_cannot_exceed_cycle_end():
    tracker = create_tracker()

    tracker.move_forward(100)

    assert tracker.position_turns == pytest.approx(29.5)
    assert tracker.state == MaterialPositionState.CYCLE_END


def test_reverse_movement():
    tracker = create_tracker()

    tracker.move_forward(20)
    tracker.move_reverse(5)

    assert tracker.position_turns == pytest.approx(15)
    assert tracker.state == MaterialPositionState.MATERIAL


def test_reverse_to_material_start():
    tracker = create_tracker()

    tracker.move_forward(10)
    tracker.move_reverse(6.5)

    assert tracker.position_turns == pytest.approx(3.5)
    assert tracker.state == MaterialPositionState.MATERIAL


def test_reverse_into_belt_zone():
    tracker = create_tracker()

    tracker.move_forward(10)
    tracker.move_reverse(7)

    assert tracker.position_turns == pytest.approx(3)
    assert tracker.state == MaterialPositionState.BELT_BEFORE_MATERIAL


def test_position_cannot_go_below_zero():
    tracker = create_tracker()

    tracker.move_reverse(100)

    assert tracker.position_turns == 0
    assert tracker.state == MaterialPositionState.BELT_BEFORE_MATERIAL


def test_reset():
    tracker = create_tracker()

    tracker.move_forward(20)
    tracker.reset()

    assert tracker.position_turns == 0
    assert tracker.state == MaterialPositionState.BELT_BEFORE_MATERIAL


def test_negative_forward_turns_are_rejected():
    tracker = create_tracker()

    with pytest.raises(ValueError):
        tracker.move_forward(-1)


def test_negative_reverse_turns_are_rejected():
    tracker = create_tracker()

    with pytest.raises(ValueError):
        tracker.move_reverse(-1)


def test_invalid_belt_start_turns():
    with pytest.raises(ValueError):
        MaterialPositionTracker(
            belt_start_turns=-1,
            material_turns=23.5,
            brush_clear_turns=2.5,
        )


def test_invalid_material_turns():
    with pytest.raises(ValueError):
        MaterialPositionTracker(
            belt_start_turns=3.5,
            material_turns=0,
            brush_clear_turns=2.5,
        )
