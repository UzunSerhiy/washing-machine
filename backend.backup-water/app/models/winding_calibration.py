from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.material_profile import MaterialProfile


class WindingCalibration(Base):
    __tablename__ = "winding_calibrations"

    id: Mapped[int] = mapped_column(primary_key=True)

    material_profile_id: Mapped[int] = mapped_column(
        ForeignKey("material_profiles.id"),
        nullable=False,
        unique=True,
    )

    material_end_turns: Mapped[float | None] = mapped_column(Float, nullable=True)

    material_profile: Mapped["MaterialProfile"] = relationship(
        back_populates="winding_calibrations"
    )
