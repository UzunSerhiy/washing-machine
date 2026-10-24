from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.drive import Drive
from app.services.drives.service import DriveService


async def configure_drives(
    session: AsyncSession,
    drive_service: DriveService,
) -> None:
    result = await session.execute(
        select(Drive).where(Drive.is_enabled.is_(True)).order_by(Drive.id)
    )

    drives = result.scalars().all()

    for db_drive in drives:
        drive_service.add_drive(
            drive_id=db_drive.id,
            address=db_drive.address,
            name=db_drive.name,
            drive_type=db_drive.type,
            position=db_drive.position,
            enabled=db_drive.is_enabled,
        )
