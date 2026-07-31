"""SQLite implementation of AcLapRepository."""

from f1_coach.domain.models.ac.ac_lap import AcLap
from f1_coach.infrastructure.logging.logger import get_logger
from f1_coach.infrastructure.storage.mappers.ac_domain_mapper import ac_lap_to_domain, ac_lap_to_orm
from f1_coach.infrastructure.storage.orm.database import get_session
from f1_coach.infrastructure.storage.orm.ac_tables import AcLapORM

logger = get_logger(__name__)


class SQLiteAcLapRepository:
    def save(self, lap: AcLap) -> None:
        with get_session() as db:
            if lap.is_persisted:
                orm = db.get(AcLapORM, lap.id)
                if orm is None:
                    raise ValueError(f"AcLap id={lap.id} not found.")
                orm.lap_time_ms = lap.lap_time_ms
                orm.telemetry_file = lap.telemetry_file
            else:
                orm = ac_lap_to_orm(lap)
                db.add(orm)
                db.flush()
                lap.id = orm.id

        logger.debug("AcLap saved: session_id=%d lap_number=%d id=%d", lap.session_id, lap.lap_number, lap.id)

    def get_by_session(self, session_id: int) -> list[AcLap]:
        with get_session() as db:
            rows = (
                db.query(AcLapORM)
                .filter(AcLapORM.session_id == session_id)
                .order_by(AcLapORM.lap_number.asc())
                .all()
            )
            return [ac_lap_to_domain(row) for row in rows]