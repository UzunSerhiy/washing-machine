from fastapi import APIRouter, HTTPException

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.database import AsyncSessionLocal
from app.models.machine import Machine
from app.schemas.machine import MachineDriveResponse, MachineResponse
from app.services.drives.service import DriveService
from app.services.machine.service import MachineService

router = APIRouter(
    prefix="/api/machine",
    tags=["machine"],
)


def get_drive_service() -> DriveService:
    from app.main import drive_service

    return drive_service


def get_machine_service() -> MachineService:
    from app.main import machine_service

    return machine_service


@router.get("", response_model=MachineResponse)
async def get_machine():
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Machine).options(selectinload(Machine.drives)).where(Machine.id == 1)
        )

        machine = result.scalar_one_or_none()

    if machine is None:
        raise HTTPException(
            status_code=404,
            detail="Machine not found",
        )

    drive_service = get_drive_service()

    drives = []

    for db_drive in machine.drives:
        if not db_drive.is_enabled:
            continue

        drive = drive_service.get_drive(db_drive.id)

        drives.append(
            MachineDriveResponse(
                id=db_drive.id,
                name=db_drive.name,
                address=db_drive.address,
                type=db_drive.type,
                position=db_drive.position,
                enabled=db_drive.is_enabled,
                status=drive.get_status(),
                frequency_hz=drive.get_frequency(),
                fault=drive.get_fault(),
            )
        )
    return MachineResponse(
        id=machine.id,
        name=machine.name,
        description=machine.description,
        is_active=machine.is_active,
        drives=drives,
    )


@router.post("/start")
def start_machine():
    machine_service = get_machine_service()
    machine_service.start()

    return {
        "status": "started",
    }


@router.post("/stop")
def stop_machine():
    machine_service = get_machine_service()
    machine_service.stop()

    return {
        "status": "stoped",
    }
