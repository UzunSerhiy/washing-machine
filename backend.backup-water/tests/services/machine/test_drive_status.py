from app.services.machine.drive_status import (
    DriveStatus,
    MachineDrivesStatus,
)


def test_drive_status_stores_diagnostics():
    status = DriveStatus(
        connected=True,
        faulted=False,
        running=False,
        frequency_hz=0.0,
    )

    assert status.connected is True
    assert status.faulted is False
    assert status.running is False
    assert status.frequency_hz == 0.0


def test_machine_drives_status_stores_both_drives():
    roller = DriveStatus(
        connected=True,
        faulted=False,
        running=False,
        frequency_hz=0.0,
    )

    brushes = DriveStatus(
        connected=True,
        faulted=True,
        running=False,
        frequency_hz=0.0,
    )

    status = MachineDrivesStatus(
        roller=roller,
        brushes=brushes,
    )

    assert status.roller is roller
    assert status.brushes is brushes

    assert status.roller.faulted is False
    assert status.brushes.faulted is True
