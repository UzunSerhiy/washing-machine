from app.services.drives.base import BaseDrive
from app.services.modbus.client import ModbusClient


class GainDrive(BaseDrive):
    REG_FREQUENCY_SET = 0x1000
    REG_FREQUENCY_OUTPUT = 0x1001
    REG_COMMAND = 0x2000
    REG_STATUS = 0x3000
    REG_FAULT = 0x8000

    CMD_FORWARD = 0x0001
    CMD_REVERSE = 0x0002
    CMD_FORWARD_JOG = 0x0003
    CMD_REVERSE_JOG = 0x0004
    CMD_COAST_STOP = 0x0005
    CMD_DECEL_STOP = 0x0006
    CMD_FAULT_RESET = 0x0007

    STATUS_FORWARD = 0x0001
    STATUS_REVERSE = 0x0002
    STATUS_STOP = 0x0003

    def __init__(self, client: ModbusClient, device_id: int):
        self.client = client
        self.device_id = device_id

    def set_frequency(self, frequency_hz: float) -> None:
        value = int(frequency_hz * 100)

        if not 0 <= value <= 65535:
            raise ValueError("Invalid frequency")

        self.client.write_register(
            address=self.REG_FREQUENCY_SET,
            value=value,
            device_id=self.device_id,
        )

    def get_frequency(self) -> float:
        value = self.client.read_register(
            address=self.REG_FREQUENCY_OUTPUT,
            device_id=self.device_id,
        )

        return value / 100

    def get_status(self) -> int:
        return self.client.read_register(
            address=self.REG_STATUS,
            device_id=self.device_id,
        )

    def get_fault(self) -> int:
        return self.client.read_register(
            address=self.REG_FAULT,
            device_id=self.device_id,
        )

    def run_forward(self) -> None:
        self._send_command(self.CMD_FORWARD)

    def run_reverse(self) -> None:
        self._send_command(self.CMD_REVERSE)

    def stop(self) -> None:
        self._send_command(self.CMD_DECEL_STOP)

    def stop_coast(self) -> None:
        self._send_command(self.CMD_COAST_STOP)

    def reset_fault(self) -> None:
        self._send_command(self.CMD_FAULT_RESET)

    def _send_command(self, command: int) -> None:
        self.client.write_register(
            address=self.REG_COMMAND,
            value=command,
            device_id=self.device_id,
        )
