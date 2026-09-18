from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.api.drives import router as drives_router
from app.db.database import AsyncSessionLocal

# from app.services.drive_service import DriveService
from app.services.drives.service import DriveService


drive_service = DriveService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    drive_service.add_fake_drive(1)
    drive_service.add_fake_drive(2)
    drive_service.add_fake_drive(3)

    print("Fake drives initialized")

    yield

    print("fake drives stopped")
    # drive_service.connect()
    #
    # drive_service.add_drive(1)
    #
    # print("RS485 connected")
    #
    # yield
    #
    # drive_service.close()
    #
    # print("RS485 disconnected")


app = FastAPI(title="Washing Machine", version="0.1.0", lifespan=lifespan)

app.include_router(drives_router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/health/db")
async def health_db():
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("SELECT 1"))
    return {"status": "ok", "database": result.scalar()}
