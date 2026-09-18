from app.services.drives.base import BaseDrive
from app.services.drives.fake import FakeDrive


class DriveService:
    def __init__(self):
        self.drives: dict[int, BaseDrive] = {}

    def add_fake_drive(self, drive_id: int) -> BaseDrive:
        drive = FakeDrive(device_id=drive_id)

        self.drives[drive_id] = drive

        return drive

    def get_drive(self, drive_id: int) -> BaseDrive:
        drive = self.drives.get(drive_id)

        if drive is None:
            raise ValueError(f"Drive {drive_id} is not configured")

        return drive
