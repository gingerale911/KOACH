"""Bidirectional mappers between AC ORM rows and domain models."""

from f1_coach.domain.models.ac.ac_lap import AcLap
from f1_coach.domain.models.ac.ac_session import AcSession
from f1_coach.infrastructure.storage.orm.ac_tables import AcLapORM, AcSessionORM


def ac_session_to_domain(orm: AcSessionORM) -> AcSession:
    return AcSession(
        session_uid=orm.session_uid,
        car_name=orm.car_name,
        driver_name=orm.driver_name,
        track_name=orm.track_name,
        track_config=orm.track_config,
        created_at=orm.created_at,
        laps=[ac_lap_to_domain(lap_orm) for lap_orm in orm.laps],
        id=orm.id,
    )


def ac_session_to_orm(domain: AcSession) -> AcSessionORM:
    kwargs: dict = dict(
        session_uid=domain.session_uid,
        car_name=domain.car_name,
        driver_name=domain.driver_name,
        track_name=domain.track_name,
        track_config=domain.track_config,
        created_at=domain.created_at,
    )
    if domain.is_persisted:
        kwargs["id"] = domain.id
    return AcSessionORM(**kwargs)


def ac_lap_to_domain(orm: AcLapORM) -> AcLap:
    return AcLap(
        lap_number=orm.lap_number,
        lap_time_ms=orm.lap_time_ms,
        telemetry_file=orm.telemetry_file,
        id=orm.id,
        session_id=orm.session_id,
    )


def ac_lap_to_orm(domain: AcLap) -> AcLapORM:
    kwargs: dict = dict(
        session_id=domain.session_id,
        lap_number=domain.lap_number,
        lap_time_ms=domain.lap_time_ms,
        telemetry_file=domain.telemetry_file,
    )
    if domain.is_persisted:
        kwargs["id"] = domain.id
    return AcLapORM(**kwargs)