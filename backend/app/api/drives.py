from fastapi import APIRouter, HTTPException

from app.services.drives.service import DriveService
from app.schemas.drive import DriveFrequencyRequest

router = APIRouter(
    prefix="/api/drives",
    tags=["drives"],
)


def get_drive_service() -> DriveService:
    from app.main import drive_service

    return drive_service


@router.get("/{drive_id}/status")
async def get_drive_status(drive_id: int):
    service = get_drive_service()

    try:
        drive = service.get_drive(drive_id)
        status = drive.get_status()

        return {
            "drive_id": drive_id,
            "status": status,
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc


@router.get("/{drive_id}/frequency")
async def get_drive_frequency(drive_id: int):
    service = get_drive_service()

    try:
        drive = service.get_drive(drive_id)
        frequency = drive.get_frequency()

        return {"drive_id": drive_id, "frequency_hz": frequency}

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc


@router.get("/{drive_id}/fault")
async def get_drive_fault(drive_id: int):
    service = get_drive_service()

    try:
        drive = service.get_drive(drive_id)
        fault = drive.get_fault()

        return {
            "drive_id": drive_id,
            "fault": fault,
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc


@router.post("/{drive_id}/frequency")
async def set_drive_frequency(drive_id: int, data: DriveFrequencyRequest):
    service = get_drive_service()

    try:
        drive = service.get_drive(drive_id)
        drive.set_frequency(data.frequency_hz)
        return {
            "drive_id": drive_id,
            "frequency_hz": drive.get_frequency(),
        }
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc


@router.post("/{drive_id}/run/forward")
async def run_drive_forward(drive_id: int):
    service = get_drive_service()

    try:
        drive = service.get_drive(drive_id)
        drive.run_forward()

        return {"drive_id": drive_id, "status": drive.get_status()}

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc


@router.post("{drive_id}/run/reverse")
async def run_drive_reverse(drive_id: int):
    service = get_drive_service()

    try:
        drive = service.get_drive(drive_id)
        drive.run_reverse()

        return {
            "drive_id": drive_id,
            "status": drive.get_status(),
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except RuntimeError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc


@router.post("/{drive_id}/run/stop")
async def stop_drive(drive_id: int):
    service = get_drive_service()

    try:
        drive = service.get_drive(drive_id)
        drive.stop()

        return {"drive_id": drive_id, "status": drive.get_status()}

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except RuntimeError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc
