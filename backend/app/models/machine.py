from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


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
