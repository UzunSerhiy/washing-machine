from unittest.mock import Mock

import pytest

from app.services.drives.service import DriveConfig, DriveService
from app.services.machine.factory import MachineFactory
from app.services.machine.machine import Machine


def create_drive_service():
    service = DriveService()

    left_drive = Mock()
    right_drive = Mock()
    roller_drive = Mock()

    service.drives = {
        1: left_drive,
        2: right_drive,
        3: roller_drive,
    }

    service.configs = {
        1: DriveConfig(
            id=1,
            address=3,
            name="Brush Left",
            type="BRUSH",
            position="LEFT",
            enabled=True,
        ),
        2: DriveConfig(
            id=2,
            address=2,
            name="Brush Right",
            type="BRUSH",
            position="RIGHT",
            enabled=True,
        ),
        3: DriveConfig(
            id=3,
            address=1,
            name="Roller",
            type="ROLLER",
            position=None,
            enabled=True,
        ),
    }

    return service, left_drive, right_drive, roller_drive


def test_create_machine():
    drive_service, left_drive, right_drive, roller_drive = create_drive_service()

    machine = MachineFactory.create(drive_service)

    assert isinstance(machine, Machine)
    assert machine.brush.left_drive is left_drive
    assert machine.brush.right_drive is right_drive
    assert machine.roller.drive is roller_drive


def test_create_requires_left_brush():
    drive_service, _, _, _ = create_drive_service()

    del drive_service.configs[1]
    del drive_service.drives[1]

    with pytest.raises(
        ValueError,
        match="Left brush drive is not configured",
    ):
        MachineFactory.create(drive_service)


def test_create_requires_right_brush():
    drive_service, _, _, _ = create_drive_service()

    del drive_service.configs[2]
    del drive_service.drives[2]

    with pytest.raises(
        ValueError,
        match="Right brush drive is not configured",
    ):
        MachineFactory.create(drive_service)


def test_create_requires_roller():
    drive_service, _, _, _ = create_drive_service()

    del drive_service.configs[3]
    del drive_service.drives[3]

    with pytest.raises(
        ValueError,
        match="Roller drive is not configured",
    ):
        MachineFactory.create(drive_service)
