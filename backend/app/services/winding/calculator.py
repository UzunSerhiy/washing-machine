import math


class WindingCalculator:
    """
    Расчёт параметров намотки материала на ролик.

    Модель:
    - двигатель: motor_rpm_at_max_frequency при max_frequency_hz;
    - редуктор: gear_ratio;
    - при увеличении диаметра рулона частота VFD уменьшается,
      чтобы сохранять постоянную линейную скорость материала;
    - speed_percent масштабирует всю базовую кривую скорости.
    """

    def __init__(
        self,
        core_diameter_mm: float,
        material_thickness_mm: float,
        motor_rpm_at_max_frequency: float = 905.0,
        max_frequency_hz: float = 50.0,
        gear_ratio: float = 100.0,
    ):
        if core_diameter_mm <= 0:
            raise ValueError("Core diameter must be greater than zero")

        if material_thickness_mm <= 0:
            raise ValueError("Material thickness must be greater than zero")

        if motor_rpm_at_max_frequency <= 0:
            raise ValueError("Motor RPM at max frequency must be greater than zero")

        if max_frequency_hz <= 0:
            raise ValueError("Max frequency must be greater than zero")

        if gear_ratio <= 0:
            raise ValueError("Gear ratio must be greater than zero")

        self.core_diameter_m = core_diameter_mm / 1000
        self.material_thickness_m = material_thickness_mm / 1000

        self.motor_rpm_at_max_frequency = motor_rpm_at_max_frequency
        self.max_frequency_hz = max_frequency_hz
        self.gear_ratio = gear_ratio

        self.wound_length_m = 0.0
        self.wound_turns = 0.0

    # ------------------------------------------------------------------
    # Basic machine parameters
    # ------------------------------------------------------------------

    @property
    def max_roller_rpm(self) -> float:
        """
        Максимальные обороты ролика при максимальной частоте VFD.

        Например:
            905 rpm / 100 = 9.05 rpm
        """

        return self.motor_rpm_at_max_frequency / self.gear_ratio

    @property
    def base_linear_speed_m_min(self) -> float:
        """
        Базовая линейная скорость материала при:
        - начальном диаметре;
        - максимальной частоте;
        - speed_percent = 100%.

        v = π * D * n
        """

        circumference_m = math.pi * self.core_diameter_m

        return circumference_m * self.max_roller_rpm

    # ------------------------------------------------------------------
    # Winding geometry
    # ------------------------------------------------------------------

    @property
    def current_diameter_m(self) -> float:
        """
        Текущий диаметр рулона.

        D = sqrt(
            D0² + 4 * t * L / π
        )
        """

        return math.sqrt(
            self.core_diameter_m**2
            + (4 * self.material_thickness_m * self.wound_length_m / math.pi)
        )

    @property
    def current_diameter_mm(self) -> float:
        return self.current_diameter_m * 1000

    # ------------------------------------------------------------------
    # Turns <-> material length
    # ------------------------------------------------------------------

    def length_for_turns(self, turns: float) -> float:
        """
        Рассчитывает длину материала после заданного количества
        полных оборотов ролика.

        L = π * D0 * N + π * t * N²
        """

        if turns < 0:
            raise ValueError("Turns cannot be negative")

        return (
            math.pi * self.core_diameter_m * turns
            + math.pi * self.material_thickness_m * turns**2
        )

    def turns_for_length(self, length_m: float) -> float:
        """
        Рассчитывает количество оборотов ролика для заданной
        длины намотанного материала.

        Решение квадратного уравнения:

        t*N² + D0*N - L/π = 0
        """

        if length_m < 0:
            raise ValueError("Length cannot be negative")

        if length_m == 0:
            return 0.0

        return (
            -self.core_diameter_m
            + math.sqrt(
                self.core_diameter_m**2
                + (4 * self.material_thickness_m * length_m / math.pi)
            )
        ) / (2 * self.material_thickness_m)

    def add_turns(self, turns: float) -> float:
        """
        Добавляет физические обороты ролика.

        Возвращает новое количество физических оборотов.
        """

        if turns < 0:
            raise ValueError("Turns cannot be negative")

        self.wound_turns += turns
        self.wound_length_m = self.length_for_turns(self.wound_turns)

        return self.wound_turns

    def add_length(self, length_m: float) -> float:
        """
        Добавляет длину намотанного материала.

        Возвращает новую длину материала.
        """

        if length_m < 0:
            raise ValueError("Length cannot be negative")

        self.wound_length_m += length_m
        self.wound_turns = self.turns_for_length(self.wound_length_m)

        return self.wound_length_m

    # ------------------------------------------------------------------
    # Speed calculation
    # ------------------------------------------------------------------

    def roller_rpm(self, speed_percent: float = 100.0) -> float:
        """
        Рассчитывает требуемые обороты ролика.

        При 100% сохраняется базовая линейная скорость.

        При увеличении диаметра рулона обороты уменьшаются.

        speed_percent:
            операторский множитель скорости.
            Например:
                100 -> 100%
                75  -> 75%
                50  -> 50%
        """

        self._validate_speed_percent(speed_percent)

        circumference_m = math.pi * self.current_diameter_m

        return self.base_linear_speed_m_min / circumference_m * speed_percent / 100

    def motor_rpm(self, speed_percent: float = 100.0) -> float:
        """
        Рассчитывает требуемые обороты двигателя.
        """

        return self.roller_rpm(speed_percent) * self.gear_ratio

    def frequency_hz(self, speed_percent: float = 100.0) -> float:
        """
        Рассчитывает частоту VFD.

        При 100% на начальном диаметре:
            frequency = max_frequency_hz

        При увеличении диаметра частота уменьшается.

        speed_percent масштабирует всю кривую.
        """

        motor_rpm = self.motor_rpm(speed_percent)

        return motor_rpm * self.max_frequency_hz / self.motor_rpm_at_max_frequency

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """
        Сбрасывает состояние намотки.
        """

        self.wound_length_m = 0.0
        self.wound_turns = 0.0

    @staticmethod
    def _validate_speed_percent(speed_percent: float) -> None:
        if not 0 < speed_percent <= 100:
            raise ValueError(
                "Speed percent must be greater than 0 and no more than 100"
            )
