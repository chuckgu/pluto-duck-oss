"""Background execution manager for query jobs."""

from __future__ import annotations

import logging
import time
from functools import lru_cache
from queue import Queue
from threading import Thread
from typing import Optional

from pluto_duck_backend.app.core.config import get_settings

from .service import QueryExecutionService

logger = logging.getLogger(__name__)


class QueryExecutionManager:
    """Simple background worker that executes queued query jobs."""

    def __init__(self, service: QueryExecutionService, worker_count: int = 1) -> None:
        self.service = service
        self._queue: Queue[str] = Queue()
        self._workers = [
            Thread(target=self._worker, name=f"query-worker-{idx}", daemon=True)
            for idx in range(worker_count)
        ]
        for worker in self._workers:
            worker.start()

    def enqueue(self, job_id: str) -> None:
        logger.debug("Enqueuing query job %s", job_id)
        self._queue.put(job_id)

    def submit_sql(self, sql: str, job_id: Optional[str] = None) -> str:
        from uuid import uuid4

        job_identifier = job_id or str(uuid4())
        self.service.submit(job_identifier, sql)
        self.enqueue(job_identifier)
        return job_identifier

    def wait_for(self, job_id: str, timeout: float = 10.0, poll_interval: float = 0.1):
        deadline = time.time() + timeout
        while time.time() < deadline:
            job = self.service.fetch(job_id)
            if job and job.status != "pending":
                return job
            time.sleep(poll_interval)
        return self.service.fetch(job_id)

    def _worker(self) -> None:
        while True:
            job_id = self._queue.get()
            try:
                logger.debug("Executing queued query job %s", job_id)
                self.service.execute(job_id)
            except Exception:  # pragma: no cover - logging only
                logger.exception("Query job %s failed during execution", job_id)
            finally:
                self._queue.task_done()


@lru_cache(maxsize=1)
def get_execution_manager() -> QueryExecutionManager:
    settings = get_settings()
    service = QueryExecutionService(settings.duckdb.path)
    return QueryExecutionManager(service)

