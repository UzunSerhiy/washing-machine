from unittest.mock import Mock

import pytest

from app.services.machine.roller import Roller


def create_roller():
    drive = Mock()
    roller = Roller(drive=drive)

    return roller, drive


def test_forward_sets_frequency_and_runs_forward():
    roller, drive = create_roller()

    roller.forward(35.0)

    drive.set_frequency.assert_called_once_with(35.0)
    drive.run_forward.assert_called_once()


def test_reverse_sets_frequency_and_runs_reverse():
    roller, drive = create_roller()

    roller.reverse(20.0)

    drive.set_frequency.assert_called_once_with(20.0)
    drive.run_reverse.assert_called_once()


def test_forward_does_not_run_reverse():
    roller, drive = create_roller()

    roller.forward(35.0)

    drive.run_reverse.assert_not_called()


def test_reverse_does_not_run_forward():
    roller, drive = create_roller()

    roller.reverse(20.0)

    drive.run_forward.assert_not_called()


def test_stop_stops_roller():
    roller, drive = create_roller()

    roller.stop()

    drive.stop.assert_called_once()


def test_stop_coast_stops_roller_with_coast_command():
    roller, drive = create_roller()

    roller.stop_coast()

    drive.stop_coast.assert_called_once()


@pytest.mark.parametrize(
    "frequency_hz",
    [-1, -10, -0.1],
)
def test_forward_rejects_negative_frequency(frequency_hz):
    roller, drive = create_roller()

    with pytest.raises(ValueError):
        roller.forward(frequency_hz)


@pytest.mark.parametrize(
    "frequency_hz",
    [-1, -10, -0.1],
)
def test_reverse_rejects_negative_frequency(frequency_hz):
    roller, drive = create_roller()

    with pytest.raises(ValueError):
        roller.reverse(frequency_hz)
