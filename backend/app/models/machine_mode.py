from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.mode_speed_settings import ModeSpeedSettings


class MachineMode(Base):
    __tablename__ = "machine_modes"

    id: Mapped[int] = mapped_column(primary_key=True)

    machine_id: Mapped[int] = mapped_column(ForeignKey("machines.id"), nullable=False)

    name: Mapped[str] = mapped_column(String(50), nullable=False)

    code: Mapped[str] = mapped_column(String(30), nullable=False)

    description: Mapped[str | None] = mapped_column(String(500), nullable=True)

    is_enabled: Mapped[bool] = mapped_column(default=True, nullable=False)

    machine: Mapped["Machine"] = relationship(back_populates="modes")

    speed_settings: Mapped["ModeSpeedSettings | None"] = relationship(
        back_populates="machine_mode",
        cascade="all, delete-orphan",
        uselist=False,
    )
