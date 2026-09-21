from typing import TYPE_CHECKING
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.drive import Drive
    from app.models.machine_mode import MachineMode
    from app.models.material_profile import MaterialProfile


class Machine(Base):
    __tablename__ = "machines"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
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
