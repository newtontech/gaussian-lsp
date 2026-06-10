"""Tests for the DiagnosticProvider feature."""

import json

import pytest
from lsprotocol.types import DiagnosticSeverity
from pygls.server import LanguageServer

from gaussian_lsp.features.diagnostic import DiagnosticProvider


@pytest.fixture
def provider() -> DiagnosticProvider:
    """Create a DiagnosticProvider instance for testing."""
    server = LanguageServer("test-gaussian-lsp", "0.0.0")
    return DiagnosticProvider(server)


# ---------------------------------------------------------------------------
# Basic provider existence
# ---------------------------------------------------------------------------


class TestDiagnosticProviderInit:
    """Test provider instantiation."""

    def test_provider_exists(self, provider: DiagnosticProvider) -> None:
        """Test that provider can be created."""
        assert provider is not None

    def test_provider_has_server(self, provider: DiagnosticProvider) -> None:
        """Test provider stores the server reference."""
        assert provider.server is not None


# ---------------------------------------------------------------------------
# Empty / minimal inputs
# ---------------------------------------------------------------------------


class TestEmptyInput:
    """Test diagnostics for empty or trivial inputs."""

    def test_empty_string_returns_diagnostics(self, provider: DiagnosticProvider) -> None:
        """Empty string is an invalid GJF and should produce parse-error diagnostics."""
        diagnostics = provider.get_diagnostics("")
        assert isinstance(diagnostics, list)
        assert len(diagnostics) > 0

    def test_whitespace_only_returns_diagnostics(self, provider: DiagnosticProvider) -> None:
        """Whitespace-only input should produce diagnostics."""
        diagnostics = provider.get_diagnostics("   \n  \n")
        assert isinstance(diagnostics, list)
        assert len(diagnostics) > 0


# ---------------------------------------------------------------------------
# Valid inputs (no diagnostics or only minor warnings)
# ---------------------------------------------------------------------------


class TestValidInput:
    """Test diagnostics for well-formed Gaussian input."""

    VALID_WATER = """\
# B3LYP/6-31G(d) opt freq

Water optimization

0 1
O  0.000000  0.000000  0.000000
H  0.000000  0.758602  0.504284
H  0.000000 -0.758602  0.504284
"""

    def test_valid_input_no_errors(self, provider: DiagnosticProvider) -> None:
        """Valid input should produce zero error-severity diagnostics."""
        diagnostics = provider.get_diagnostics(self.VALID_WATER)
        errors = [d for d in diagnostics if d.severity == DiagnosticSeverity.Error]
        assert errors == []

    def test_valid_input_returns_list(self, provider: DiagnosticProvider) -> None:
        """Diagnostics should always be a list."""
        diagnostics = provider.get_diagnostics(self.VALID_WATER)
        assert isinstance(diagnostics, list)


# ---------------------------------------------------------------------------
# Warning-level diagnostics
# ---------------------------------------------------------------------------


class TestWarningDiagnostics:
    """Test warning-level diagnostics."""

    def test_unknown_element_warning(self, provider: DiagnosticProvider) -> None:
        """Unknown element symbols should produce a warning."""
        content = """\
# B3LYP/6-31G(d) opt

Bad element

0 1
Xx 0.0 0.0 0.0
"""
        diagnostics = provider.get_diagnostics(content)
        warnings = [d for d in diagnostics if d.severity == DiagnosticSeverity.Warning]
        assert any("unknown" in d.message.lower() for d in warnings)

    def test_no_method_warning(self, provider: DiagnosticProvider) -> None:
        """Route without a recognizable method should warn."""
        content = """\
# /6-31G(d) opt

No method

0 1
H 0.0 0.0 0.0
H 0.0 0.0 0.7
"""
        diagnostics = provider.get_diagnostics(content)
        messages = [d.message for d in diagnostics]
        assert any("method" in m.lower() for m in messages)

    def test_no_basis_set_warning(self, provider: DiagnosticProvider) -> None:
        """Route without a recognizable basis set should warn."""
        content = """\
# B3LYP opt

No basis

0 1
H 0.0 0.0 0.0
H 0.0 0.0 0.7
"""
        diagnostics = provider.get_diagnostics(content)
        messages = [d.message for d in diagnostics]
        assert any("basis" in m.lower() for m in messages)

    def test_ecp_basis_with_light_elements_warning(self, provider: DiagnosticProvider) -> None:
        """ECP basis set on light-only elements should warn."""
        content = """\
# B3LYP/LANL2DZ

Water with ECP

0 1
O 0.0 0.0 0.0
H 0.0 0.0 1.0
H 1.0 0.0 0.0
"""
        diagnostics = provider.get_diagnostics(content)
        warnings = [d for d in diagnostics if d.severity == DiagnosticSeverity.Warning]
        assert any("ECP" in d.message for d in warnings)


# ---------------------------------------------------------------------------
# Error-level diagnostics
# ---------------------------------------------------------------------------


class TestErrorDiagnostics:
    """Test error-level diagnostics."""

    def test_missing_route_section(self, provider: DiagnosticProvider) -> None:
        """Missing route section should produce an error."""
        content = """\
Test

0 1
H 0.0 0.0 0.0
"""
        diagnostics = provider.get_diagnostics(content)
        errors = [d for d in diagnostics if d.severity == DiagnosticSeverity.Error]
        assert any("route" in e.message.lower() for e in errors)

    def test_missing_atoms(self, provider: DiagnosticProvider) -> None:
        """Missing atoms should produce an error."""
        content = """\
# B3LYP/6-31G(d)

Empty geometry

0 1
"""
        diagnostics = provider.get_diagnostics(content)
        errors = [d for d in diagnostics if d.severity == DiagnosticSeverity.Error]
        assert any("atom" in e.message.lower() for e in errors)

    def test_invalid_route_keyword_typo(self, provider: DiagnosticProvider) -> None:
        """Common route typos like 'optimize' should produce errors."""
        content = """\
# B3LYP/6-31G(d) optimize

Typo route

0 1
H 0.0 0.0 0.0
H 0.0 0.0 0.7
"""
        diagnostics = provider.get_diagnostics(content)
        messages = [d.message for d in diagnostics]
        assert any("opt instead of optimize" in m for m in messages)

    def test_invalid_charge_multiplicity(self, provider: DiagnosticProvider) -> None:
        """Non-numeric charge/multiplicity should produce an error."""
        content = """\
# B3LYP/6-31G(d)

Bad charge mult

0 singlet
H 0.0 0.0 0.0
"""
        diagnostics = provider.get_diagnostics(content)
        messages = [d.message for d in diagnostics]
        assert any("Invalid charge/multiplicity" in m for m in messages)

    def test_missing_blank_line_after_route(self, provider: DiagnosticProvider) -> None:
        """Missing blank line after route should produce an error."""
        content = """\
# B3LYP/6-31G(d)
No blank line
0 1
O 0.0 0.0 0.0
"""
        diagnostics = provider.get_diagnostics(content)
        messages = [d.message for d in diagnostics]
        assert any("blank line after route" in m.lower() for m in messages)

    def test_mutually_exclusive_scf_methods(self, provider: DiagnosticProvider) -> None:
        """Mutually exclusive SCF methods should produce an error."""
        content = """\
# RHF UHF/6-31G(d)

Bad SCF

0 1
H 0.0 0.0 0.0
"""
        diagnostics = provider.get_diagnostics(content)
        messages = [d.message for d in diagnostics]
        assert any("Mutually exclusive SCF" in m for m in messages)

    def test_sp_and_opt_conflict(self, provider: DiagnosticProvider) -> None:
        """SP and OPT together should produce an error."""
        content = """\
# SP OPT B3LYP/6-31G(d)

Conflicting job types

0 1
H 0.0 0.0 0.0
"""
        diagnostics = provider.get_diagnostics(content)
        messages = [d.message for d in diagnostics]
        assert any("SP and OPT are mutually exclusive" in m for m in messages)

    def test_multiple_basis_sets(self, provider: DiagnosticProvider) -> None:
        """Multiple basis sets in route should produce an error."""
        content = """\
# B3LYP/6-31G(d) cc-pVDZ

Multiple basis

0 1
H 0.0 0.0 0.0
"""
        diagnostics = provider.get_diagnostics(content)
        messages = [d.message for d in diagnostics]
        assert any("Multiple basis sets" in m for m in messages)

    def test_gen_basis_missing_section(self, provider: DiagnosticProvider) -> None:
        """Gen basis without custom section should produce an error."""
        content = """\
# B3LYP/Gen

Missing basis data

0 1
H 0.0 0.0 0.0
"""
        diagnostics = provider.get_diagnostics(content)
        messages = [d.message for d in diagnostics]
        assert any("Gen basis set is requested" in m for m in messages)


# ---------------------------------------------------------------------------
# Snapshot (JSON-serializable) tests
# ---------------------------------------------------------------------------


class TestDiagnosticSnapshot:
    """Test the JSON-serializable diagnostic snapshot."""

    def test_snapshot_is_list(self, provider: DiagnosticProvider) -> None:
        """Snapshot should always return a list."""
        snapshot = provider.get_diagnostics_snapshot("")
        assert isinstance(snapshot, list)

    def test_snapshot_is_json_serializable(self, provider: DiagnosticProvider) -> None:
        """Snapshot should be serializable with json.dumps."""
        snapshot = provider.get_diagnostics_snapshot(
            "# B3LYP/6-31G(d)\n\nTest\n\n0 1\nH 0.0 0.0 0.0\n"
        )
        serialized = json.dumps(snapshot)
        assert isinstance(serialized, str)
        # Round-trip should work
        parsed = json.loads(serialized)
        assert parsed == snapshot

    def test_snapshot_deterministic_ordering(self, provider: DiagnosticProvider) -> None:
        """Repeated calls on the same input should produce identical snapshots."""
        content = """\
# RHF UHF/6-31G(d)

Determinism test

0 1
H 0.0 0.0 0.0
"""
        first = provider.get_diagnostics_snapshot(content)
        second = provider.get_diagnostics_snapshot(content)
        assert first == second

    def test_snapshot_entries_have_required_keys(self, provider: DiagnosticProvider) -> None:
        """Each snapshot entry should have range, severity, source, message."""
        snapshot = provider.get_diagnostics_snapshot("")
        for entry in snapshot:
            assert "range" in entry
            assert "severity" in entry
            assert "source" in entry
            assert "message" in entry
            assert "start" in entry["range"]
            assert "end" in entry["range"]
            assert "line" in entry["range"]["start"]
            assert "character" in entry["range"]["start"]

    def test_snapshot_severity_is_string(self, provider: DiagnosticProvider) -> None:
        """Snapshot severity should be a human-readable string."""
        snapshot = provider.get_diagnostics_snapshot(
            "# B3LYP/6-31G(d)\n\nTest\n\n0 1\nXx 0.0 0.0 0.0\n"
        )
        valid_severities = {"error", "warning", "information", "hint"}
        for entry in snapshot:
            assert entry["severity"] in valid_severities

    def test_snapshot_source_is_gaussian_lsp(self, provider: DiagnosticProvider) -> None:
        """Snapshot source should always be gaussian-lsp."""
        snapshot = provider.get_diagnostics_snapshot("")
        for entry in snapshot:
            assert entry["source"] == "gaussian-lsp"

    def test_snapshot_empty_valid_input(self, provider: DiagnosticProvider) -> None:
        """Valid input should produce an empty snapshot."""
        content = """\
# B3LYP/6-31G(d) opt freq

Water

0 1
O  0.0 0.0 0.0
H  0.0 0.758 0.504
H  0.0 -0.758 0.504
"""
        snapshot = provider.get_diagnostics_snapshot(content)
        errors = [e for e in snapshot if e["severity"] == "error"]
        assert errors == []

    def test_snapshot_contains_error_for_broken_input(self, provider: DiagnosticProvider) -> None:
        """Broken input should produce errors in the snapshot."""
        content = """\
%chk=
%mem=abc
# b3lyp/631g optimize

Broken input

0 2
H 0.0 0.0 0.0
H 0.0 0.0 0.7
"""
        snapshot = provider.get_diagnostics_snapshot(content)
        assert len(snapshot) > 0
        messages = [e["message"] for e in snapshot]
        assert any("%chk" in m for m in messages)
        assert any("%mem" in m for m in messages)


class TestDiagnosticSnapshotCoverage:
    """Extra tests for snapshot edge-case coverage."""

    def test_snapshot_includes_code_when_present(self, provider: DiagnosticProvider) -> None:
        """Snapshot entry should include 'code' when the diagnostic has one."""
        from unittest.mock import patch

        from lsprotocol.types import Diagnostic, DiagnosticSeverity, Position, Range

        fake_diag = Diagnostic(
            range=Range(start=Position(line=0, character=0), end=Position(line=0, character=1)),
            message="test",
            severity=DiagnosticSeverity.Error,
            source="gaussian-lsp",
            code="E001",
        )
        with patch.object(provider, "get_diagnostics", return_value=[fake_diag]):
            snapshot = provider.get_diagnostics_snapshot("anything")
        assert snapshot[0]["code"] == "E001"

    def test_snapshot_handles_none_severity(self, provider: DiagnosticProvider) -> None:
        """Snapshot should treat None severity as 'error'."""
        from unittest.mock import patch

        from lsprotocol.types import Diagnostic, Position, Range

        fake_diag = Diagnostic(
            range=Range(start=Position(line=0, character=0), end=Position(line=0, character=1)),
            message="no severity",
            severity=None,
            source="gaussian-lsp",
        )
        with patch.object(provider, "get_diagnostics", return_value=[fake_diag]):
            snapshot = provider.get_diagnostics_snapshot("anything")
        assert snapshot[0]["severity"] == "error"
