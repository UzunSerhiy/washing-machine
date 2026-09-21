from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.api.drives import router as drives_router
from app.api.machine import router as machine_router
from app.db.database import AsyncSessionLocal

from app.services.drives.configurator import configure_drives
from app.services.drives.service import DriveService
from app.services.machine.service import MachineService

from app.core.config import settings

drive_service = DriveService()

machine_service = MachineService(
    drive_service=drive_service,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.DRIVE_MODE == "real":
        drive_service.connect()

    async with AsyncSessionLocal() as session:
        await configure_drives(
            session=session,
            drive_service=drive_service,
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


app = FastAPI(title="Washing Machine", version="0.1.0", lifespan=lifespan)

app.include_router(drives_router)
app.include_router(machine_router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/health/db")
async def health_db():
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("SELECT 1"))
    return {"status": "ok", "database": result.scalar()}
