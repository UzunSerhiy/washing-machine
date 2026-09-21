from app.services.drives.service import DriveService


class MachineService:
    def __init__(self, drive_service: DriveService):
        self.drive_service = drive_service

    def start(self) -> None:
        """
        Starts all configured drives in the forward direction.
        """
        for drive_id in sorted(self.drive_service.drives):
            drive = self.drive_service.get_drive(drive_id)
            drive.run_forward()

    def stop(self) -> None:
        """
        Stops all configured drives with deceleration.
        """
        for drive_id in sorted(
            self.drive_service.drives,
            reverse=True,
        ):
            drive = self.drive_service.get_drive(drive_id)
            drive.stop()
