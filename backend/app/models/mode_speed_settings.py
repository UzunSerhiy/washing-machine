from sqlalchemy import ForeignKey, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ModeSpeedSettings(Base):
    __tablename__ = "mode_speed_settings"

    id: Mapped[int] = mapped_column(primary_key=True)

    machine_mode_id: Mapped[int] = mapped_column(
        ForeignKey("machine_modes.id"), nullable=False, unique=True
    )

    belt_speed_percent: Mapped[float] = mapped_column(Float, nullable=False)

    material_speed_percent: Mapped[float] = mapped_column(Float, nullable=False)

    brush_speed_percent: Mapped[float | None] = mapped_column(Float, nullable=True)

    machine_mode: Mapped["MachineMode"] = relationship(back_populates="speed_settings")
