from app.services.drives.base import BaseDrive


class Brush:
    def __init__(
        self,
        left_drive: BaseDrive,
        right_drive: BaseDrive,
    ):
        self.left_drive = left_drive
        self.right_drive = right_drive

    def start(self, frequency_hz: float) -> None:
        if frequency_hz <= 0:
            raise ValueError("Frequency must be greater than zero")

        self.left_drive.set_frequency(frequency_hz)
        self.right_drive.set_frequency(frequency_hz)

        self.left_drive.run_forward()
        self.right_drive.run_reverse()

    def stop(self) -> None:
        self.left_drive.stop()
        self.right_drive.stop()
