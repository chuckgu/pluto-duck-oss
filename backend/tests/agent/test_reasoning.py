"""Tests for the reasoning node decision parsing."""

from __future__ import annotations

import pytest

from pluto_duck_backend.agent.core.nodes.reasoning import _parse_decision


@pytest.mark.parametrize(
    "response,expected",
    [
        ('{"next": "schema", "reason": "Need metadata"}', ("schema", "Need metadata")),
        ('{"next": "FINAL", "reason": "Done"}', ("finalize", "Done")),
        ('{"next": "unknown", "reason": "?"}', ("planner", "?")),
        ("not-json", ("planner", "not-json")),
    ],
)
def test_parse_decision(response: str, expected: tuple[str, str]) -> None:
    parsed = _parse_decision(response)
    assert parsed["next"] == expected[0]
    assert parsed["reason"] == expected[1]


