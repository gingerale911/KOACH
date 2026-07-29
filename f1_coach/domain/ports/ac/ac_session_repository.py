"""AcSessionRepository port.

F125'in SessionRepository'sine paralel — laps eager-loaded olarak gelir,
tek tek AcLapRepository çağrısına gerek kalmadan.
"""

from typing import Protocol

from f1_coach.domain.models.ac.ac_session import AcSession


class AcSessionRepository(Protocol):
    """Persistence contract for AcSession aggregates."""

    def save(self, session: AcSession) -> None:
        """Insert or update a session.

        After a successful call, ``session.id`` must reflect the persisted value.
        """
        ...

    def get_by_id(self, session_id: int) -> AcSession | None:
        ...

    def get_by_uid(self, session_uid: str) -> AcSession | None:
        ...

    def get_all(self) -> list[AcSession]:
        """Return all sessions ordered by created_at descending."""
        ...

    def delete(self, session_id: int) -> None:
        """Delete a session and cascade to its laps.

        Parquet dosyalarının silinmesi çağıranın (application/presentation)
        sorumluluğunda — F125/FSAE ile aynı sorumluluk ayrımı.
        """
        ...