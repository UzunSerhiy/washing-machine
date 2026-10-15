from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.material_profile import MaterialProfile


router = APIRouter(
    prefix="/api/material-profiles",
    tags=["Material Profiles"],
)


class MaterialProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    machine_id: int
    name: str
    code: str
    description: str | None
    is_enabled: bool


@router.get("", response_model=list[MaterialProfileResponse])
async def get_material_profiles(
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MaterialProfile)
        .where(
            MaterialProfile.machine_id == 1,
            MaterialProfile.is_enabled.is_(True),
        )
        .order_by(MaterialProfile.id)
    )

    return result.scalars().all()
