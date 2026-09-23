import math


class WindingCalculator:
    def __init__(
        self,
        core_diameter_mm: float,
        material_thickness_mm: float,
    ):
        if core_diameter_mm <= 0:
            raise ValueError("Core diameter must be greater than zero")

        if material_thickness_mm <= 0:
            raise ValueError("Material thickness must be greater than zero")

        self.core_diameter_m = core_diameter_mm / 1000
        self.material_thickness_m = material_thickness_mm / 1000

        self.wound_length_m = 0.0

    @property
    def current_diameter_m(self) -> float:
        """
        Текущий диаметр рулона

        D = sqrt((D0 * D0) + 4 * t * L / Pi)
        """

        return math.sqrt(
            self.core_diameter_m**2
            + (4 * self.material_thickness_m * self.wound_length_m / math.pi)
        )

    @property
    def current_diameter_mm(self) -> float:
        return self.current_diameter_m * 1000

    def add_rotation(self, angle_rad: float) -> float:
        """
        Добавляет вращение вала.

        angle_rad:
            угол в радианах.

        Например:
            полный оборот = 2π
            половина      = π
            четверть      = π / 2

        Возвращает новую длину намотанного материала.
        """

        if angle_rad < 0:
            raise ValueError("Rotation angle cannot be negative")

        diameter = self.current_diameter_m

        added_length = diameter * angle_rad

        self.wound_length_m += added_length

        return self.wound_length_m

    def reset(self) -> None:
        """
        Сбросить накопленную длинну
        """

        self.wound_length_m = 0.0

    def roller_rpm(self, linear_speed_m_min: float) -> float:
        """
        Расчитать обороты ролика для заданной линейной склрости материала.

        linear_speed_m_min:
        m/min

        return:
            rmp/min
        """

        if linear_speed_m_min < 0:
            raise ValueError("Linear speed  cannot be negative")

        circumference_m = math.pi * self.current_diameter_m

        if circumference_m <= 0:
            raise ValueError("Invalid reller curcumference")

        return linear_speed_m_min / circumference_m
