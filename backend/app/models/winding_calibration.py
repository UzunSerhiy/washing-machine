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
        ForeignKey("material_profiles.id"), nullable=False
    )

    mode_code: Mapped[str] = mapped_column(String(30), nullable=False)

    name: Mapped[str] = mapped_column(String(100), nullable=False)

    belt_end_turns: Mapped[float | None] = mapped_column(Float, nullable=True)

    material_end_turns: Mapped[float | None] = mapped_column(Float, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    material_profile: Mapped["MaterialProfile"] = relationship(
        back_populates="winding_calibrations"
    )
