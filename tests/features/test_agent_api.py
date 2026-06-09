import json, pytest
from lsprotocol.types import Diagnostic, DiagnosticSeverity, Position, Range
from gaussian_lsp.features.agent_api import AgentAPIProvider, AgentAPISnapshot

class TestSnapshot:
    def test_to_json(self):
        s = AgentAPISnapshot(uri="test", diagnostics=[{"line": 0}])
        assert json.loads(s.to_json())["uri"] == "test"

class TestProvider:
    def test_empty(self):
        snap = AgentAPIProvider().get_snapshot("")
        assert snap.diagnostics == []

    def test_with_diagnostics(self):
        diags = [Diagnostic(range=Range(start=Position(0, 0), end=Position(0, 0)),
            message="err", severity=DiagnosticSeverity.Error, source="test", code="X1")]
        snap = AgentAPIProvider().get_snapshot("test", diagnostics=diags)
        assert len(snap.diagnostics) == 1

    def test_outline(self):
        snap = AgentAPIProvider().get_outline_json("title test\n")
        assert "outline" in snap

    def test_metadata(self):
        snap = AgentAPIProvider().get_snapshot("test")
        assert snap.metadata["language"] == "gaussian"

    def test_diags_json(self):
        r = AgentAPIProvider().get_diagnostics_json("test")
        assert "count" in r
