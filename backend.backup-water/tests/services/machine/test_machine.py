from unittest.mock import Mock

from app.services.machine.machine import Machine


def create_machine():
    brush = Mock()
    roller = Mock()

    machine = Machine(
        brush=brush,
        roller=roller,
    )

    return machine, brush, roller


def test_start_brush_delegates_to_brush():
    machine, brush, roller = create_machine()

    machine.start_brush(35.0)

    brush.start.assert_called_once_with(35.0)
    roller.assert_not_called()


def test_stop_brush_delegates_to_brush():
    machine, brush, roller = create_machine()

    machine.stop_brush()

    brush.stop.assert_called_once()


def test_start_roller_forward_delegates_to_roller():
    machine, brush, roller = create_machine()

    machine.start_roller_forward(40.0)

    roller.forward.assert_called_once_with(40.0)


def test_start_roller_reverse_delegates_to_roller():
    machine, brush, roller = create_machine()

    machine.start_roller_reverse(20.0)

    roller.reverse.assert_called_once_with(20.0)


def test_stop_roller_delegates_to_roller():
    machine, brush, roller = create_machine()

    machine.stop_roller()

    roller.stop.assert_called_once()


def test_stop_roller_coast_delegates_to_roller():
    machine, brush, roller = create_machine()

    machine.stop_roller_coast()

    roller.stop_coast.assert_called_once()


def test_stop_all_stops_brush_and_roller():
    machine, brush, roller = create_machine()

    machine.stop_all()

    brush.stop.assert_called_once()
    roller.stop.assert_called_once()
