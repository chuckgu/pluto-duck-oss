"""Service to orchestrate dbt commands programmatically."""

from __future__ import annotations

import json
import os
import subprocess
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import duckdb


class DbtInvocationError(RuntimeError):
    """Raised when a dbt command fails."""


class DbtService:
    """Wraps dbt CLI to run projects bundled with Pluto-Duck."""

    def __init__(
        self,
        project_dir: Path,
        profiles_dir: Path,
        artifacts_dir: Path,
        warehouse_path: Path,
    ) -> None:
        self.project_dir = project_dir
        self.profiles_dir = profiles_dir
        self.artifacts_dir = artifacts_dir
        self.warehouse_path = warehouse_path
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

    def _run_dbt(
        self,
        args: List[str],
        *,
        env: Optional[Dict[str, str]] = None,
        command_name: str,
    ) -> Dict[str, object]:
        command = ["dbt"] + args + ["--target-path", str(self.artifacts_dir)]
        try:
            process = subprocess.run(
                command,
                cwd=self.project_dir,
                env={**dict(os.environ), **(env or {})},
                text=True,
                capture_output=True,
                check=False,
            )
        except FileNotFoundError as exc:
            raise DbtInvocationError(str(exc)) from exc
        if process.returncode != 0:
            raise DbtInvocationError(process.stderr)

        summary = self._ingest_artifacts(command_name)
        summary["stdout"] = process.stdout
        summary["stderr"] = process.stderr
        return summary

    def _ingest_artifacts(self, command_name: str) -> Dict[str, object]:
        run_id = str(uuid.uuid4())
        run_results_path = self.artifacts_dir / "run_results.json"
        manifest_path = self.artifacts_dir / "manifest.json"

        generated_at: Optional[datetime] = None
        models: List[Dict[str, object]] = []

        if run_results_path.exists():
            with run_results_path.open("r", encoding="utf-8") as fh:
                run_results = json.load(fh)
            metadata = run_results.get("metadata", {})
            generated_at_str = metadata.get("generated_at")
            if generated_at_str:
                try:
                    generated_at = datetime.fromisoformat(generated_at_str.replace("Z", "+00:00"))
                except ValueError:
                    generated_at = None
            for result in run_results.get("results", []):
                models.append(
                    {
                        "unique_id": result.get("unique_id"),
                        "status": result.get("status"),
                        "execution_time": result.get("execution_time"),
                    }
                )

        manifest_models: Dict[str, Dict[str, object]] = {}
        if manifest_path.exists():
            with manifest_path.open("r", encoding="utf-8") as fh:
                manifest = json.load(fh)
            manifest_models = manifest.get("nodes", {})

        self._persist_metadata(run_id, command_name, generated_at, models, manifest_models)

        return {
            "run_id": run_id,
            "command": command_name,
            "generated_at": generated_at.isoformat() if generated_at else None,
            "artifacts_path": str(self.artifacts_dir),
            "models": models,
        }

    def _persist_metadata(
        self,
        run_id: str,
        command_name: str,
        generated_at: Optional[datetime],
        models: List[Dict[str, object]],
        manifest_models: Dict[str, Dict[str, object]],
    ) -> None:
        con = duckdb.connect(str(self.warehouse_path))
        try:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS dbt_run_history (
                    run_id TEXT PRIMARY KEY,
                    command TEXT,
                    generated_at TIMESTAMP,
                    artifacts_path TEXT
                )
                """
            )
            con.execute(
                """
                INSERT OR REPLACE INTO dbt_run_history (run_id, command, generated_at, artifacts_path)
                VALUES (?, ?, ?, ?)
                """,
                [run_id, command_name, generated_at, str(self.artifacts_dir)],
            )

            con.execute(
                """
                CREATE TABLE IF NOT EXISTS dbt_models (
                    unique_id TEXT PRIMARY KEY,
                    name TEXT,
                    resource_type TEXT,
                    status TEXT,
                    execution_time DOUBLE,
                    last_run TIMESTAMP
                )
                """
            )
            for model in models:
                unique_id = model.get("unique_id")
                if not unique_id:
                    continue
                manifest_entry = manifest_models.get(unique_id, {})
                name = manifest_entry.get("name")
                resource_type = manifest_entry.get("resource_type")
                con.execute(
                    """
                    INSERT OR REPLACE INTO dbt_models (unique_id, name, resource_type, status, execution_time, last_run)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    [
                        unique_id,
                        name,
                        resource_type,
                        model.get("status"),
                        model.get("execution_time"),
                        generated_at,
                    ],
                )
        finally:
            con.close()

    def run(
        self,
        select: Optional[List[str]] = None,
        vars: Optional[Dict[str, str]] = None,
    ) -> Dict[str, object]:
        args = ["run", "--profiles-dir", str(self.profiles_dir)]
        if select:
            args += ["--select", " ".join(select)]
        if vars:
            args += ["--vars", json.dumps(vars)]
        return self._run_dbt(args, command_name="run")

    def test(self, select: Optional[List[str]] = None) -> Dict[str, object]:
        args = ["test", "--profiles-dir", str(self.profiles_dir)]
        if select:
            args += ["--select", " ".join(select)]
        return self._run_dbt(args, command_name="test")

