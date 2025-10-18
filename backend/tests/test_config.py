from pathlib import Path

from pluto_duck_backend.app.core.config import DEFAULT_DATA_ROOT, PlutoDuckSettings, get_settings


def test_settings_singleton(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("PLUTODUCK_DATA_DIR__ROOT", str(tmp_path / "root"))
    get_settings.cache_clear()

    first = get_settings()
    second = get_settings()

    assert first is second
    assert first.data_dir.root == tmp_path / "root"


def test_settings_prepare_environment(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("PLUTODUCK_DATA_DIR__ROOT", str(tmp_path / "root"))
    monkeypatch.setenv("PLUTODUCK_AGENT__PROVIDER", "mock")
    settings = PlutoDuckSettings()
    settings.prepare_environment()

    assert settings.data_dir.root.exists()
    assert settings.dbt.project_path.is_relative_to(settings.data_dir.root)
    assert settings.agent.provider == "mock"
    assert settings.dbt.profiles_path is not None


def test_default_paths_under_home(monkeypatch) -> None:
    monkeypatch.delenv("PLUTODUCK_DATA_DIR__ROOT", raising=False)
    get_settings.cache_clear()

    settings = get_settings()
    assert settings.data_dir.root == DEFAULT_DATA_ROOT

