from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.material_profile import MaterialProfile


class WindingParameters(Base):
    __tablename__ = "winding_parameters"

    id: Mapped[int] = mapped_column(primary_key=True)

    material_profile_id: Mapped[int] = mapped_column(
        ForeignKey("material_profiles.id"),
        nullable=False,
        unique=True,
    )

    # Geometry empty roller
    core_diameter_mm: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    # Material thickness
    material_thickness_mm: Mapped[float | None] = mapped_column(Float, nullable=True)

    target_speed_m_min: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    calibration_turns: Mapped[float | None] = mapped_column(Float, nullable=True)

    calibration_final_diameter_mm: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    material_profile: Mapped["MaterialProfile"] = relationship(
        back_populates="winding_parameters"
    )
