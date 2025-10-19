"""Ingestion service package with connector registry."""

from .registry import ConnectorRegistry, get_registry
from .service import IngestionJob, IngestionService

__all__ = ["ConnectorRegistry", "get_registry", "IngestionService", "IngestionJob"]


def _register_bundled_connectors() -> None:
    from .connectors import CSVConnector, ParquetConnector, PostgresConnector, SQLiteConnector

    registry = get_registry()
    for connector in (CSVConnector, ParquetConnector, PostgresConnector, SQLiteConnector):
        try:
            registry.register(connector)
        except ValueError:
            # Already registered
            pass


_register_bundled_connectors()

