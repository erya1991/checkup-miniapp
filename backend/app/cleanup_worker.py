"""Independent durable file cleanup consumer: python -m app.cleanup_worker."""
import logging
import re
import time

from sqlalchemy import select

from app.core import cos
from app.db.session import create_db_engine, create_session_factory
from app.models import FileCleanup

logger = logging.getLogger(__name__)


def process_cleanup(db, cleanup):
    if cleanup.status == "DONE":
        return True
    try:
        if cleanup.target_type == "OBJECT":
            cos.delete_object(cleanup.cos_object_key)
        elif cleanup.target_type == "PREFIX":
            if not re.fullmatch(r"users/[^/]+/ingestions/[^/]+/", cleanup.cos_object_key):
                raise ValueError("INVALID_CLEANUP_PREFIX")
            cos.delete_prefix(cleanup.cos_object_key)
        else:
            raise ValueError("INVALID_CLEANUP_TARGET")
    except Exception:  # noqa: BLE001 - durable retry must not expose medical exception data
        logger.warning("cleanup_id=%s target_type=%s error_code=COS_CLEANUP_FAILED",
                       cleanup.id, cleanup.target_type)
        return False
    cleanup.status = "DONE"
    db.flush()
    return True


def attempt_cleanup(factory, cleanup_id):
    # Post-delete best effort must never change the outcome of the committed DELETE.
    try:
        with factory() as db:
            row = db.scalar(select(FileCleanup).where(FileCleanup.id == cleanup_id)
                            .with_for_update(skip_locked=True))
            if row:
                process_cleanup(db, row)
                db.commit()
    except Exception:  # noqa: BLE001 - durable retry must not expose medical exception data
        logger.warning("cleanup_id=%s error_code=CLEANUP_RETRY_PENDING", cleanup_id)


def run_once(factory):
    with factory() as db:
        ids = list(db.scalars(select(FileCleanup.id).where(FileCleanup.status == "PENDING")
                              .order_by(FileCleanup.created_at, FileCleanup.id)))
    for cleanup_id in ids:
        attempt_cleanup(factory, cleanup_id)
    return len(ids)


def main():
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("qcloud_cos").setLevel(logging.WARNING)
    engine = create_db_engine()
    factory = create_session_factory(engine)
    try:
        while True:
            try:
                run_once(factory)
            except Exception:  # noqa: BLE001 - retry transient database failure without sensitive logs
                logger.warning("error_code=CLEANUP_PROCESSOR_RETRY")
            time.sleep(10)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
