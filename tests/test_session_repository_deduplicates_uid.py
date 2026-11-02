from contextlib import contextmanager
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session as SQLASession, sessionmaker

from f1_coach.domain.models.f125.enums import SessionType, TrackName
from f1_coach.domain.models.f125.session import Session
from f1_coach.infrastructure.storage.orm.base import Base
from f1_coach.infrastructure.storage.orm import f125_tables  # noqa: F401
from f1_coach.infrastructure.storage.repositories.f125 import sqlite_session_repository


def test_save_reuses_existing_session_for_same_uid(monkeypatch, tmp_path):
    db_path = tmp_path / "test_koach.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    @contextmanager
    def fake_get_session():
        session: SQLASession = factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    monkeypatch.setattr(sqlite_session_repository, "get_session", fake_get_session)

    repo = sqlite_session_repository.SQLiteSessionRepository()

    first = Session(
        session_uid="abc123",
        track=TrackName.MELBOURNE,
        session_type=SessionType.RACE,
        created_at=datetime.now(),
    )
    repo.save(first)

    duplicate = Session(
        session_uid="abc123",
        track=TrackName.MELBOURNE,
        session_type=SessionType.RACE,
        created_at=datetime.now(),
    )
    repo.save(duplicate)

    rows = repo.get_all()
    assert len(rows) == 1
    assert rows[0].session_uid == "abc123"
    assert rows[0].id == first.id
