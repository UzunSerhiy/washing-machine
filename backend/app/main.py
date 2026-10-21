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

from app.core.config import settings


drive_service = DriveService()

machine: Machine | None = None
machine_service: MachineService | None = None
machine_operation_service: MachineOperationService | None = None
calibration_session_service: CalibrationSessionService | None = None
calibration_runtime: CalibrationRuntime | None = None
auto_session_service: AutoSessionService | None = None
auto_runtime: AutoRuntime | None = None
roller_reference_sensor: FakeRollerReferenceSensor | None = None


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

    roller_reference_sensor = FakeRollerReferenceSensor()
    roller_sensor_service = RollerSensorService(roller_reference_sensor)

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

    drive_service.close()

    if settings.DRIVE_MODE == "fake":
        print("Fake drives stopped")
    else:
        print("RS485 disconnected")

    if calibration_runtime is not None:
        await calibration_runtime.stop()

    if auto_runtime is not None:
        await auto_runtime.stop()


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
