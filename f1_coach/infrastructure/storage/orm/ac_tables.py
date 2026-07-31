"""SQLAlchemy ORM table definitions for the Assetto Corsa (AC) module.

F125/FSAE ile aynı Base'i paylaşır (bkz. base.py) — tek bir koach.db
dosyasında üç modülün de tabloları bir arada yaşar.

Schema overview:
    ac_sessions  — bir UDP bağlantı oturumu (handshake anında oluşur)
    ac_laps      — RTLap olayıyla tamamlanmış her tur
"""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from f1_coach.infrastructure.storage.orm.base import Base


class AcSessionORM(Base):
    __tablename__ = "ac_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_uid: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    car_name: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    driver_name: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    track_name: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    track_config: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    laps: Mapped[list["AcLapORM"]] = relationship(
        "AcLapORM",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="AcLapORM.lap_number",
    )


class AcLapORM(Base):
    __tablename__ = "ac_laps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ac_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    lap_number: Mapped[int] = mapped_column(Integer, nullable=False)
    lap_time_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    telemetry_file: Mapped[str] = mapped_column(String(512), nullable=False, default="")

    session: Mapped["AcSessionORM"] = relationship("AcSessionORM", back_populates="laps")