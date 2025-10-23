"""Utility to load data into DuckDB tables."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List

import duckdb
import pandas as pd


def _quote_identifier(identifier: str) -> str:
    escaped = identifier.replace('"', '""')
    return f'"{escaped}"'


class DuckDBLoader:
    """Helper around DuckDB connections for ingestion tasks."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    def load_dicts(
        self,
        target_table: str,
        rows: Iterable[Dict[str, object]],
        *,
        overwrite: bool = False,
    ) -> int:
        rows_list: List[Dict[str, object]] = list(rows)
        if not rows_list:
            return 0

        # Use pandas DataFrame for better type handling
        df = pd.DataFrame(rows_list)
        
        con = duckdb.connect(str(self.database_path))
        try:
            safe_table = _quote_identifier(target_table)
            if overwrite:
                con.execute(f"DROP TABLE IF EXISTS {safe_table}")
            
            # DuckDB can directly create table from pandas DataFrame
            con.execute(f"CREATE TABLE {safe_table} AS SELECT * FROM df")
        finally:
            con.close()

        return len(rows_list)


