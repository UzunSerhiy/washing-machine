import asyncio

from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.models.drive import Drive


async def update_drive_config():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Drive).order_by(Drive.id))

        drives = result.scalars().all()

        if len(drives) != 3:
            raise RuntimeError(f"Expected 3 drives, found {len(drives)}")

        # Temporarily move addresses to avoid UNIQUE conflicts.
        for drive in drives:
            drive.address += 100

        await session.flush()

        # Drive ID 1 → Roller → Modbus 1
        drive = await session.get(Drive, 1)

        if drive is None:
            raise RuntimeError("Drive 1 not found")

        drive.name = "Roller"
        drive.address = 1
        drive.type = "ROLLER"
        drive.position = None
        drive.is_enabled = True

        # Drive ID 2 → Brush Right → Modbus 2
        drive = await session.get(Drive, 2)

        if drive is None:
            raise RuntimeError("Drive 2 not found")

        drive.name = "Brush Right"
        drive.address = 2
        drive.type = "BRUSH"
        drive.position = "RIGHT"
        drive.is_enabled = True

        # Drive ID 3 → Brush Left → Modbus 3
        drive = await session.get(Drive, 3)

        if drive is None:
            raise RuntimeError("Drive 3 not found")

        drive.name = "Brush Left"
        drive.address = 3
        drive.type = "BRUSH"
        drive.position = "LEFT"
        drive.is_enabled = True

        await session.commit()

        print("Drive configuration updated successfully")

        for drive in sorted(drives, key=lambda item: item.id):
            print(
                f"id={drive.id} | "
                f"name={drive.name} | "
                f"address={drive.address} | "
                f"type={drive.type} | "
                f"position={drive.position}"
            )


if __name__ == "__main__":
    asyncio.run(update_drive_config())
