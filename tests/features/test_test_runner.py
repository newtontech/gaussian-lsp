import json

import pytest
from lsprotocol.types import DiagnosticSeverity

from gaussian_lsp.features.test_runner import (
    SolverOutput,
    TestRunnerConfig,
    TestRunnerProvider,
    parse_solver_output,
    solver_output_to_diagnostics,
)


class TestConfig:
    def test_default_disabled(self):
        assert not TestRunnerConfig().enabled

    def test_validate_missing(self):
        assert len(TestRunnerConfig(enabled=True, executable="").validate()) == 1

    def test_validate_ok(self):
        assert len(TestRunnerConfig(executable="g16", enabled=True).validate()) == 0


class TestParse:
    def test_empty(self):
        assert parse_solver_output("").success

    def test_error(self):
        r = parse_solver_output("Error: invalid route\n")
        assert not r.success and len(r.errors) == 1

    def test_warning(self):
        r = parse_solver_output("Warning: deprecated keyword\n")
        assert r.success and len(r.warnings) == 1


class TestDiags:
    def test_error(self):
        d = solver_output_to_diagnostics(
            SolverOutput(errors=[{"message": "e", "line": 0, "source": "t"}])
        )
        assert d[0].code == "Gauss9001"

    def test_warning(self):
        d = solver_output_to_diagnostics(
            SolverOutput(warnings=[{"message": "w", "line": 0, "source": "t"}])
        )
        assert d[0].code == "Gauss9002"


class TestProvider:
    def test_disabled(self):
        assert (
            TestRunnerProvider().run_validation("x")[0].severity == DiagnosticSeverity.Information
        )

    def test_no_exec(self):
        assert (
            TestRunnerProvider(TestRunnerConfig(executable="", enabled=True))
            .run_validation("x")[0]
            .severity
            == DiagnosticSeverity.Warning
        )

    def test_missing(self):
        assert (
            TestRunnerProvider(TestRunnerConfig(executable="/nope", enabled=True))
            .run_validation("x")[0]
            .severity
            == DiagnosticSeverity.Error
        )

    def test_captured(self):
        assert len(TestRunnerProvider().run_with_captured_output("Error: bad\n")) == 1

    def test_clean(self):
        assert len(TestRunnerProvider().run_with_captured_output("ok\n")) == 0

    def test_snapshot(self):
        s = json.loads(
            TestRunnerProvider(TestRunnerConfig(executable="g16", enabled=True)).snapshot_config()
        )
        assert s["enabled"] and s["executable"] == "g16"
