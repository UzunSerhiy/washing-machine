from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Drive(Base):
    __tablename__ = "drives"

    id: Mapped[int] = mapped_column(primary_key=True)

    machine_id: Mapped[int] = mapped_column(ForeignKey("machines.id"), nullable=False)

    name: Mapped[str] = mapped_column(String(100), nullable=False)

    address: Mapped[int] = mapped_column(nullable=False)

    type: Mapped[str] = mapped_column(String(20), nullable=False)

    position: Mapped[str | None] = mapped_column(String(20), nullable=True)

    is_enabled: Mapped[bool] = mapped_column(default=True, nullable=False)

    machine: Mapped["Machine"] = relationship(
        back_populates="drives",
    )
