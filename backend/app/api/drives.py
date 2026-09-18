from fastapi import APIRouter, HTTPException

from app.services.drive_service import DriveService

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
