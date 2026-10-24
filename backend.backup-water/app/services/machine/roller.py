from app.services.drives.base import BaseDrive


class Roller:
    def __init__(self, drive: BaseDrive):
        self.drive = drive

    def forward(self, frequency_hz: float) -> None:
        self._validate_frequency(frequency_hz)
        self.drive.set_frequency(frequency_hz)
        self.drive.run_forward()

    def reverse(self, frequency_hz: float) -> None:
        self._validate_frequency(frequency_hz)
        self.drive.set_frequency(frequency_hz)
        self.drive.run_reverse()

    def stop(self) -> None:
        self.drive.stop()

    def stop_coast(self) -> None:
        self.drive.stop_coast()

    @staticmethod
    def _validate_frequency(frequency_hz: float) -> None:
        if frequency_hz < 0:
            raise ValueError("Frequency cannot be negative")
