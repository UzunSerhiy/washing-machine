from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.machine import Machine


class MachineCalibrationSettings(Base):
    __tablename__ = "machine_calibrations"

    id: Mapped[int] = mapped_column(primary_key=True)

    machine_id: Mapped[int] = mapped_column(
        ForeignKey("machines.id"),
        nullable=False,
        unique=True,
    )

    material_start_turns: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    washing_stop_turns: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    machine: Mapped["Machine"] = relationship(back_populates="calibration")
