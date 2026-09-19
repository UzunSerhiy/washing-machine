from app.core.config import settings
from app.services.drives.base import BaseDrive
from app.services.drives.fake import FakeDrive
from app.services.drives.gain import GainDrive
from app.services.modbus.client import ModbusClient


class DriveService:
    def __init__(self):
        self.mode = settings.DRIVE_MODE
        self.drives: dict[int, BaseDrive] = {}
        self.client: ModbusClient | None = None

        if self.mode == "real":
            self.client = ModbusClient(
                port=settings.SERIAL_PORT,
                baudrate=settings.BAUDTATE,
            )

    def connect(self) -> None:
        if self.client is None:
            return

        if not self.client.connect():
            raise RuntimeError("Failed to connect to RS485")

    def close(self) -> None:
        if self.client is not None:
            self.client.close()

    def add_drive(
        self,
        drive_id: int,
        address: int,
        drive_type: str,
        position: str | None,
    ) -> BaseDrive:
        if self.mode == "fake":
            drive = FakeDrive(
                device_id=drive_id,
            )
        elif self.mode == "real":
            if self.client is None:
                raise RuntimeError("Modbus client is not initialized")
            drive = GainDrive(client=self.client, device_id=address)
        else:
            raise ValueError(f"Unsupported drive mode: {self.mode}")

        self.drives[drive_id] = drive

        print(
            f"Drive configured: "
            f"id={drive_id}, "
            f"address={address}, "
            f"type={drive_type}, "
            f"position={position}"
        )

        return drive

    # def add_fake_drive(self, drive_id: int) -> BaseDrive:
    #     drive = FakeDrive(device_id=drive_id)
    #
    #     self.drives[drive_id] = drive
    #
    #     return drive
    #
    # def add_gain_drive(self, drive_id: int) -> BaseDrive:
    #     if self.client is None:
    #         raise RuntimeError("Modbus client is not initialized")
    #
    #     drive = GainDrive(
    #         client=self.client,
    #         device_id=drive_id,
    #     )
    #
    #     self.drives[drive_id] = drive
    #
    #     return drive

    def get_drive(self, drive_id: int) -> BaseDrive:
        drive = self.drives.get(drive_id)

        if drive is None:
            raise ValueError(f"Drive {drive_id} is not configured")

        return drive
