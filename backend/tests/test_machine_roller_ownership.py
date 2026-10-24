from unittest.mock import Mock

import pytest

from app.services.machine.machine import Machine
from app.services.machine.roller import Roller


@pytest.fixture
def machine():
    drive = Mock()
    brush = Mock()
    return Machine(
        brush=brush,
        roller=Roller(drive=drive),
    )


def test_homing_blocks_manual_forward(machine):
    machine.acquire_roller("homing")

    with pytest.raises(RuntimeError, match="reserved"):
        machine.start_roller_forward(10.0)

    machine.roller.drive.run_forward.assert_not_called()


def test_homing_blocks_manual_reverse(machine):
    machine.acquire_roller("homing")

    with pytest.raises(RuntimeError, match="reserved"):
        machine.start_roller_reverse(10.0)

    machine.roller.drive.run_reverse.assert_not_called()


def test_homing_owner_can_move(machine):
    machine.acquire_roller("homing")

    machine.start_roller_reverse(
        10.0,
        owner="homing",
    )

    machine.roller.drive.run_reverse.assert_called_once()


def test_stop_allowed_during_homing(machine):
    machine.acquire_roller("homing")

    machine.stop_roller()

    machine.roller.drive.stop.assert_called_once()


def test_other_owner_cannot_release(machine):
    machine.acquire_roller("homing")

    with pytest.raises(RuntimeError, match="mismatch"):
        machine.release_roller("manual")

    assert machine.roller_owner == "homing"


def test_release_allows_manual_movement(machine):
    machine.acquire_roller("homing")
    machine.release_roller("homing")

    machine.start_roller_forward(10.0)

    machine.roller.drive.run_forward.assert_called_once()
