import pytest
from app.models.machine_calibration import MachineCalibrationSettings
from app.models.winding_calibration import (
    WindingCalibration as WindingCalibrationModel,
)
from app.services.machine.calibration.repository import CalibrationRepository
from app.services.machine.calibration.session import CalibrationSession
from app.services.machine.calibration.points import CalibrationPoint
from app.services.winding.rotation import RollerRotationCalculator
from app.services.machine.calibration.data import CalibrationData
from app.models.winding_parameters import WindingParameters


class FakeMachine:
    def start_roller_forward(self, frequency_hz: float) -> None:
        pass

    def start_roller_reverse(self, frequency_hz: float) -> None:
        pass

    def stop_roller(self) -> None:
        pass


class FakeResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class FakeSession:
    def __init__(self, results=None):
        self.results = list(results or [])
        self.added = []

    async def execute(self, statement):
        if not self.results:
            raise AssertionError("Unexpected database query")

        return FakeResult(self.results.pop(0))

    def add(self, model):
        self.added.append(model)


def create_calibration_session(
    material_profile_id: int = 1,
) -> CalibrationSession:
    session = CalibrationSession(
        machine=FakeMachine(),
        rotation_calculator=RollerRotationCalculator(
            motor_rpm_at_50hz=905,
            gear_ratio=100,
        ),
        material_profile_id=material_profile_id,
    )

    session.position_tracker.set_position(3.0)
    session.set_point(CalibrationPoint.WASHING_STOP)

    session.position_tracker.set_position(10.0)
    session.set_point(CalibrationPoint.MATERIAL_START)

    session.position_tracker.set_position(35.0)
    session.set_point(CalibrationPoint.MATERIAL_END)

    return session


@pytest.mark.anyio
async def test_save_creates_machine_calibration() -> None:
    db = FakeSession(
        results=[
            None,
            None,
        ]
    )

    repository = CalibrationRepository()
    calibration_session = create_calibration_session()

    await repository.save(
        db=db,
        machine_id=1,
        calibration_session=calibration_session,
    )

    machine_models = [
        model for model in db.added if isinstance(model, MachineCalibrationSettings)
    ]

    assert len(machine_models) == 1

    model = machine_models[0]

    assert model.machine_id == 1
    assert model.washing_stop_turns == 3.0
    assert model.material_start_turns == 10.0


@pytest.mark.anyio
async def test_save_creates_winding_calibration() -> None:
    db = FakeSession(
        results=[
            None,
            None,
        ]
    )

    repository = CalibrationRepository()
    calibration_session = create_calibration_session(
        material_profile_id=5,
    )

    await repository.save(
        db=db,
        machine_id=1,
        calibration_session=calibration_session,
    )

    winding_models = [
        model for model in db.added if isinstance(model, WindingCalibrationModel)
    ]

    assert len(winding_models) == 1

    model = winding_models[0]

    assert model.material_profile_id == 5
    assert model.material_end_turns == 35.0


@pytest.mark.anyio
async def test_save_updates_existing_calibrations() -> None:
    machine_model = MachineCalibrationSettings(
        machine_id=1,
        washing_stop_turns=1.0,
        material_start_turns=2.0,
    )

    winding_model = WindingCalibrationModel(
        material_profile_id=1,
        material_end_turns=5.0,
    )

    db = FakeSession(
        results=[
            machine_model,
            winding_model,
        ]
    )

    repository = CalibrationRepository()
    calibration_session = create_calibration_session()

    await repository.save(
        db=db,
        machine_id=1,
        calibration_session=calibration_session,
    )

    assert db.added == []

    assert machine_model.washing_stop_turns == 3.0
    assert machine_model.material_start_turns == 10.0
    assert winding_model.material_end_turns == 35.0


@pytest.mark.anyio
async def test_save_rejects_incomplete_calibration() -> None:
    db = FakeSession()

    repository = CalibrationRepository()

    calibration_session = CalibrationSession(
        machine=FakeMachine(),
        rotation_calculator=RollerRotationCalculator(
            motor_rpm_at_50hz=905,
            gear_ratio=100,
        ),
        material_profile_id=1,
    )

    with pytest.raises(
        ValueError,
        match="Material start point is not calibrated",
    ):
        await repository.save(
            db=db,
            machine_id=1,
            calibration_session=calibration_session,
        )

    assert db.added == []


@pytest.mark.anyio
async def test_save_different_material_uses_selected_material_profile() -> None:
    machine_model = MachineCalibrationSettings(
        machine_id=1,
        washing_stop_turns=3.0,
        material_start_turns=10.0,
    )

    db = FakeSession(
        results=[
            machine_model,
            None,
        ]
    )

    repository = CalibrationRepository()

    calibration_session = create_calibration_session(
        material_profile_id=8,
    )

    await repository.save(
        db=db,
        machine_id=1,
        calibration_session=calibration_session,
    )

    assert len(db.added) == 1

    winding_model = db.added[0]

    assert isinstance(
        winding_model,
        WindingCalibrationModel,
    )
    assert winding_model.material_profile_id == 8
    assert winding_model.material_end_turns == 35.0

    # Общая калибровка машины остаётся той же записью.
    assert machine_model.washing_stop_turns == 3.0
    assert machine_model.material_start_turns == 10.0


@pytest.mark.anyio
async def test_load_returns_saved_calibration() -> None:
    machine_calibration = MachineCalibrationSettings(
        machine_id=1,
        washing_stop_turns=5.0,
        material_start_turns=12.0,
    )

    winding_calibration = WindingCalibrationModel(
        material_profile_id=3,
        material_end_turns=40.0,
    )

    db = FakeSession(
        results=[
            machine_calibration,
            winding_calibration,
        ]
    )

    repository = CalibrationRepository()

    data = await repository.load(
        db=db,
        machine_id=1,
        material_profile_id=3,
    )

    assert isinstance(data, CalibrationData)

    assert data.machine_id == 1
    assert data.material_profile_id == 3

    assert data.washing_stop_turns == 5.0
    assert data.material_start_turns == 12.0
    assert data.material_end_turns == 40.0


@pytest.mark.anyio
async def test_load_requires_machine_calibration() -> None:
    db = FakeSession(
        results=[
            None,
        ]
    )

    repository = CalibrationRepository()

    with pytest.raises(
        RuntimeError,
        match="Machine calibration not found",
    ):
        await repository.load(
            db=db,
            machine_id=1,
            material_profile_id=3,
        )


@pytest.mark.anyio
async def test_load_requires_material_calibration() -> None:
    machine_calibration = MachineCalibrationSettings(
        machine_id=1,
        washing_stop_turns=5.0,
        material_start_turns=12.0,
    )

    db = FakeSession(
        results=[
            machine_calibration,
            None,
        ]
    )

    repository = CalibrationRepository()

    with pytest.raises(
        RuntimeError,
        match="Material calibration not found",
    ):
        await repository.load(
            db=db,
            machine_id=1,
            material_profile_id=3,
        )


@pytest.mark.anyio
async def test_save_updates_winding_parameters_from_calibration() -> None:
    machine_model = MachineCalibrationSettings(
        machine_id=1,
        washing_stop_turns=3.0,
        material_start_turns=10.0,
    )

    winding_model = WindingCalibrationModel(
        material_profile_id=1,
        material_end_turns=35.0,
    )

    parameters = WindingParameters(
        material_profile_id=1,
        core_diameter_mm=200.0,
    )

    db = FakeSession(
        results=[
            machine_model,
            winding_model,
            parameters,
        ]
    )

    repository = CalibrationRepository()
    calibration_session = create_calibration_session()

    await repository.save(
        db=db,
        machine_id=1,
        calibration_session=calibration_session,
        final_diameter_mm=225.0,
    )

    assert parameters.calibration_turns == pytest.approx(25.0)
    assert parameters.calibration_final_diameter_mm == pytest.approx(225.0)
    assert parameters.material_thickness_mm == pytest.approx(0.5)


@pytest.mark.anyio
async def test_save_requires_winding_parameters() -> None:
    machine_model = MachineCalibrationSettings(
        machine_id=1,
        washing_stop_turns=3.0,
        material_start_turns=10.0,
    )

    winding_model = WindingCalibrationModel(
        material_profile_id=1,
        material_end_turns=35.0,
    )

    db = FakeSession(
        results=[
            machine_model,
            winding_model,
            None,
        ]
    )

    repository = CalibrationRepository()
    calibration_session = create_calibration_session()

    with pytest.raises(
        RuntimeError,
        match="Winding parameters not found",
    ):
        await repository.save(
            db=db,
            machine_id=1,
            calibration_session=calibration_session,
            final_diameter_mm=225.0,
        )
