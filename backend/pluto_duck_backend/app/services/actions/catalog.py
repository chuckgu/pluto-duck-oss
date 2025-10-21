"""Catalog mapping logical subjects/actions to service calls."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from pluto_duck_backend.app.core.config import get_settings
from pluto_duck_backend.app.services.execution.manager import get_execution_manager
from pluto_duck_backend.app.services.ingestion import IngestionJob, IngestionService, get_registry
from pluto_duck_backend.app.services.transformation import DbtService
import duckdb


@dataclass
class ActionDefinition:
    subject: str
    action: str
    description: str
    handler: Callable[..., dict]

    def to_dict(self) -> Dict[str, object]:
        return {
            "subject": self.subject,
            "action": self.action,
            "description": self.description,
        }


class ActionCatalog:
    """In-memory catalog of actions available to the agent/API."""

    def __init__(self) -> None:
        self._actions: Dict[str, ActionDefinition] = {}

    def register(self, definition: ActionDefinition) -> None:
        key = self._key(definition.subject, definition.action)
        self._actions[key] = definition

    def list_actions(self, subject: Optional[str] = None) -> List[ActionDefinition]:
        if subject is None:
            return list(self._actions.values())
        return [action for action in self._actions.values() if action.subject == subject]

    def get(self, subject: str, action: str) -> ActionDefinition:
        key = self._key(subject, action)
        return self._actions[key]

    @staticmethod
    def _key(subject: str, action: str) -> str:
        return f"{subject}:{action}"


def _build_default_catalog() -> ActionCatalog:
    catalog = ActionCatalog()

    def query_handler(sql: str) -> dict:
        manager = get_execution_manager()
        run_id = manager.submit_sql(sql)
        job = manager.wait_for(run_id)
        if not job:
            raise RuntimeError("Query job missing")
        return {
            "run_id": job.run_id,
            "status": job.status,
            "result_table": job.result_table,
            "error": job.error,
        }

    def ingestion_handler(connector: str, target_table: str, config: Optional[dict] = None, overwrite: bool = False) -> dict:
        registry = get_registry()
        service = IngestionService(registry)
        settings = get_settings()
        job = IngestionJob(
            connector=connector,
            target_table=target_table,
            warehouse_path=settings.duckdb.path,
            overwrite=overwrite,
            config=config or {},
        )
        return service.run(job)

    def dbt_run_handler(select: Optional[List[str]] = None, vars: Optional[dict] = None) -> dict:
        settings = get_settings()
        service = DbtService(
            settings.dbt.project_path,
            settings.dbt.profiles_path,
            settings.data_dir.artifacts / "dbt",
            settings.duckdb.path,
        )
        return service.run(select=select, vars=vars)

    def dbt_test_handler(select: Optional[List[str]] = None) -> dict:
        settings = get_settings()
        service = DbtService(
            settings.dbt.project_path,
            settings.dbt.profiles_path,
            settings.data_dir.artifacts / "dbt",
            settings.duckdb.path,
        )
        return service.test(select=select)

    catalog.register(
        ActionDefinition(
            subject="query",
            action="run",
            description="Execute SQL against the local DuckDB warehouse.",
            handler=query_handler,
        )
    )

    catalog.register(
        ActionDefinition(
            subject="ingestion",
            action="run",
            description="Run an ingestion connector to load data into DuckDB.",
            handler=ingestion_handler,
        )
    )

    catalog.register(
        ActionDefinition(
            subject="dbt",
            action="run",
            description="Run dbt models in the configured project.",
            handler=dbt_run_handler,
        )
    )

    catalog.register(
        ActionDefinition(
            subject="dbt",
            action="test",
            description="Run dbt tests in the configured project.",
            handler=dbt_test_handler,
        )
    )

    _persist_catalog(catalog)

    return catalog


def _persist_catalog(catalog: ActionCatalog) -> None:
    settings = get_settings()
    warehouse_path = settings.duckdb.path
    if not warehouse_path.exists():
        return
    con = duckdb.connect(str(warehouse_path))
    try:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS action_catalog (
                subject TEXT,
                action TEXT,
                description TEXT,
                PRIMARY KEY (subject, action)
            )
            """
        )
        con.execute("DELETE FROM action_catalog")
        for action in catalog.list_actions():
            con.execute(
                "INSERT INTO action_catalog (subject, action, description) VALUES (?, ?, ?)",
                [action.subject, action.action, action.description],
            )
    except duckdb.IOException:
        # Warehouse might not exist yet (e.g., during tests); skip persistence.
        pass
    finally:
        con.close()


_DEFAULT_CATALOG = _build_default_catalog()


def get_action_catalog() -> ActionCatalog:
    return _DEFAULT_CATALOG

