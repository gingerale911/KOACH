"""SQLite implementation of AcSessionRepository."""

from sqlalchemy.orm import joinedload

from f1_coach.domain.models.ac.ac_session import AcSession
from f1_coach.infrastructure.logging.logger import get_logger
from f1_coach.infrastructure.storage.mappers.ac_domain_mapper import ac_session_to_domain, ac_session_to_orm
from f1_coach.infrastructure.storage.orm.database import get_session
from f1_coach.infrastructure.storage.orm.ac_tables import AcSessionORM

logger = get_logger(__name__)


class SQLiteAcSessionRepository:
    def save(self, session: AcSession) -> None:
        with get_session() as db:
            if session.is_persisted:
                orm = db.get(AcSessionORM, session.id)
                if orm is None:
                    raise ValueError(f"AcSession id={session.id} not found.")
                orm.car_name = session.car_name
                orm.driver_name = session.driver_name
                orm.track_name = session.track_name
                orm.track_config = session.track_config
            else:
                orm = ac_session_to_orm(session)
                db.add(orm)
                db.flush()
                session.id = orm.id

        logger.debug("AcSession saved: uid=%s id=%d", session.session_uid, session.id)

    def get_by_id(self, session_id: int) -> AcSession | None:
        with get_session() as db:
            orm = (
                db.query(AcSessionORM)
                .options(joinedload(AcSessionORM.laps))
                .filter(AcSessionORM.id == session_id)
                .first()
            )
            return ac_session_to_domain(orm) if orm else None

    def get_by_uid(self, session_uid: str) -> AcSession | None:
        with get_session() as db:
            orm = (
                db.query(AcSessionORM)
                .options(joinedload(AcSessionORM.laps))
                .filter(AcSessionORM.session_uid == session_uid)
                .first()
            )
            return ac_session_to_domain(orm) if orm else None

    def get_all(self) -> list[AcSession]:
        with get_session() as db:
            rows = (
                db.query(AcSessionORM)
                .options(joinedload(AcSessionORM.laps))
                .order_by(AcSessionORM.created_at.desc())
                .all()
            )
            return [ac_session_to_domain(row) for row in rows]

    def delete(self, session_id: int) -> None:
        with get_session() as db:
            orm = db.get(AcSessionORM, session_id)
            if orm is None:
                raise ValueError(f"AcSession id={session_id} not found.")
            db.delete(orm)
        logger.info("AcSession deleted: id=%d", session_id)