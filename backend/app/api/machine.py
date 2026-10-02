from fastapi import APIRouter, HTTPException

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.database import AsyncSessionLocal
from app.models.machine import Machine
from app.schemas.machine import (
    MachineDriveResponse,
    MachineResponse,
    MachineOperationResponse,
    ManualSpeedRequest,
)
from app.services.drives.service import DriveService
from app.services.machine.service import MachineService
from app.services.machine.operation_service import MachineOperationService

router = APIRouter(
    prefix="/api/machine",
    tags=["machine"],
)


def get_drive_service() -> DriveService:
    from app.main import drive_service

    return drive_service


def get_machine_service() -> MachineService:
    from app.main import machine_service

    if machine_service is None:
        raise RuntimeError("Machine service is not initialized")

    return machine_service


def get_machine_operation_service() -> MachineOperationService:
    from app.main import machine_operation_service

    if machine_operation_service is None:
        raise RuntimeError("Machine operation service is not initialized")

    return machine_operation_service


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


@router.get("/operation", response_model=MachineOperationResponse)
def get_machine_operation():
    service = get_machine_operation_service()
    state = service.state

    return MachineOperationResponse(
        mode=state.mode,
        auto_stage=state.auto_stage,
        material_profile_id=state.material_profile_id,
        roller_speed_percent=state.roller_speed_percent,
        brush_speed_percent=state.brush_speed_percent,
        roller_running=state.roller_running,
        brush_running=state.brush_running,
        running=state.running,
        paused=state.paused,
    )


@router.put(
    "/manual/roller/speed",
    response_model=MachineOperationResponse,
)
def set_manual_roller_speed(request: ManualSpeedRequest):
    service = get_machine_operation_service()

    try:
        service.set_manual_roller_speed(request.speed_percent)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return service.state


@router.put("/manual/brush/speed", response_model=MachineOperationResponse)
def set_manual_brush_speed(request: ManualSpeedRequest):
    service = get_machine_operation_service()

    try:
        service.set_manual_brush_speed(request.speed_percent)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return service.state


@router.post("/start")
def start_machine():
    service = get_machine_service()

    service.start()

    return {
        "status": "started",
    }


@router.post("/stop")
def stop_machine():
    service = get_machine_service()

    service.stop()

    return {
        "status": "stopped",
    }


@router.post(
    "/manual/roller/forward",
    response_model=MachineOperationResponse,
)
def start_manual_roller_forward():
    service = get_machine_operation_service()

    try:
        service.start_manual_roller_forward()
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return service.state


@router.post("/manual/roller/reverse", response_model=MachineOperationResponse)
def start_manual_roller_reverse():
    service = get_machine_operation_service()

    try:
        service.start_manual_roller_reverse()
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return service.state


@router.post("/manual/roller/stop", response_model=MachineOperationResponse)
def stop_manula_roller():
    service = get_machine_operation_service()

    try:
        service.stop_manual_roller()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return service.state


@router.post("/manual/brush/start", response_model=MachineOperationResponse)
def start_manual_brush():
    service = get_machine_operation_service()

    try:
        service.start_manual_brush()
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return service.state


@router.post("/manual/brush/stop", response_model=MachineOperationResponse)
def stop_manual_brush():
    service = get_machine_operation_service()

    try:
        service.stop_manual_brush()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return service.state
