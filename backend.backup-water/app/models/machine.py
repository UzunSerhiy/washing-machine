from typing import TYPE_CHECKING
from sqlalchemy import String, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.drive import Drive
    from app.models.machine_mode import MachineMode
    from app.models.material_profile import MaterialProfile
    from app.models.machine_calibration import MachineCalibrationSettings


class Machine(Base):
    __tablename__ = "machines"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    roller_core_diameter_mm: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=200.0,
    )
    drives: Mapped[list["Drive"]] = relationship(
        back_populates="machine",
        cascade="all, delete-orphan",
    )
    modes: Mapped[list["MachineMode"]] = relationship(
        back_populates="machine", cascade="all, delete-orphan"
    )
    material_profiles: Mapped[list["MaterialProfile"]] = relationship(
        back_populates="machine", cascade="all, delete-orphan"
    )

    calibration: Mapped["MachineCalibrationSettings | None"] = relationship(
        back_populates="machine", cascade="all, delete-orphan", uselist=False
    )
