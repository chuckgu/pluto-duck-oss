"""Parquet file connector."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable

import pyarrow.parquet as pq

from ..base import BaseConnector


class ParquetConnector(BaseConnector):
    name = "parquet"

    def __init__(self, config: Dict[str, object]) -> None:
        super().__init__(config)
        self.path = Path(config["path"])

    def fetch_metadata(self) -> Dict[str, object]:
        metadata = pq.read_metadata(self.path)
        return {
            "path": str(self.path),
            "rows": metadata.num_rows,
            "columns": metadata.num_columns,
        }

    def stream_rows(self) -> Iterable[Dict[str, object]]:
        table = pq.read_table(self.path)
        for batch in table.to_batches():
            for row in batch.to_pylist():
                yield row


