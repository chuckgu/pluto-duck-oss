"""CSV file connector."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, Iterable

from ..base import BaseConnector


def _coerce(value: str | None) -> object:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value


class CSVConnector(BaseConnector):
    name = "csv"

    def __init__(self, config: Dict[str, object]) -> None:
        super().__init__(config)
        self.path = Path(config["path"])

    def fetch_metadata(self) -> Dict[str, object]:
        return {
            "path": str(self.path),
        }

    def stream_rows(self) -> Iterable[Dict[str, object]]:
        with self.path.open("r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                yield {key: _coerce(value) for key, value in row.items()}


