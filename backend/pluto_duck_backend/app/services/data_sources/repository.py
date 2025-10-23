"""Repository for managing data sources."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

import duckdb

from pluto_duck_backend.app.core.config import get_settings


@dataclass
class DataSource:
    """Data source entity."""

    id: str
    project_id: Optional[str]
    name: str
    description: Optional[str]
    connector_type: str
    source_config: Dict[str, Any]
    target_table: str
    rows_count: Optional[int]
    status: str
    last_imported_at: Optional[datetime]
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime
    metadata: Optional[Dict[str, Any]]


class DataSourceRepository:
    """Repository for data source CRUD operations."""

    def __init__(self, warehouse_path: Path, default_project_id: str) -> None:
        self.warehouse_path = warehouse_path
        self.default_project_id = default_project_id

    def _connect(self) -> duckdb.DuckDBPyConnection:
        return duckdb.connect(str(self.warehouse_path))

    def create(
        self,
        name: str,
        connector_type: str,
        source_config: Dict[str, Any],
        target_table: str,
        *,
        description: Optional[str] = None,
        project_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Create a new data source record."""
        source_id = str(uuid4())
        now = datetime.now(UTC)
        
        with self._connect() as con:
            con.execute(
                """
                INSERT INTO data_sources (
                    id, project_id, name, description, connector_type, 
                    source_config, target_table, status, created_at, updated_at, metadata
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?)
                """,
                [
                    source_id,
                    project_id or self.default_project_id,
                    name,
                    description,
                    connector_type,
                    json.dumps(source_config),
                    target_table,
                    now,
                    now,
                    json.dumps(metadata or {}),
                ],
            )
        
        return source_id

    def list_all(self, project_id: Optional[str] = None) -> List[DataSource]:
        """List all data sources, optionally filtered by project."""
        with self._connect() as con:
            if project_id:
                rows = con.execute(
                    """
                    SELECT id, project_id, name, description, connector_type, 
                           source_config, target_table, rows_count, status, 
                           last_imported_at, error_message, created_at, updated_at, metadata
                    FROM data_sources
                    WHERE project_id = ?
                    ORDER BY updated_at DESC
                    """,
                    [project_id],
                ).fetchall()
            else:
                rows = con.execute(
                    """
                    SELECT id, project_id, name, description, connector_type, 
                           source_config, target_table, rows_count, status, 
                           last_imported_at, error_message, created_at, updated_at, metadata
                    FROM data_sources
                    ORDER BY updated_at DESC
                    """
                ).fetchall()
        
        return [self._row_to_entity(row) for row in rows]

    def get(self, source_id: str) -> Optional[DataSource]:
        """Get a single data source by ID."""
        with self._connect() as con:
            row = con.execute(
                """
                SELECT id, project_id, name, description, connector_type, 
                       source_config, target_table, rows_count, status, 
                       last_imported_at, error_message, created_at, updated_at, metadata
                FROM data_sources
                WHERE id = ?
                """,
                [source_id],
            ).fetchone()
        
        if not row:
            return None
        
        return self._row_to_entity(row)

    def update_import_status(
        self,
        source_id: str,
        *,
        status: str,
        rows_count: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Update import status after sync/import."""
        now = datetime.now(UTC)
        
        with self._connect() as con:
            con.execute(
                """
                UPDATE data_sources
                SET status = ?, rows_count = ?, last_imported_at = ?, 
                    error_message = ?, updated_at = ?
                WHERE id = ?
                """,
                [status, rows_count, now, error_message, now, source_id],
            )

    def delete(self, source_id: str) -> bool:
        """Delete a data source record."""
        with self._connect() as con:
            exists = con.execute(
                "SELECT 1 FROM data_sources WHERE id = ?",
                [source_id],
            ).fetchone()
            
            if not exists:
                return False
            
            con.execute("DELETE FROM data_sources WHERE id = ?", [source_id])
        
        return True

    def _row_to_entity(self, row: tuple) -> DataSource:
        """Convert database row to DataSource entity."""
        return DataSource(
            id=str(row[0]),
            project_id=str(row[1]) if row[1] else None,
            name=row[2],
            description=row[3],
            connector_type=row[4],
            source_config=json.loads(row[5]) if row[5] else {},
            target_table=row[6],
            rows_count=row[7],
            status=row[8],
            last_imported_at=self._ensure_utc(row[9]) if row[9] else None,
            error_message=row[10],
            created_at=self._ensure_utc(row[11]),
            updated_at=self._ensure_utc(row[12]),
            metadata=json.loads(row[13]) if row[13] else None,
        )

    def _ensure_utc(self, value: datetime) -> datetime:
        """Ensure datetime has UTC timezone."""
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


@lru_cache(maxsize=1)
def get_data_source_repository() -> DataSourceRepository:
    """Get singleton data source repository instance."""
    from pluto_duck_backend.app.services.chat import get_chat_repository
    
    settings = get_settings()
    chat_repo = get_chat_repository()
    
    return DataSourceRepository(
        warehouse_path=settings.duckdb.path,
        default_project_id=chat_repo._default_project_id,
    )

