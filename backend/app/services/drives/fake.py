from app.services.drives.base import BaseDrive


class FakeDrive(BaseDrive):
    STATUS_FORWARD = 0x0001
    STATUS_REVERSE = 0x0002
    STATUS_STOP = 0x0003

    def __init__(self, device_id: int):
        self.device_id = device_id

        self.frequency_hz = 0.0
        self.status = self.STATUS_STOP
        self.fault = 0

    def set_frequency(self, frequency_hz: float) -> None:
        if not 0 <= frequency_hz <= 100:
            raise ValueError("Invalid frequency")

        self.frequency_hz = frequency_hz

    def get_frequency(self) -> float:
        return self.frequency_hz

    def run_forward(self) -> None:
        self.status = self.STATUS_FORWARD

    def run_reverse(self) -> None:
        self.status = self.STATUS_REVERSE

    def stop(self) -> None:
        self.status = self.STATUS_STOP

    def stop_coast(self) -> None:
        self.status = self.STATUS_STOP

    def get_status(self) -> int:
        return self.status

    def get_fault(self) -> int:
        return self.fault

    def reset_fault(self) -> None:
        self.fault = 0
