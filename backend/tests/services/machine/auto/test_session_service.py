import pytest

from app.services.machine.auto.session_service import AutoSessionService
from app.services.machine.operation import AutoStage, OperationMode
from app.services.machine.state import MachineOperationState
from app.services.speed.auto_settings import AutoSpeedSettings
from app.services.machine.calibration.data import CalibrationData


class FakeWindingParametersRepository:
    def __init__(self):
        self.calls = []

    async def load(
        self,
        session,
        material_profile_id,
    ):
        self.calls.append(
            (
                session,
                material_profile_id,
            )
        )

        parameters = type("WindingParameters", (), {})()
        parameters.material_thickness_mm = 1.5

        return parameters


class FakeCalibrationRepository:
    def __init__(self):
        self.calls = []

    async def load(self, db, machine_id, material_profile_id):
        self.calls.append((db, machine_id, material_profile_id))

        return CalibrationData(
            machine_id=machine_id,
            material_profile_id=material_profile_id,
            washing_stop_turns=15.0,
            material_start_turns=100.0,
            material_end_turns=180,
        )


class FakeOperationService:
    def __init__(self):
        self.state = MachineOperationState(
            mode=OperationMode.AUTO,
            auto_stage=AutoStage.WINDING,
            material_profile_id=7,
        )


class FakeSpeedSettingsService:
    def __init__(self):
        self.calls = []

    async def load(self, session, machine_id, stage):
        self.calls.append((session, machine_id, stage))

        return AutoSpeedSettings(
            stage=stage,
            mode_speed_percent=70.0,
            brush_speed_percent=None,
        )


class FakeMachineRepository:
    def __init__(self):
        self.calls = []

    async def load(
        self,
        session,
        machine_id,
    ):
        self.calls.append(
            (
                session,
                machine_id,
            )
        )

        machine = type("Machine", (), {})()
        machine.roller_core_diameter_mm = 200.0

        return machine


@pytest.mark.anyio
async def test_prepare_winding_loads_saved_stage_speed():
    operation_service = FakeOperationService()
    speed_settings_service = FakeSpeedSettingsService()
    calibration_repository = FakeCalibrationRepository()
    winding_parameters_repository = FakeWindingParametersRepository()
    machine_repository = FakeMachineRepository()

    service = AutoSessionService(
        machine_id=1,
        operation_service=operation_service,
        speed_settings_service=speed_settings_service,
        calibration_repository=calibration_repository,
        winding_parameters_repository=winding_parameters_repository,
        machine_repository=machine_repository,
    )

    fake_session = object()

    prepared = await service.prepare(fake_session)

    assert machine_repository.calls == [
        (
            fake_session,
            1,
        )
    ]

    assert prepared.machine is not None
    assert winding_parameters_repository.calls == [
        (
            fake_session,
            7,
        )
    ]

    assert prepared.winding_parameters is not None
    assert speed_settings_service.calls == [
        (
            fake_session,
            1,
            AutoStage.WINDING,
        )
    ]

    assert prepared.stage == AutoStage.WINDING
    assert prepared.material_profile_id == 7
    assert prepared.mode_speed_percent == pytest.approx(70.0)
    assert prepared.brush_speed_percent is None
    assert calibration_repository.calls == [
        (
            fake_session,
            1,
            7,
        )
    ]
    assert prepared.calibration.machine_id == 1
    assert prepared.calibration.material_profile_id == 7
    assert prepared.calibration.washing_stop_turns == pytest.approx(15.0)
    assert prepared.calibration.material_start_turns == pytest.approx(100.0)
    assert prepared.calibration.material_end_turns == pytest.approx(180.0)
    assert prepared.winding_calculator is not None
    assert prepared.winding_calculator.core_diameter_m == pytest.approx(0.2)
    assert prepared.winding_calculator.material_thickness_m == pytest.approx(0.0015)


@pytest.mark.anyio
async def test_prepare_requires_auto_mode():
    operation_service = FakeOperationService()
    operation_service.state.mode = OperationMode.MANUAL

    service = AutoSessionService(
        machine_id=1,
        operation_service=operation_service,
        speed_settings_service=FakeSpeedSettingsService(),
    )

    with pytest.raises(RuntimeError, match="Machine is not in auto mode"):
        await service.prepare(object())


@pytest.mark.anyio
async def test_prepare_requires_auto_stage():
    operation_service = FakeOperationService()
    operation_service.state.auto_stage = None

    service = AutoSessionService(
        machine_id=1,
        operation_service=operation_service,
        speed_settings_service=FakeSpeedSettingsService(),
    )

    with pytest.raises(RuntimeError, match="Auto stage is not selected"):
        await service.prepare(object())


@pytest.mark.anyio
async def test_prepare_requires_material_profile():
    operation_service = FakeOperationService()
    operation_service.state.material_profile_id = None

    service = AutoSessionService(
        machine_id=1,
        operation_service=operation_service,
        speed_settings_service=FakeSpeedSettingsService(),
    )

    with pytest.raises(RuntimeError, match="Material profile is not selected"):
        await service.prepare(object())
