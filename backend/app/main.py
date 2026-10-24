import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.drives import router as drives_router
from app.api.machine import router as machine_router
from app.api.material_profiles import router as material_profiles_router
from app.db.database import AsyncSessionLocal

from app.services.drives.configurator import configure_drives
from app.services.drives.service import DriveService
from app.services.machine.factory import MachineFactory
from app.services.machine.machine import Machine
from app.services.machine.service import MachineService
from app.services.machine.operation_service import MachineOperationService
from app.services.machine.calibration.session_service import CalibrationSessionService
from app.services.machine.calibration.runtime import CalibrationRuntime
from app.services.winding.rotation import RollerRotationCalculator
from app.services.machine.auto.session_service import AutoSessionService
from app.services.machine.auto.runtime import AutoRuntime
from app.services.speed.auto_settings import AutoSpeedSettingsService
from app.services.machine.sensors.fake_reference import FakeRollerReferenceSensor
from app.services.machine.sensors.service import RollerSensorService

from app.services.machine.sensors.roller_reference import RollerReferenceSensor
from app.services.machine.sensors.serial_reference import SerialRollerReferenceSensor
from app.services.machine.io_controller import MachineIOController
from app.services.machine.roller_homing_service import RollerHomingService
from app.services.machine.roller_homing_runtime import RollerHomingRuntime

from app.core.config import settings


drive_service = DriveService()

machine: Machine | None = None
machine_service: MachineService | None = None
machine_operation_service: MachineOperationService | None = None
calibration_session_service: CalibrationSessionService | None = None
calibration_runtime: CalibrationRuntime | None = None
auto_session_service: AutoSessionService | None = None
auto_runtime: AutoRuntime | None = None
roller_reference_sensor: RollerReferenceSensor | None = None
machine_io_controller: MachineIOController | None = None
roller_homing_service: RollerHomingService | None = None
roller_homing_runtime: RollerHomingRuntime | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global machine
    global machine_service
    global machine_operation_service
    global calibration_session_service
    global calibration_runtime
    global auto_session_service
    global auto_runtime
    global roller_reference_sensor
    global machine_io_controller
    global roller_homing_service, roller_homing_runtime

    if settings.DRIVE_MODE == "real":
        drive_service.connect()

    async with AsyncSessionLocal() as session:
        await configure_drives(
            session=session,
            drive_service=drive_service,
        )

    created_machine = MachineFactory.create(drive_service)

    machine = created_machine

    machine_service = MachineService(
        machine=created_machine,
    )

    machine_operation_service = MachineOperationService(
        machine=created_machine,
    )

    auto_session_service = AutoSessionService(
        machine_id=1,
        operation_service=machine_operation_service,
        speed_settings_service=AutoSpeedSettingsService(),
    )

    auto_runtime = AutoRuntime(
        auto_service=auto_session_service,
        interval_seconds=0.1,
    )

    await auto_runtime.start()

    rotation_calculator = RollerRotationCalculator(
        motor_rpm_at_50hz=settings.ROLLER_MOTOR_RPM_AT_50HZ,
        gear_ratio=settings.ROLLER_GEAR_RATIO,
    )

    sensor_mode = os.getenv("ROLLER_SENSOR_MODE", "fake").lower()

    if sensor_mode == "serial":
        roller_reference_sensor = SerialRollerReferenceSensor(
            port=os.getenv("ESP32_SERIAL_PORT", "/dev/ttyACM0"),
            baudrate=int(os.getenv("ESP32_SERIAL_BAUDRATE", "115200")),
        )
        roller_reference_sensor.start()
        print("ESP32 roller reference sensor started")

        machine_io_controller = MachineIOController(
            sensor=roller_reference_sensor,
        )

        machine_io_controller.start()

    elif sensor_mode == "fake":
        roller_reference_sensor = FakeRollerReferenceSensor()
        print("Fake roller reference sensor initialized")

    else:
        raise RuntimeError(f"Unsupported ROLLER_SENSOR_MODE: {sensor_mode}")

    roller_sensor_service = RollerSensorService(roller_reference_sensor)

    roller_homing_service = RollerHomingService(
        machine=created_machine,
        sensor_service=roller_sensor_service,
        rotation_calculator=rotation_calculator,
    )

    calibration_session_service.set_roller_homing_service(roller_homing_service)

    auto_session_service.set_roller_homing_service(roller_homing_service)

    machine_operation_service.set_roller_homing_service(roller_homing_service)

    created_machine.set_roller_external_stop_callback(
        roller_homing_service.external_stop
    )

    roller_homing_runtime = RollerHomingRuntime(
        homing_service=roller_homing_service,
        interval_seconds=0.1,
    )

    await roller_homing_runtime.start()

    calibration_session_service = CalibrationSessionService(
        machine=created_machine,
        rotation_calculator=rotation_calculator,
        sensor_service=roller_sensor_service,
    )

    calibration_runtime = CalibrationRuntime(
        calibration_service=calibration_session_service, interval_seconds=0.1
    )

    await calibration_runtime.start()

    if settings.DRIVE_MODE == "fake":
        print("Fake drives initialized")
    else:
        print("RS485 connected")

    yield

    if roller_homing_runtime is not None:
        await roller_homing_runtime.stop()

    drive_service.close()

    if settings.DRIVE_MODE == "fake":
        print("Fake drives stopped")
    else:
        print("RS485 disconnected")

    if calibration_runtime is not None:
        await calibration_runtime.stop()

    if auto_runtime is not None:
        await auto_runtime.stop()

    if isinstance(roller_reference_sensor, SerialRollerReferenceSensor):
        roller_reference_sensor.stop()
        print("ESP32 roller reference sensor stopped")
        if machine_io_controller is not None:
            machine_io_controller.stop()


app = FastAPI(
    title="Washing Machine",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(drives_router)
app.include_router(machine_router)
app.include_router(material_profiles_router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/health/db")
async def health_db():
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("SELECT 1"))

    return {
        "status": "ok",
        "database": result.scalar(),
    }
