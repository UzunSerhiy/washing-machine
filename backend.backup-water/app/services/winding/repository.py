from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.winding_parameters import WindingParameters


class WindingParametersRepository:
    async def load(
        self,
        session: AsyncSession,
        material_profile_id: int,
    ) -> WindingParameters:
        result = await session.execute(
            select(WindingParameters).where(
                WindingParameters.material_profile_id == material_profile_id
            )
        )

        parameters = result.scalar_one_or_none()

        if parameters is None:
            raise RuntimeError("Winding parameters not found")

        return parameters
