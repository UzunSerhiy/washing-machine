from app.models.machine import Machine
from app.models.winding_parameters import WindingParameters
from app.services.winding.calculator import WindingCalculator


class WindingCalculatorFactory:
    @staticmethod
    def create(
        machine: Machine,
        parameters: WindingParameters,
    ) -> WindingCalculator:
        if parameters.material_thickness_mm is None:
            raise ValueError("Material thickness is not configured")

        return WindingCalculator(
            core_diameter_mm=machine.roller_core_diameter_mm,
            material_thickness_mm=parameters.material_thickness_mm,
        )
