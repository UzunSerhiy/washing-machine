from unittest.mock import Mock

import pytest

from app.services.machine.brush import Brush


def create_brush():
    left_drive = Mock()
    right_drive = Mock()

    brush = Brush(
        left_drive=left_drive,
        right_drive=right_drive,
    )

    return brush, left_drive, right_drive


def test_start_sets_same_frequency_on_both_brushes():
    brush, left_drive, right_drive = create_brush()

    brush.start(35.0)

    left_drive.set_frequency.assert_called_once_with(35.0)
    right_drive.set_frequency.assert_called_once_with(35.0)


def test_start_runs_brushes_in_opposite_directions():
    brush, left_drive, right_drive = create_brush()

    brush.start(35.0)

    left_drive.run_forward.assert_called_once()
    right_drive.run_reverse.assert_called_once()


def test_start_does_not_reverse_left_brush():
    brush, left_drive, right_drive = create_brush()

    brush.start(35.0)

    left_drive.run_reverse.assert_not_called()
    right_drive.run_forward.assert_not_called()


def test_stop_stops_both_brushes():
    brush, left_drive, right_drive = create_brush()

    brush.stop()

    left_drive.stop.assert_called_once()
    right_drive.stop.assert_called_once()


@pytest.mark.parametrize(
    "frequency_hz",
    [0, -1, -10],
)
def test_start_rejects_invalid_frequency(frequency_hz):
    brush, left_drive, right_drive = create_brush()

    with pytest.raises(ValueError):
        brush.start(frequency_hz)
