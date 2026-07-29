"""AcLapRepository port."""

from typing import Protocol

from f1_coach.domain.models.ac.ac_lap import AcLap


class AcLapRepository(Protocol):
    """Persistence contract for AcLap rows."""

    def save(self, lap: AcLap) -> None:
        """Insert or update a lap.

        After a successful call, ``lap.id`` must reflect the persisted value.
        """
        ...

    def get_by_session(self, session_id: int) -> list[AcLap]:
        """Return all laps for a session, ordered by lap_number ascending."""
        ...