from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.machine import Machine


class MachineRepository:
    async def load(
        self,
        session: AsyncSession,
        machine_id: int,
    ) -> Machine:
        result = await session.execute(select(Machine).where(Machine.id == machine_id))

        machine = result.scalar_one_or_none()

        if machine is None:
            raise RuntimeError("Machine not found")

        return machine
