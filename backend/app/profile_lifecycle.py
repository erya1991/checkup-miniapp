"""Serialize one owner's lifecycle writes before taking any business row locks.

The transaction-scoped PostgreSQL lock covers moves between the owner's profiles,
default selection and ingestion creation too. It never blocks other owners or
changes the OCR worker protocol. SQLite is only used for sequential unit tests.
"""
import hashlib

from sqlalchemy import select, text

from app.models import User


def lock_lifecycle(db, user_id):
    if db.get_bind().dialect.name == "postgresql":
        key = int.from_bytes(hashlib.sha256(f"profile-lifecycle:{user_id}".encode()).digest()[:8],
                             "big", signed=True)
        db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": key})
    # Authentication can have loaded a stale default before waiting for the lock.
    return db.scalar(select(User).where(User.id == user_id)
                     .execution_options(populate_existing=True))
