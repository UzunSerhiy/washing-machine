from app.services.drives.service import DriveService
from app.services.machine.brush import Brush
from app.services.machine.machine import Machine
from app.services.machine.roller import Roller


class MachineFactory:
    @staticmethod
    def create(drive_service: DriveService) -> Machine:
        left_drive = None
        right_drive = None
        roller_drive = None

        for drive_id, config in drive_service.configs.items():
            if not config.enabled:
                continue

            drive = drive_service.get_drive(drive_id)

            if config.type == "BRUSH":
                if config.position == "LEFT":
                    left_drive = drive
                elif config.position == "RIGHT":
                    right_drive = drive

            elif config.type == "ROLLER":
                roller_drive = drive

        if left_drive is None:
            raise ValueError("Left brush drive is not configured")

        if right_drive is None:
            raise ValueError("Right brush drive is not configured")

        if roller_drive is None:
            raise ValueError("Roller drive is not configured")

        return Machine(
            brush=Brush(
                left_drive=left_drive,
                right_drive=right_drive,
            ),
            roller=Roller(
                drive=roller_drive,
            ),
        )
