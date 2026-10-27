"""Step 30B: simulated E-STOP / physical RESET contract; never touches hardware.

A GAIN fault register is only telemetry. Tests do not prove E-STOP wiring,
contact safety category, physical stopping, or RESET electrical behavior.
"""
import asyncio

import pytest

from tests.test_motion_fault_http_recovery import rig, request, assert_no_commands


def test_estop_e15_on_each_drive_blocks_software_ack(rig):
    for drive_id in (1, 2, 3):
        rig.drives[drive_id].get_fault.return_value = 15
        status, response = request(rig)
        assert status == 409, (drive_id, response)
        assert rig.machine.motion_fault_latched == "E15"
        assert rig.machine.clears == 0
        rig.drives[drive_id].get_fault.return_value = 0
    assert_no_commands(rig)


def test_physical_reset_telemetry_zero_does_not_clear_software_latch(rig):
    # Simulate physical RESET changing GAIN fault registers from E15 to 0.
    for drive in rig.drives.values():
        drive.get_fault.return_value = 15
    for drive in rig.drives.values():
        drive.get_fault.return_value = 0
    assert rig.machine.motion_fault_latched == "E15"
    assert rig.machine.clears == 0
    assert_no_commands(rig)


def test_physical_reset_without_operator_confirmation_is_rejected(rig):
    status, response = request(rig, confirmed=False)
    assert status == 409, response
    assert rig.machine.motion_fault_latched == "E15"
    assert rig.machine.clears == 0
    assert_no_commands(rig)


@pytest.mark.parametrize("drive_id", (1, 2, 3))
def test_reset_with_missing_drive_telemetry_is_rejected(rig, drive_id):
    rig.drives[drive_id].get_fault.side_effect = OSError("RS485 disconnected")
    status, response = request(rig)
    assert status == 409, response
    assert rig.machine.motion_fault_latched == "E15"
    assert rig.machine.clears == 0
    assert_no_commands(rig)


def test_reset_and_confirm_clear_software_latch_but_never_run(rig):
    status, response = request(rig)
    assert status == 200, response
    assert response["homed"] is False
    assert response["automatic_restart"] is False
    assert rig.machine.motion_fault_latched is None
    assert_no_commands(rig)


def test_new_estop_after_ack_requires_new_ack(rig):
    assert request(rig)[0] == 200
    # Simulate monitor latching a new E15 event after an earlier recovery.
    rig.machine.motion_fault_latched = "E15 (new event)"
    rig.runtime._notified = True
    rig.drives[1].get_fault.return_value = 15
    status, response = request(rig)
    assert status == 409, response
    assert rig.machine.motion_fault_latched == "E15 (new event)"
    assert rig.machine.clears == 1
    assert_no_commands(rig)
