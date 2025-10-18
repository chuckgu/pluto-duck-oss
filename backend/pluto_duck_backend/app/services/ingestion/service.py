"""High-level ingestion service orchestrating connectors."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

from .base import IngestionContext
from .registry import ConnectorRegistry


@dataclass
class IngestionJob:
    connector: str
    target_table: str
    warehouse_path: Path
    overwrite: bool = False
    config: Dict[str, object] | None = None


class IngestionService:
    """Coordinates ingestion workflows using registered connectors."""

    def __init__(self, registry: ConnectorRegistry) -> None:
        self.registry = registry

    def run(self, job: IngestionJob) -> Dict[str, object]:
        connector = self.registry.create(job.connector, job.config or {})
        connector.open()
        try:
            context = IngestionContext(
                target_table=job.target_table,
                warehouse_path=job.warehouse_path,
                overwrite=job.overwrite,
            )
            row_count = connector.materialize(context)
            metadata = connector.fetch_metadata()
        finally:
            connector.close()

        return {
            "rows_ingested": row_count,
            "metadata": metadata,
        }


