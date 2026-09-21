import asyncio

from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.models.drive import Drive
from app.models.machine import Machine
from app.models.machine_mode import MachineMode


async def seed():
    async with AsyncSessionLocal() as session:
        # Machine
        result = await session.execute(
            select(Machine).where(Machine.name == "Washing Machine")
        )

        machine = result.scalar_one_or_none()

        if machine is None:
            machine = Machine(
                name="Washing Machine",
                description="Industrial washing machine",
            )

            session.add(machine)
            await session.flush()

        # Drives
        drives = [
            {
                "name": "Brush Left",
                "address": 1,
                "type": "BRUSH",
                "position": "LEFT",
            },
            {
                "name": "Brush Right",
                "address": 2,
                "type": "BRUSH",
                "position": "RIGHT",
            },
            {
                "name": "Roller",
                "address": 3,
                "type": "ROLLER",
                "position": None,
            },
        ]

        for drive_data in drives:
            result = await session.execute(
                select(Drive).where(
                    Drive.machine_id == machine.id,
                    Drive.address == drive_data["address"],
                )
            )

            drive = result.scalar_one_or_none()

            if drive is None:
                session.add(
                    Drive(
                        machine_id=machine.id,
                        name=drive_data["name"],
                        address=drive_data["address"],
                        type=drive_data["type"],
                        position=drive_data["position"],
                        is_enabled=True,
                    )
                )

        # Machine modes
        modes = [
            {
                "name": "Намотка",
                "code": "WINDING",
                "description": "Наматывание материала",
            },
            {
                "name": "Мойка",
                "code": "WASHING",
                "description": "Основной режим мойки",
            },
            {
                "name": "Сушка",
                "code": "DRYING",
                "description": "Режим сушки материала",
            },
            {
                "name": "Размотка",
                "code": "UNWINDING",
                "description": "Разматывание материала",
            },
        ]

        for mode_data in modes:
            result = await session.execute(
                select(MachineMode).where(
                    MachineMode.machine_id == machine.id,
                    MachineMode.code == mode_data["code"],
                )
            )

            mode = result.scalar_one_or_none()

            if mode is None:
                session.add(
                    MachineMode(
                        machine_id=machine.id,
                        name=mode_data["name"],
                        code=mode_data["code"],
                        description=mode_data["description"],
                        is_enabled=True,
                    )
                )

        await session.commit()

        print("Machine configurator created")


if __name__ == "__main__":
    asyncio.run(seed())
