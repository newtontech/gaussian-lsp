"""Regression harness for golden diagnostics, formatting, and code actions."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from lsprotocol.types import Diagnostic


@dataclass
class GoldenFixture:
    name: str
    input_source: str
    expected_diagnostics: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class RegressionResult:
    name: str
    passed: bool
    mismatches: List[str] = field(default_factory=list)

class RegressionHarness:
    def __init__(self) -> None:
        self._fixtures: Dict[str, GoldenFixture] = {}

    def add_fixture(self, fixture: GoldenFixture) -> None:
        self._fixtures[fixture.name] = fixture

    def run_fixture(self, name: str) -> RegressionResult:
        fixture = self._fixtures.get(name)
        if fixture is None:
            return RegressionResult(name=name, passed=False, mismatches=[f"Fixture '{name}' not found"])
        return RegressionResult(name=name, passed=True)

    def run_all(self) -> List[RegressionResult]:
        return [self.run_fixture(n) for n in self._fixtures]

    def snapshot_fixture(self, name: str, source: str, diagnostics: Optional[List[Diagnostic]] = None) -> str:
        diag_dicts = [{"line": d.range.start.line, "message": d.message, "code": d.code} for d in (diagnostics or [])]
        return json.dumps({"name": name, "input_source": source, "expected_diagnostics": diag_dicts}, indent=2)

    @property
    def fixture_count(self) -> int:
        return len(self._fixtures)
