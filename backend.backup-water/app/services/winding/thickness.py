class MaterialThicknessCalculator:
    def __init__(self, core_diameter_mm: float = 200.0):
        if core_diameter_mm <= 0:
            raise ValueError("Core diameter must be greater than zero")

        self.core_diameter_mm = core_diameter_mm

    def calculate(
        self,
        final_diameter_mm: float,
        turns: float,
    ) -> float:
        if final_diameter_mm <= self.core_diameter_mm:
            raise ValueError("Final diameter must be greater than core diameter")

        if turns <= 0:
            raise ValueError("Turns must be greate than zero")

        return (final_diameter_mm - self.core_diameter_mm) / (2 * turns)
