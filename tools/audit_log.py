"""
PostgreSQL audit logger for triage decisions.

Records every triage outcome for compliance, analytics, and
model improvement. HIPAA-ready: no raw clinical notes stored,
only structured decision metadata.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped

from models.fhir_types import ESILevel

# ---------------------------------------------------------------------------
# SQLAlchemy setup
# ---------------------------------------------------------------------------

DSN = os.getenv("POSTGRES_DSN", "postgresql+asyncpg://alignwell:alignwell@localhost:5432/alignwell")
engine = create_async_engine(DSN, echo=False)


class Base(DeclarativeBase):
    pass


class TriageAuditRecord(Base):
    """One row per completed triage workflow run."""

    __tablename__ = "triage_audit"

    id: Mapped[str] = mapped_column(sa.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=datetime.utcnow)

    patient_id: Mapped[str] = mapped_column(sa.String, nullable=False)
    condition_id: Mapped[str] = mapped_column(sa.String, nullable=False)
    chief_complaint: Mapped[str] = mapped_column(sa.Text, nullable=False)

    esi_level: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    triage_reasoning: Mapped[str] = mapped_column(sa.Text, nullable=True)

    scheduler_action: Mapped[str] = mapped_column(sa.String, nullable=True)  # booked | waitlisted | escalated
    slot_id: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    appointment_id: Mapped[str | None] = mapped_column(sa.String, nullable=True)

    requires_escalation: Mapped[bool] = mapped_column(sa.Boolean, default=False)
    error: Mapped[str | None] = mapped_column(sa.Text, nullable=True)


async def init_db() -> None:
    """Create tables if they don't exist. Called on app startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def log_triage_outcome(
    patient_id: str,
    condition_id: str,
    chief_complaint: str,
    esi_level: ESILevel | None,
    triage_reasoning: str,
    scheduler_action: str,
    slot_id: str | None,
    appointment_id: str | None,
    requires_escalation: bool,
    error: str | None,
) -> str:
    """
    Persist a triage audit record and return its ID.

    Called by the NotificationAgent as the final step of every run.
    """
    record = TriageAuditRecord(
        patient_id=patient_id,
        condition_id=condition_id,
        chief_complaint=chief_complaint,
        esi_level=esi_level.value if esi_level else None,
        triage_reasoning=triage_reasoning,
        scheduler_action=scheduler_action,
        slot_id=slot_id,
        appointment_id=appointment_id,
        requires_escalation=requires_escalation,
        error=error,
    )
    record_id = record.id  # capture before commit expires the instance
    async with AsyncSession(engine) as session:
        session.add(record)
        await session.commit()
        return record_id
