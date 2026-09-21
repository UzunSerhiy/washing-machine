from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class MaterialProfile(Base):
    __tablename__ = "material_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)

    machine_id: Mapped[int] = mapped_column(ForeignKey("machines.id"), nullable=False)

    name: Mapped[str] = mapped_column(String(100), nullable=False)

    code: Mapped[str] = mapped_column(String(50), nullable=False)

    description: Mapped[str | None] = mapped_column(String(500), nullable=True)

    is_enabled: Mapped[bool] = mapped_column(default=True, nullable=False)

    machine: Mapped["Machine"] = relationship(back_populates="material_profiles")
