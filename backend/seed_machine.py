import asyncio

from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.models.drive import Drive
from app.models.machine import Machine
from app.models.machine_mode import MachineMode
from app.models.material_profile import MaterialProfile


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
                "address": 3,
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
                "address": 1,
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

        # Material profiles
        material_profiles = [
            {
                "name": "Дах 5м",
                "code": "ROOF_5M",
                "description": "Дахове покриття 5 м",
            },
            {
                "name": "Дах 10м",
                "code": "ROOF_10M",
                "description": "Дахове покриття 10 м",
            },
            {
                "name": "Дах 15м",
                "code": "ROOF_15M",
                "description": "Дахoве покриття 15 м",
            },
            {
                "name": "Дах 20м",
                "code": "ROOF_20M",
                "description": "Дахoве покриття 20 м",
            },
            {
                "name": "Дах 30м",
                "code": "ROOF_30M",
                "description": "Дахoве покриття 30 м",
            },
            {
                "name": "Дах 40M",
                "code": "ROOF_40M",
                "description": "Дахoве покриття 40 м",
            },
            {
                "name": "Дах 50м",
                "code": "ROOF_50M",
                "description": "Дахoве покриття 50 м",
            },
            {
                "name": "Стіна 2.3 м",
                "code": "WALL_2_3M",
                "description": "Висота стіни 2.3 м",
            },
            {
                "name": "Стіна 3 м",
                "code": "WALL_3M",
                "description": "Висота стіни 3 м",
            },
            {
                "name": "Стіна 4 м",
                "code": "WALL_4M",
                "description": "Висота стіни 4 м",
            },
            {
                "name": "Трикутник 5 м",
                "code": "TRIANGLE_5M",
                "description": "Трикутник довжиною 5 м (10)",
            },
            {
                "name": "Трикутник 7.5 м",
                "code": "TRIANGLE_7_5M",
                "description": "Трикутник довжиною 7.5 м (15)",
            },
            {
                "name": "Трикутник 10 м",
                "code": "TRIANGLE_10M",
                "description": "Ткрикутник довжиною 10 м (20)",
            },
            {
                "name": "Трикутник 15 м",
                "code": "TRIANGLE_15M",
                "description": "Ткрикутник довжиною 15 м (30)",
            },
            {
                "name": "Трикутник 20 м",
                "code": "TRIANGLE_20M",
                "description": "Ткрикутник довжиною 20 м (40)",
            },
            {
                "name": "Трикутник 25 м",
                "code": "TRIANGLE_25M",
                "description": "Ткрикутник довжиною 25 м (50)",
            },
        ]

        for profile_data in material_profiles:
            result = await session.execute(
                select(MaterialProfile).where(
                    MaterialProfile.machine_id == machine.id,
                    MaterialProfile.code == profile_data["code"],
                )
            )

            profile = result.scalar_one_or_none()

            if profile is None:
                session.add(
                    MaterialProfile(
                        machine_id=machine.id,
                        name=profile_data["name"],
                        code=profile_data["code"],
                        description=profile_data["description"],
                        is_enabled=True,
                    )
                )

        await session.commit()

        print("Machine configurator created")


if __name__ == "__main__":
    asyncio.run(seed())
