import pytest

from app.models.machine import Machine
from app.models.winding_parameters import WindingParameters
from app.services.winding.factory import WindingCalculatorFactory


def test_create_winding_calculator():
    machine = Machine(
        name="Washing Machine",
        roller_core_diameter_mm=200.0,
    )

    parameters = WindingParameters(
        material_profile_id=1,
        core_diameter_mm=None,
        material_thickness_mm=1,
    )

    calculator = WindingCalculatorFactory.create(
        machine=machine,
        parameters=parameters,
    )

    assert calculator.core_diameter_m == 0.2
    assert calculator.material_thickness_m == 0.001


def test_create_uses_machine_core_diameter():
    machine = Machine(
        name="Washing Machine",
        roller_core_diameter_mm=250.0,
    )

    parameters = WindingParameters(
        material_profile_id=1,
        core_diameter_mm=100,
        material_thickness_mm=1,
    )

    calculator = WindingCalculatorFactory.create(
        machine=machine,
        parameters=parameters,
    )

    assert calculator.core_diameter_m == 0.25


def test_create_requires_material_thickness():
    machine = Machine(
        name="Washing Machine",
        roller_core_diameter_mm=200.0,
    )

    parameters = WindingParameters(
        material_profile_id=1,
        core_diameter_mm=None,
        material_thickness_mm=None,
    )

    with pytest.raises(
        ValueError,
        match="Material thickness is not configured",
    ):
        WindingCalculatorFactory.create(
            machine=machine,
            parameters=parameters,
        )
