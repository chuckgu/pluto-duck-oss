"""Data sources management endpoints."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from pluto_duck_backend.app.services.data_sources import DataSourceRepository, get_data_source_repository
from pluto_duck_backend.app.services.ingestion import IngestionJob, IngestionService, get_registry
from pluto_duck_backend.app.core.config import get_settings

router = APIRouter(prefix="/data-sources", tags=["data-sources"])


class CreateDataSourceRequest(BaseModel):
    """Request to create and import a new data source."""

    name: str = Field(..., description="Display name for the data source")
    description: Optional[str] = Field(None, description="Optional description")
    connector_type: str = Field(..., description="Connector type: csv, parquet, postgres, sqlite")
    source_config: Dict[str, Any] = Field(..., description="Connector-specific configuration")
    target_table: str = Field(..., description="Target DuckDB table name")
    overwrite: bool = Field(False, description="Overwrite existing table")


class DataSourceResponse(BaseModel):
    """Response model for a data source."""

    id: str
    name: str
    description: Optional[str]
    connector_type: str
    source_config: Dict[str, Any]
    target_table: str
    rows_count: Optional[int]
    status: str
    last_imported_at: Optional[str]
    error_message: Optional[str]
    created_at: str
    updated_at: str


class CreateDataSourceResponse(BaseModel):
    """Response after creating and importing a data source."""

    id: str
    status: str
    rows_imported: Optional[int]
    message: str


class SyncResponse(BaseModel):
    """Response after syncing a data source."""

    status: str
    rows_imported: Optional[int]
    message: str


def get_repository() -> DataSourceRepository:
    """Dependency to get data source repository."""
    return get_data_source_repository()


def get_ingestion_service() -> IngestionService:
    """Dependency to get ingestion service."""
    registry = get_registry()
    return IngestionService(registry)


@router.get("", response_model=List[DataSourceResponse])
def list_data_sources(
    repo: DataSourceRepository = Depends(get_repository),
) -> List[DataSourceResponse]:
    """List all data sources."""
    sources = repo.list_all()
    
    return [
        DataSourceResponse(
            id=source.id,
            name=source.name,
            description=source.description,
            connector_type=source.connector_type,
            source_config=source.source_config,
            target_table=source.target_table,
            rows_count=source.rows_count,
            status=source.status,
            last_imported_at=source.last_imported_at.isoformat() if source.last_imported_at else None,
            error_message=source.error_message,
            created_at=source.created_at.isoformat(),
            updated_at=source.updated_at.isoformat(),
        )
        for source in sources
    ]


@router.post("", response_model=CreateDataSourceResponse)
def create_data_source(
    request: CreateDataSourceRequest,
    repo: DataSourceRepository = Depends(get_repository),
    ingestion_service: IngestionService = Depends(get_ingestion_service),
) -> CreateDataSourceResponse:
    """Create a new data source and import data."""
    settings = get_settings()
    
    # Create data source record
    source_id = repo.create(
        name=request.name,
        connector_type=request.connector_type,
        source_config=request.source_config,
        target_table=request.target_table,
        description=request.description,
    )
    
    # Run ingestion
    try:
        job = IngestionJob(
            connector=request.connector_type,
            target_table=request.target_table,
            warehouse_path=settings.duckdb.path,
            overwrite=request.overwrite,
            config=request.source_config,
        )
        
        result = ingestion_service.run(job)
        rows_imported = result.get("rows_ingested")
        
        # Update status to active
        repo.update_import_status(
            source_id,
            status="active",
            rows_count=rows_imported,
        )
        
        return CreateDataSourceResponse(
            id=source_id,
            status="active",
            rows_imported=rows_imported,
            message=f"Successfully imported {rows_imported} rows",
        )
    except Exception as exc:
        # Update status to error
        repo.update_import_status(
            source_id,
            status="error",
            error_message=str(exc),
        )
        
        raise HTTPException(
            status_code=500,
            detail=f"Failed to import data: {str(exc)}",
        ) from exc


@router.post("/{source_id}/sync", response_model=SyncResponse)
def sync_data_source(
    source_id: str,
    repo: DataSourceRepository = Depends(get_repository),
    ingestion_service: IngestionService = Depends(get_ingestion_service),
) -> SyncResponse:
    """Re-import data from an existing data source."""
    settings = get_settings()
    
    # Get existing source
    source = repo.get(source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Data source not found")
    
    # Run ingestion
    try:
        repo.update_import_status(source_id, status="syncing")
        
        job = IngestionJob(
            connector=source.connector_type,
            target_table=source.target_table,
            warehouse_path=settings.duckdb.path,
            overwrite=True,  # Always overwrite on sync
            config=source.source_config,
        )
        
        result = ingestion_service.run(job)
        rows_imported = result.get("rows_ingested")
        
        # Update status to active
        repo.update_import_status(
            source_id,
            status="active",
            rows_count=rows_imported,
        )
        
        return SyncResponse(
            status="active",
            rows_imported=rows_imported,
            message=f"Successfully synced {rows_imported} rows",
        )
    except Exception as exc:
        # Update status to error
        repo.update_import_status(
            source_id,
            status="error",
            error_message=str(exc),
        )
        
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sync data: {str(exc)}",
        ) from exc


@router.delete("/{source_id}")
def delete_data_source(
    source_id: str,
    drop_table: bool = False,
    repo: DataSourceRepository = Depends(get_repository),
) -> Dict[str, str]:
    """Delete a data source record and optionally drop the DuckDB table."""
    source = repo.get(source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Data source not found")
    
    # Optionally drop the DuckDB table
    if drop_table:
        settings = get_settings()
        try:
            with duckdb.connect(str(settings.duckdb.path)) as con:
                con.execute(f"DROP TABLE IF EXISTS {source.target_table}")
        except Exception as exc:
            # Log but don't fail the deletion
            pass
    
    # Delete the source record
    deleted = repo.delete(source_id)
    
    if not deleted:
        raise HTTPException(status_code=404, detail="Data source not found")
    
    return {
        "message": f"Data source '{source.name}' deleted successfully",
        "table_dropped": drop_table,
    }

