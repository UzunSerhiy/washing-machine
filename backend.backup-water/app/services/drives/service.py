from dataclasses import dataclass

from app.core.config import settings
from app.services.drives.base import BaseDrive
from app.services.drives.fake import FakeDrive
from app.services.drives.gain import GainDrive
from app.services.modbus.client import ModbusClient


@dataclass
class DriveConfig:
    id: int
    address: int
    name: str
    type: str
    position: str | None
    enabled: bool


class DriveService:
    def __init__(self):
        self.mode = settings.DRIVE_MODE

        self.drives: dict[int, BaseDrive] = {}
        self.configs: dict[int, DriveConfig] = {}

        self.client: ModbusClient | None = None

        if self.mode == "real":
            self.client = ModbusClient(
                port=settings.SERIAL_PORT,
                baudrate=settings.BAUDRATE,
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
        name: str,
        drive_type: str,
        position: str | None,
        enabled: bool,
    ) -> BaseDrive:
        if self.mode == "fake":
            drive = FakeDrive(
                device_id=drive_id,
            )

        elif self.mode == "real":
            if self.client is None:
                raise RuntimeError("Modbus client is not initialized")

            drive = GainDrive(
                client=self.client,
                device_id=address,
            )

        else:
            raise ValueError(f"Unsupported drive mode: {self.mode}")

        self.drives[drive_id] = drive

        self.configs[drive_id] = DriveConfig(
            id=drive_id,
            address=address,
            name=name,
            type=drive_type,
            position=position,
            enabled=enabled,
        )

        print(
            f"Drive configured: "
            f"id={drive_id}, "
            f"address={address}, "
            f"type={drive_type}, "
            f"position={position}"
        )

        return drive

    def get_drive(self, drive_id: int) -> BaseDrive:
        drive = self.drives.get(drive_id)

        if drive is None:
            raise ValueError(f"Drive {drive_id} is not configured")

        return drive
