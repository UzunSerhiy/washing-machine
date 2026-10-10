import pytest
import asyncio

from app.services.machine.auto.runtime import AutoRuntime
from app.services.machine.auto.session_service import AutoSessionService
from app.services.machine.operation import AutoStage, OperationMode
from app.services.machine.state import MachineOperationState
from app.services.speed.auto_settings import AutoSpeedSettings
from app.services.machine.calibration.data import CalibrationData
from app.services.machine.controller.winding import WindingController


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


class FakePhysicalMachine:
    def __init__(self):
        self.start_roller_forward_calls = []
        self.stop_roller_calls = 0

    def start_roller_forward(self, frequency_hz):
        self.start_roller_forward_calls.append(frequency_hz)

    def stop_roller(self):
        self.stop_roller_calls += 1


class FakeOperationService:
    def __init__(self):
        self.state = MachineOperationState(
            mode=OperationMode.AUTO,
            auto_stage=AutoStage.WINDING,
            material_profile_id=7,
        )

        self.machine = FakePhysicalMachine()

    @property
    def start_roller_forward_calls(self):
        return self.machine.start_roller_forward_calls

    @property
    def stop_roller_calls(self):
        return self.machine.stop_roller_calls


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
    assert isinstance(
        prepared.controller,
        WindingController,
    )

    assert prepared.controller.position_turns == pytest.approx(0.0)

    assert prepared.controller.machine_calibration.washing_stop_turns == pytest.approx(
        15.0
    )

    assert (
        prepared.controller.machine_calibration.material_start_turns
        == pytest.approx(100.0)
    )

    assert prepared.controller.winding_calibration.material_end_turns == pytest.approx(
        180.0
    )

    assert prepared.controller.winding_calculator is prepared.winding_calculator

    assert prepared.controller.rotation_calculator.motor_rpm_at_50hz == pytest.approx(
        905.0
    )

    assert prepared.controller.rotation_calculator.gear_ratio == pytest.approx(100.0)

    assert prepared.controller.machine is operation_service.machine


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


@pytest.mark.anyio
async def test_prepare_does_not_start_winding():
    operation_service = FakeOperationService()

    service = AutoSessionService(
        machine_id=1,
        operation_service=operation_service,
        speed_settings_service=FakeSpeedSettingsService(),
        calibration_repository=FakeCalibrationRepository(),
        winding_parameters_repository=FakeWindingParametersRepository(),
        machine_repository=FakeMachineRepository(),
    )

    prepared = await service.prepare(object())

    assert isinstance(prepared.controller, WindingController)

    assert operation_service.start_roller_forward_calls == []
    assert operation_service.stop_roller_calls == 0

    assert prepared.controller.position_turns == pytest.approx(0.0)


@pytest.mark.anyio
async def test_start_winding_starts_roller_forward():
    operation_service = FakeOperationService()

    service = AutoSessionService(
        machine_id=1,
        operation_service=operation_service,
        speed_settings_service=FakeSpeedSettingsService(),
        calibration_repository=FakeCalibrationRepository(),
        winding_parameters_repository=FakeWindingParametersRepository(),
        machine_repository=FakeMachineRepository(),
    )

    await service.prepare(object())

    service.start()

    assert operation_service.start_roller_forward_calls == [pytest.approx(35.0)]

    assert service.operation_service.state.running is True
    assert service.operation_service.state.paused is False


def test_start_requires_prepared_stage():
    service = AutoSessionService(
        machine_id=1,
        operation_service=FakeOperationService(),
        speed_settings_service=FakeSpeedSettingsService(),
    )

    with pytest.raises(
        RuntimeError,
        match="Auto stage is not prepared",
    ):
        service.start()


@pytest.mark.anyio
async def test_tick_updates_winding_position():
    operation_service = FakeOperationService()

    service = AutoSessionService(
        machine_id=1,
        operation_service=operation_service,
        speed_settings_service=FakeSpeedSettingsService(),
        calibration_repository=FakeCalibrationRepository(),
        winding_parameters_repository=FakeWindingParametersRepository(),
        machine_repository=FakeMachineRepository(),
    )

    prepared = await service.prepare(object())

    service.start()

    initial_position = prepared.controller.position_turns

    service.tick(elapsed_seconds=1.0)

    assert prepared.controller.position_turns > initial_position

    assert prepared.controller.position_turns == pytest.approx(
        35.0 * 905.0 / 50.0 / 100.0 / 60.0
    )


@pytest.mark.anyio
async def test_winding_completes_at_material_end():
    operation_service = FakeOperationService()

    service = AutoSessionService(
        machine_id=1,
        operation_service=operation_service,
        speed_settings_service=FakeSpeedSettingsService(),
        calibration_repository=FakeCalibrationRepository(),
        winding_parameters_repository=FakeWindingParametersRepository(),
        machine_repository=FakeMachineRepository(),
    )

    prepared = await service.prepare(object())

    # Начинаем непосредственно перед MATERIAL_END.
    prepared.controller.position_tracker.set_position(179.99)

    service.start()

    service.tick(elapsed_seconds=1.0)

    assert prepared.controller.completed is True
    assert prepared.controller.position_turns == pytest.approx(180.0)

    assert operation_service.stop_roller_calls == 1
    assert operation_service.state.running is False
    assert operation_service.state.auto_stage == AutoStage.WINDING

    # После завершения новые команды не отправляются.
    start_calls = len(operation_service.start_roller_forward_calls)

    service.tick(elapsed_seconds=1.0)

    assert len(operation_service.start_roller_forward_calls) == start_calls
    assert operation_service.stop_roller_calls == 1


@pytest.mark.anyio
async def test_pause_winding_stops_roller_and_preserves_position():
    operation_service = FakeOperationService()

    service = AutoSessionService(
        machine_id=1,
        operation_service=operation_service,
        speed_settings_service=FakeSpeedSettingsService(),
        calibration_repository=FakeCalibrationRepository(),
        winding_parameters_repository=FakeWindingParametersRepository(),
        machine_repository=FakeMachineRepository(),
    )

    prepared = await service.prepare(object())

    service.start()
    service.tick(elapsed_seconds=1.0)

    position_before_pause = prepared.controller.position_turns

    service.pause()

    assert operation_service.stop_roller_calls == 1
    assert operation_service.state.running is False
    assert operation_service.state.paused is True

    service.tick(elapsed_seconds=5.0)

    assert prepared.controller.position_turns == pytest.approx(position_before_pause)
    assert operation_service.stop_roller_calls == 1


@pytest.mark.anyio
async def test_resume_winding_continues_from_paused_position():
    operation_service = FakeOperationService()

    service = AutoSessionService(
        machine_id=1,
        operation_service=operation_service,
        speed_settings_service=FakeSpeedSettingsService(),
        calibration_repository=FakeCalibrationRepository(),
        winding_parameters_repository=FakeWindingParametersRepository(),
        machine_repository=FakeMachineRepository(),
    )

    prepared = await service.prepare(object())

    service.start()
    service.tick(elapsed_seconds=1.0)
    service.pause()

    paused_position = prepared.controller.position_turns

    service.resume()

    assert operation_service.state.running is True
    assert operation_service.state.paused is False

    # После возобновления частотник получил новую команду запуска.
    assert len(operation_service.start_roller_forward_calls) == 3

    # Позиция при возобновлении не сбрасывается.
    assert prepared.controller.position_turns == pytest.approx(paused_position)

    service.tick(elapsed_seconds=1.0)

    assert prepared.controller.position_turns > paused_position


@pytest.mark.anyio
async def test_resume_requires_paused_state():
    service = AutoSessionService(
        machine_id=1,
        operation_service=FakeOperationService(),
        speed_settings_service=FakeSpeedSettingsService(),
        calibration_repository=FakeCalibrationRepository(),
        winding_parameters_repository=FakeWindingParametersRepository(),
        machine_repository=FakeMachineRepository(),
    )

    await service.prepare(object())

    service.start()

    with pytest.raises(
        RuntimeError,
        match="Auto stage is not paused",
    ):
        service.resume()


@pytest.mark.anyio
async def test_stop_winding_ends_auto_session():
    operation_service = FakeOperationService()

    service = AutoSessionService(
        machine_id=1,
        operation_service=operation_service,
        speed_settings_service=FakeSpeedSettingsService(),
        calibration_repository=FakeCalibrationRepository(),
        winding_parameters_repository=FakeWindingParametersRepository(),
        machine_repository=FakeMachineRepository(),
    )

    prepared = await service.prepare(object())

    service.start()
    service.tick(elapsed_seconds=1.0)

    service.stop()

    assert operation_service.stop_roller_calls == 1
    assert operation_service.state.running is False
    assert operation_service.state.paused is False

    # Подготовленная сессия больше недоступна.
    assert service._prepared is None

    # Этап остаётся выбранным.
    assert operation_service.state.auto_stage == AutoStage.WINDING

    with pytest.raises(
        RuntimeError,
        match="Auto stage is not prepared",
    ):
        service.resume()

    # Повторный tick не должен продолжать движение.
    position_after_stop = prepared.controller.position_turns

    service.tick(elapsed_seconds=1.0)

    assert prepared.controller.position_turns == pytest.approx(position_after_stop)


@pytest.mark.anyio
async def test_runtime_drives_winding_session():
    operation_service = FakeOperationService()

    service = AutoSessionService(
        machine_id=1,
        operation_service=operation_service,
        speed_settings_service=FakeSpeedSettingsService(),
        calibration_repository=FakeCalibrationRepository(),
        winding_parameters_repository=FakeWindingParametersRepository(),
        machine_repository=FakeMachineRepository(),
    )

    prepared = await service.prepare(object())
    service.start()

    runtime = AutoRuntime(
        auto_service=service,
        interval_seconds=0.01,
    )

    await runtime.start()

    try:
        await asyncio.sleep(0.05)
    finally:
        await runtime.stop()

    assert prepared.controller.position_turns > 0
    assert len(operation_service.start_roller_forward_calls) > 1


@pytest.mark.anyio
async def test_tick_failure_clears_running_state():
    operation_service = FakeOperationService()

    service = AutoSessionService(
        machine_id=1,
        operation_service=operation_service,
        speed_settings_service=FakeSpeedSettingsService(),
        calibration_repository=FakeCalibrationRepository(),
        winding_parameters_repository=FakeWindingParametersRepository(),
        machine_repository=FakeMachineRepository(),
    )

    await service.prepare(object())
    service.start()

    def failing_start_roller_forward(frequency_hz):
        raise OSError("RS-485 communication failed")

    operation_service.machine.start_roller_forward = failing_start_roller_forward

    with pytest.raises(
        OSError,
        match="RS-485 communication failed",
    ):
        service.tick(elapsed_seconds=0.1)

    assert operation_service.state.running is False
    assert operation_service.state.paused is False


@pytest.mark.anyio
async def test_start_failure_keeps_machine_stopped():
    operation_service = FakeOperationService()

    service = AutoSessionService(
        machine_id=1,
        operation_service=operation_service,
        speed_settings_service=FakeSpeedSettingsService(),
        calibration_repository=FakeCalibrationRepository(),
        winding_parameters_repository=FakeWindingParametersRepository(),
        machine_repository=FakeMachineRepository(),
    )

    await service.prepare(object())

    def failing_start_roller_forward(frequency_hz):
        raise OSError("RS-485 communication failed")

    operation_service.machine.start_roller_forward = failing_start_roller_forward

    with pytest.raises(
        OSError,
        match="RS-485 communication failed",
    ):
        service.start()

    assert operation_service.state.running is False
    assert operation_service.state.paused is False


@pytest.mark.anyio
async def test_tick_update_failure_clears_running_state():
    operation_service = FakeOperationService()

    service = AutoSessionService(
        machine_id=1,
        operation_service=operation_service,
        speed_settings_service=FakeSpeedSettingsService(),
        calibration_repository=FakeCalibrationRepository(),
        winding_parameters_repository=FakeWindingParametersRepository(),
        machine_repository=FakeMachineRepository(),
    )

    prepared = await service.prepare(object())
    service.start()

    def failing_update(
        belt_frequency_hz,
        speed_percent,
        elapsed_seconds,
    ):
        raise RuntimeError("Position calculation failed")

    prepared.controller.update = failing_update

    with pytest.raises(
        RuntimeError,
        match="Position calculation failed",
    ):
        service.tick(elapsed_seconds=0.1)

    assert operation_service.state.running is False
    assert operation_service.state.paused is False


@pytest.mark.anyio
async def test_cannot_restart_after_tick_failure():
    operation_service = FakeOperationService()

    service = AutoSessionService(
        machine_id=1,
        operation_service=operation_service,
        speed_settings_service=FakeSpeedSettingsService(),
        calibration_repository=FakeCalibrationRepository(),
        winding_parameters_repository=FakeWindingParametersRepository(),
        machine_repository=FakeMachineRepository(),
    )

    prepared = await service.prepare(object())
    service.start()

    def failing_update(
        belt_frequency_hz,
        speed_percent,
        elapsed_seconds,
    ):
        raise RuntimeError("Position calculation failed")

    prepared.controller.update = failing_update

    with pytest.raises(
        RuntimeError,
        match="Position calculation failed",
    ):
        service.tick(elapsed_seconds=0.1)

    assert operation_service.state.running is False

    with pytest.raises(RuntimeError, match="fault"):
        service.start()


@pytest.mark.anyio
async def test_cannot_resume_after_fault():
    operation_service = FakeOperationService()

    service = AutoSessionService(
        machine_id=1,
        operation_service=operation_service,
        speed_settings_service=FakeSpeedSettingsService(),
        calibration_repository=FakeCalibrationRepository(),
        winding_parameters_repository=FakeWindingParametersRepository(),
        machine_repository=FakeMachineRepository(),
    )

    prepared = await service.prepare(object())
    service.start()

    def failing_update(
        belt_frequency_hz,
        speed_percent,
        elapsed_seconds,
    ):
        raise RuntimeError("Position calculation failed")

    prepared.controller.update = failing_update

    with pytest.raises(
        RuntimeError,
        match="Position calculation failed",
    ):
        service.tick(elapsed_seconds=0.1)

    assert service._faulted is True

    # Имитируем попытку восстановить состояние PAUSE.
    operation_service.state.paused = True

    with pytest.raises(RuntimeError, match="fault"):
        service.resume()

    assert operation_service.state.running is False
    assert (
        operation_service.start_roller_forward_calls
        == (operation_service.start_roller_forward_calls[:1])
    )


@pytest.mark.anyio
async def test_start_failure_enters_fault_state():
    operation_service = FakeOperationService()

    service = AutoSessionService(
        machine_id=1,
        operation_service=operation_service,
        speed_settings_service=FakeSpeedSettingsService(),
        calibration_repository=FakeCalibrationRepository(),
        winding_parameters_repository=FakeWindingParametersRepository(),
        machine_repository=FakeMachineRepository(),
    )

    await service.prepare(object())

    def failing_start_roller_forward(frequency_hz):
        raise OSError("RS-485 communication failed")

    operation_service.machine.start_roller_forward = failing_start_roller_forward

    with pytest.raises(
        OSError,
        match="RS-485 communication failed",
    ):
        service.start()

    assert service._faulted is True
    assert operation_service.state.running is False
    assert operation_service.state.paused is False

    with pytest.raises(RuntimeError, match="fault"):
        service.start()


@pytest.mark.anyio
async def test_resume_failure_enters_fault_state():
    operation_service = FakeOperationService()

    service = AutoSessionService(
        machine_id=1,
        operation_service=operation_service,
        speed_settings_service=FakeSpeedSettingsService(),
        calibration_repository=FakeCalibrationRepository(),
        winding_parameters_repository=FakeWindingParametersRepository(),
        machine_repository=FakeMachineRepository(),
    )

    await service.prepare(object())
    service.start()
    service.pause()

    assert operation_service.state.paused is True

    def failing_start_roller_forward(frequency_hz):
        raise OSError("RS-485 communication failed")

    operation_service.machine.start_roller_forward = failing_start_roller_forward

    with pytest.raises(
        OSError,
        match="RS-485 communication failed",
    ):
        service.resume()

    assert service._faulted is True
    assert operation_service.state.running is False
    assert operation_service.state.paused is False

    with pytest.raises(RuntimeError, match="fault"):
        service.resume()


@pytest.mark.anyio
async def test_stop_does_not_clear_fault():
    operation_service = FakeOperationService()

    service = AutoSessionService(
        machine_id=1,
        operation_service=operation_service,
        speed_settings_service=FakeSpeedSettingsService(),
        calibration_repository=FakeCalibrationRepository(),
        winding_parameters_repository=FakeWindingParametersRepository(),
        machine_repository=FakeMachineRepository(),
    )

    prepared = await service.prepare(object())
    service.start()

    def failing_update(
        belt_frequency_hz,
        speed_percent,
        elapsed_seconds,
    ):
        raise RuntimeError("Position calculation failed")

    prepared.controller.update = failing_update

    with pytest.raises(RuntimeError, match="Position calculation failed"):
        service.tick(elapsed_seconds=0.1)

    assert service._faulted is True

    service.stop()

    assert service._faulted is True
    assert operation_service.state.running is False
    assert operation_service.state.paused is False

    with pytest.raises(RuntimeError, match="fault"):
        service.start()


@pytest.mark.anyio
async def test_stop_failure_enters_fault_state():
    operation_service = FakeOperationService()

    service = AutoSessionService(
        machine_id=1,
        operation_service=operation_service,
        speed_settings_service=FakeSpeedSettingsService(),
        calibration_repository=FakeCalibrationRepository(),
        winding_parameters_repository=FakeWindingParametersRepository(),
        machine_repository=FakeMachineRepository(),
    )

    await service.prepare(object())
    service.start()

    def failing_stop_roller():
        raise OSError("RS-485 stop failed")

    operation_service.machine.stop_roller = failing_stop_roller

    with pytest.raises(
        OSError,
        match="RS-485 stop failed",
    ):
        service.stop()

    assert service._faulted is True
    assert operation_service.state.running is False
    assert operation_service.state.paused is False

    with pytest.raises(RuntimeError, match="fault"):
        service.start()


@pytest.mark.anyio
async def test_pause_failure_enters_fault_state():
    operation_service = FakeOperationService()

    service = AutoSessionService(
        machine_id=1,
        operation_service=operation_service,
        speed_settings_service=FakeSpeedSettingsService(),
        calibration_repository=FakeCalibrationRepository(),
        winding_parameters_repository=FakeWindingParametersRepository(),
        machine_repository=FakeMachineRepository(),
    )

    await service.prepare(object())
    service.start()

    def failing_stop_roller():
        raise OSError("RS-485 pause failed")

    operation_service.machine.stop_roller = failing_stop_roller

    with pytest.raises(
        OSError,
        match="RS-485 pause failed",
    ):
        service.pause()

    assert service._faulted is True
    assert operation_service.state.running is False
    assert operation_service.state.paused is False

    with pytest.raises(RuntimeError, match="fault"):
        service.resume()

    with pytest.raises(RuntimeError, match="fault"):
        service.start()
