from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.api.drives import router as drives_router
from app.api.machine import router as machine_router
from app.db.database import AsyncSessionLocal

from app.services.drives.configurator import configure_drives
from app.services.drives.service import DriveService
from app.services.machine.factory import MachineFactory
from app.services.machine.machine import Machine
from app.services.machine.service import MachineService
from app.services.machine.operation_service import MachineOperationService

from app.core.config import settings


drive_service = DriveService()

machine: Machine | None = None
machine_service: MachineService | None = None
machine_operation_service: MachineOperationService | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global machine
    global machine_service
    global machine_operation_service

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


app = FastAPI(
    title="Washing Machine",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(drives_router)
app.include_router(machine_router)


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
