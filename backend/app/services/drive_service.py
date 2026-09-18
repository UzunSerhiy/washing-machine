from app.core.config import settings
from app.services.modbus.client import ModbusClient
from app.services.modbus.gain import GainDrive


class DriveService:
    def __init__(self):
        self.client = ModbusClient(
            port=settings.SERIAL_PORT,
            baudrate=settings.BAUDTATE,
        )

        self.drives: dict[int, GainDrive] = {}

    def connect(self) -> None:
        if not self.client.connect():
            raise RuntimeError("Failed to connect to RS485")

    def close(self) -> None:
        self.client.close()

    def add_drive(self, drive_id: int) -> GainDrive:
        drive = GainDrive(
            client=self.client,
            device_id=drive_id,
        )

        self.drives[drive_id] = drive

        return drive

    def get_drive(self, drive_id: int) -> GainDrive:
        drive = self.drives.get(drive_id)

        if drive is None:
            raise ValueError(f"Drive {drive_id} is not configured")

        return drive
