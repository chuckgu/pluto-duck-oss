"""Prompt loading utilities for agent nodes."""

from __future__ import annotations

from importlib import resources
from typing import Optional


def load_prompt(name: str, *, encoding: str = "utf-8") -> str:
    """Load a prompt template from the package resources."""

    package = __name__
    filename = f"{name}.txt"
    resource = resources.files(package).joinpath(filename)
    with resources.as_file(resource) as path:
        return path.read_text(encoding=encoding)


def try_load_prompt(name: str, *, encoding: str = "utf-8") -> Optional[str]:
    """Attempt to load a prompt template, returning None if missing."""

    try:
        return load_prompt(name, encoding=encoding)
    except FileNotFoundError:
        return None


