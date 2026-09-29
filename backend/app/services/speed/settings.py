class RuntimeSpeedSettings:
    def __init__(
        self,
        belt_speed_percent: float,
        material_speed_percent: float,
        brush_speed_percent: float | None,
    ):
        self.set_belt_speed(belt_speed_percent)
        self.set_material_speed(material_speed_percent)

        if brush_speed_percent is not None:
            self.set_brush_speed(brush_speed_percent)
        else:
            self.brush_speed_percent = None

    def set_belt_speed(self, speed_percent: float) -> None:
        self._validate_speed_percent(speed_percent)

        self.belt_speed_percent = speed_percent

    def set_material_speed(self, speed_percent: float) -> None:
        self._validate_speed_percent(speed_percent)

        self.material_speed_percent = speed_percent

    def set_brush_speed(self, speed_percent: float) -> None:
        if speed_percent is not None:
            self._validate_speed_percent(speed_percent)
        self.brush_speed_percent = speed_percent

    @staticmethod
    def _validate_speed_percent(speed_percent: float) -> None:
        if not 0 < speed_percent <= 100:
            raise ValueError(
                "Speed percent must be greater than 0 and no more than 100"
            )
