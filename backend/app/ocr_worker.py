"""Run with `python -m app.ocr_worker`; one task at a time."""

import logging
import os
import socket
import threading
from time import sleep

from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import create_db_engine, create_session_factory
from app.models import OcrResultItem, OcrTask, ReportIngestion
from app.ocr_pipeline import PIPELINE_VERSION, OcrExecutionError, run_pipeline
from app.ocr_queue import claim, fail, owns_lease, renew, utcnow

logger = logging.getLogger(__name__)
WORKER_LOCK_KEY = 72403103


def heartbeat_interval_seconds() -> float:
    return min(60.0, get_settings().ocr_task_lease_seconds / 3)


def heartbeat(factory, task_id: str, worker_id: str, stop: threading.Event) -> None:
    while not stop.wait(heartbeat_interval_seconds()):
        try:
            with factory() as db:
                if not renew(db, task_id, worker_id):
                    return
        except Exception:  # noqa: BLE001 - a failed heartbeat must not expose OCR data
            logger.warning("task_id=%s error_code=OCR_HEARTBEAT_FAILED", task_id)


def process(factory, task: OcrTask, worker_id: str) -> None:
    stop = threading.Event()
    thread = threading.Thread(target=heartbeat, args=(factory, task.id, worker_id, stop), daemon=True)
    thread.start()
    try:
        with factory() as db:
            ingestion = db.get(ReportIngestion, task.ingestion_id)
            user_id = ingestion.user_id
        rows, candidates, summary, artifact_root = run_pipeline(task, user_id)
        with factory() as db:
            current = db.get(OcrTask, task.id, with_for_update=True)
            if not owns_lease(current, worker_id):
                db.rollback()
                logger.warning("task_id=%s error_code=OCR_LEASE_LOST", task.id)
                return
            for row in rows:
                db.add(OcrResultItem(ocr_task_id=task.id, **row))
            current.pipeline_version = PIPELINE_VERSION
            current.report_candidates = candidates
            current.result_summary = summary
            current.artifact_root = artifact_root
            current.status = "SUCCEEDED"
            current.finished_at = utcnow()
            current.worker_id = current.locked_at = current.lease_expires_at = None
            db.get(ReportIngestion, current.ingestion_id).status = "PENDING_CONFIRMATION"
            db.commit()
        logger.info("task_id=%s run_no=%s status=SUCCEEDED", task.id, task.run_no)
    except OcrExecutionError as exc:
        with factory() as db:
            fail(db, task.id, worker_id, exc.code, exc.recoverable)
        logger.warning("task_id=%s run_no=%s error_code=%s", task.id, task.run_no, exc.code)
    except Exception:  # noqa: BLE001 - unexpected execution failures consume a bounded attempt
        with factory() as db:
            fail(db, task.id, worker_id, "OCR_WORKER_ERROR", recoverable=True)
        logger.error("task_id=%s run_no=%s error_code=OCR_WORKER_ERROR", task.id, task.run_no)
    finally:
        stop.set()
        thread.join(timeout=5)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    if get_settings().ocr_worker_concurrency != 1:
        raise ValueError("OCR_WORKER_CONCURRENCY must be 1 in Stage 03")
    engine = create_db_engine()
    if engine.dialect.name != "postgresql":
        raise RuntimeError("OCR Worker requires PostgreSQL")
    factory = create_session_factory(engine)
    worker_id = f"{socket.gethostname()}-{os.getpid()}"
    logger.info("worker_id=%s concurrency=1", worker_id)
    try:
        with engine.connect() as lock_connection:
            if not lock_connection.scalar(text("SELECT pg_try_advisory_lock(:key)"),
                                          {"key": WORKER_LOCK_KEY}):
                raise RuntimeError("Another OCR Worker is already active")
            lock_connection.commit()
            try:
                while True:
                    try:
                        with factory() as db:
                            task = claim(db, worker_id)
                        if task is None:
                            sleep(3)
                            continue
                        process(factory, task, worker_id)
                    except Exception:  # noqa: BLE001 - resume polling after DB recovery
                        logger.error("worker_id=%s error_code=OCR_QUEUE_ERROR", worker_id)
                        sleep(5)
            finally:
                lock_connection.execute(text("SELECT pg_advisory_unlock(:key)"),
                                        {"key": WORKER_LOCK_KEY})
    except KeyboardInterrupt:
        logger.info("worker_id=%s status=STOPPED", worker_id)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
