class RollerRotationCalculator:
    def __init__(self, motor_rpm_at_50hz: float, gear_ratio: float):
        if motor_rpm_at_50hz <= 0:
            raise ValueError("Motor must be greater than zero")

        if gear_ratio <= 0:
            raise ValueError("Gear ration must be greater than zero")

        self.motor_rpm_at_50hz = motor_rpm_at_50hz
        self.gear_ratio = gear_ratio

    def motor_rpm(
        self,
        frequency_hz: float,
    ) -> float:
        if frequency_hz < 0:
            raise ValueError("Frequency cannot be negative")

        return frequency_hz * self.motor_rpm_at_50hz / 50

    def roller_rpm(
        self,
        frequency_hz: float,
    ) -> float:
        return self.motor_rpm(frequency_hz) / self.gear_ratio

    def revolutions(
        self,
        frequency_hz: float,
        elapsed_second: float,
    ) -> float:
        if elapsed_second < 0:
            raise ValueError("Elapsed time cannot be negative")
        rpm = self.roller_rpm(frequency_hz)

        return rpm * elapsed_second / 60
