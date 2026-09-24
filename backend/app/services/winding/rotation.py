class RollerRotationCalculator:
    """
    Рассчитывает обороты выходного вала ролика
    по частоте VFD, оборотам двигателя и передаточному
    отношению редуктора.

    Класс не хранит состояние.
    Он только выполняет физические расчёты.
    """

    def __init__(
        self,
        motor_rpm_at_50hz: float,
        gear_ratio: float,
    ):
        if motor_rpm_at_50hz <= 0:
            raise ValueError("Motor RPM must be greater than zero")

        if gear_ratio <= 0:
            raise ValueError("Gear ratio must be greater than zero")

        self.motor_rpm_at_50hz = motor_rpm_at_50hz
        self.gear_ratio = gear_ratio

    def motor_rpm(
        self,
        frequency_hz: float,
    ) -> float:
        """
        Рассчитывает обороты двигателя по частоте VFD.

        Например:

        50 Hz -> 905 rpm
        25 Hz -> 452.5 rpm
        """

        if frequency_hz < 0:
            raise ValueError("Frequency cannot be negative")

        return frequency_hz * self.motor_rpm_at_50hz / 50

    def roller_rpm(
        self,
        frequency_hz: float,
    ) -> float:
        """
        Рассчитывает обороты выходного вала ролика.
        """

        return self.motor_rpm(frequency_hz) / self.gear_ratio

    def revolutions_for_time(
        self,
        frequency_hz: float,
        elapsed_seconds: float,
    ) -> float:
        """
        Рассчитывает количество физических оборотов ролика
        за заданное время.
        """

        if elapsed_seconds < 0:
            raise ValueError("Elapsed time cannot be negative")

        rpm = self.roller_rpm(frequency_hz)

        return rpm * elapsed_seconds / 60
