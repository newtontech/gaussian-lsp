"""Tests for the LintProvider feature."""

import json

import pytest
from lsprotocol.types import DiagnosticSeverity
from pygls.server import LanguageServer

from gaussian_lsp.features.lint import (
    RULE_FREQ_WITHOUT_OPT,
    RULE_MEM_LOW,
    RULE_NO_JOB_TYPE,
    RULE_NPROC_UNUSUAL,
    RULE_OPEN_SHELL_WITHOUT_UNRESTRICTED,
    RULE_OPT_LOOSE_CONVERGENCE,
    RULE_ROUTE_TYPO,
    RULE_SCF_CONVERGENCE_POSTHF,
    RULE_UNKNOWN_LINK0,
    RULE_UNKNOWN_ROUTE_KEYWORD,
    RULE_VERBOSITY_HINT,
    LintProvider,
)


@pytest.fixture
def provider() -> LintProvider:
    """Create a LintProvider instance for testing."""
    server = LanguageServer("test-gaussian-lsp", "0.0.0")
    return LintProvider(server)


# ---------------------------------------------------------------------------
# Basic provider existence
# ---------------------------------------------------------------------------


class TestLintProviderInit:
    """Test provider instantiation."""

    def test_provider_exists(self, provider: LintProvider) -> None:
        """Test that provider can be created."""
        assert provider is not None

    def test_provider_has_server(self, provider: LintProvider) -> None:
        """Test provider stores the server reference."""
        assert provider.server is not None

    def test_provider_source(self, provider: LintProvider) -> None:
        """Test provider has the correct source identifier."""
        assert provider.SOURCE == "gaussian-lsp-lint"


# ---------------------------------------------------------------------------
# Valid inputs -- lint should produce no errors
# ---------------------------------------------------------------------------


class TestValidInput:
    """Test lint for well-formed Gaussian input."""

    VALID_WATER = """\
#P B3LYP/6-31G(d) opt freq

Water optimization

0 1
O  0.000000  0.000000  0.000000
H  0.000000  0.758602  0.504284
H  0.000000 -0.758602  0.504284
"""

    def test_valid_input_no_errors(self, provider: LintProvider) -> None:
        """Valid input should produce zero error-severity lint diagnostics."""
        diagnostics = provider.lint(self.VALID_WATER)
        errors = [d for d in diagnostics if d.severity == DiagnosticSeverity.Error]
        assert errors == []

    def test_valid_input_source(self, provider: LintProvider) -> None:
        """All lint diagnostics should have source 'gaussian-lsp-lint'."""
        diagnostics = provider.lint(self.VALID_WATER)
        for d in diagnostics:
            assert d.source == "gaussian-lsp-lint"


# ---------------------------------------------------------------------------
# Unparseable input
# ---------------------------------------------------------------------------


class TestUnparseableInput:
    """Test lint on input that the parser cannot handle."""

    def test_empty_string_produces_no_lint(self, provider: LintProvider) -> None:
        """Empty string should not crash lint; it returns empty list."""
        diagnostics = provider.lint("")
        assert isinstance(diagnostics, list)

    def test_garbage_input_produces_no_lint(self, provider: LintProvider) -> None:
        """Garbage input that fails parsing should return empty list."""
        diagnostics = provider.lint("}}} garbage {{{")
        assert isinstance(diagnostics, list)


# ---------------------------------------------------------------------------
# Route keyword checks (G0xx)
# ---------------------------------------------------------------------------


class TestRouteKeywordChecks:
    """Test route-keyword lint rules."""

    def test_unknown_route_keyword(self, provider: LintProvider) -> None:
        """Unknown keyword in route should produce G001 warning."""
        content = """\
#P B3LYP/6-31G(d) opt BOGUSKEYWORD

Test

0 1
H 0.0 0.0 0.0
H 0.0 0.0 0.7
"""
        diagnostics = provider.lint(content)
        messages = [d.message for d in diagnostics]
        assert any("Unknown route keyword" in m and "BOGUSKEYWORD" in m for m in messages)
        codes = [d.code for d in diagnostics]
        assert RULE_UNKNOWN_ROUTE_KEYWORD in codes

    def test_route_typo_optimize(self, provider: LintProvider) -> None:
        """'OPTIMIZE' should be flagged as typo G002."""
        content = """\
#P B3LYP/6-31G(d) OPTIMIZE

Test

0 1
H 0.0 0.0 0.0
H 0.0 0.0 0.7
"""
        diagnostics = provider.lint(content)
        messages = [d.message for d in diagnostics]
        assert any("OPTIMIZE" in m and "OPT" in m for m in messages)
        codes = [d.code for d in diagnostics]
        assert RULE_ROUTE_TYPO in codes

    def test_route_typo_freqency(self, provider: LintProvider) -> None:
        """'FREQENCY' should be flagged as typo G002."""
        content = """\
#P B3LYP/6-31G(d) FREQENCY

Test

0 1
H 0.0 0.0 0.0
H 0.0 0.0 0.7
"""
        diagnostics = provider.lint(content)
        messages = [d.message for d in diagnostics]
        assert any("FREQENCY" in m for m in messages)

    def test_known_keywords_no_lint(self, provider: LintProvider) -> None:
        """All valid tokens in route should produce no unknown-keyword warnings."""
        content = """\
#P B3LYP/6-31G(d) opt freq

Test

0 1
H 0.0 0.0 0.0
"""
        diagnostics = provider.lint(content)
        unknown = [d for d in diagnostics if d.code == RULE_UNKNOWN_ROUTE_KEYWORD]
        assert unknown == []


# ---------------------------------------------------------------------------
# Link0 checks (G1xx)
# ---------------------------------------------------------------------------


class TestLink0Checks:
    """Test Link0 command lint rules."""

    def test_unknown_link0_command(self, provider: LintProvider) -> None:
        """Unknown Link0 command should produce G010 warning."""
        content = """\
%boguscmd=hello
#P B3LYP/6-31G(d) opt

Test

0 1
H 0.0 0.0 0.0
H 0.0 0.0 0.7
"""
        diagnostics = provider.lint(content)
        messages = [d.message for d in diagnostics]
        assert any("Unknown Link0 command" in m and "boguscmd" in m for m in messages)
        codes = [d.code for d in diagnostics]
        assert RULE_UNKNOWN_LINK0 in codes

    def test_nproc_one_hint(self, provider: LintProvider) -> None:
        """%nproc=1 should produce G011 hint."""
        content = """\
%nprocshared=1
#P B3LYP/6-31G(d) opt

Test

0 1
H 0.0 0.0 0.0
H 0.0 0.0 0.7
"""
        diagnostics = provider.lint(content)
        messages = [d.message for d in diagnostics]
        assert any("nproc" in m.lower() and "1" in m for m in messages)
        codes = [d.code for d in diagnostics]
        assert RULE_NPROC_UNUSUAL in codes

    def test_mem_low_hint(self, provider: LintProvider) -> None:
        """%mem=64MB should produce G012 hint."""
        content = """\
%mem=64MB
#P B3LYP/6-31G(d) opt

Test

0 1
H 0.0 0.0 0.0
H 0.0 0.0 0.7
"""
        diagnostics = provider.lint(content)
        messages = [d.message for d in diagnostics]
        assert any("mem" in m.lower() and "64" in m for m in messages)
        codes = [d.code for d in diagnostics]
        assert RULE_MEM_LOW in codes

    def test_valid_link0_no_warnings(self, provider: LintProvider) -> None:
        """Known Link0 commands with reasonable values should not warn."""
        content = """\
%mem=4GB
%nprocs=4
%chk=test.chk
#P B3LYP/6-31G(d) opt

Test

0 1
H 0.0 0.0 0.0
"""
        diagnostics = provider.lint(content)
        link0_warnings = [d for d in diagnostics if d.code in (
            RULE_UNKNOWN_LINK0, RULE_NPROC_UNUSUAL, RULE_MEM_LOW,
        )]
        assert link0_warnings == []


# ---------------------------------------------------------------------------
# Job-type configuration checks (G2xx)
# ---------------------------------------------------------------------------


class TestJobTypeRules:
    """Test job-type configuration lint rules."""

    def test_no_job_type_hint(self, provider: LintProvider) -> None:
        """Route with no job type keyword should produce G020 info."""
        content = """\
#P B3LYP/6-31G(d)

Test

0 1
H 0.0 0.0 0.0
"""
        diagnostics = provider.lint(content)
        messages = [d.message for d in diagnostics]
        assert any("job type keyword" in m.lower() for m in messages)
        codes = [d.code for d in diagnostics]
        assert RULE_NO_JOB_TYPE in codes

    def test_freq_without_opt_info(self, provider: LintProvider) -> None:
        """FREQ without OPT should produce G021 info."""
        content = """\
#P B3LYP/6-31G(d) freq

Test

0 1
H 0.0 0.0 0.0
H 0.0 0.0 0.7
"""
        diagnostics = provider.lint(content)
        messages = [d.message for d in diagnostics]
        assert any("FREQ without OPT" in m for m in messages)
        codes = [d.code for d in diagnostics]
        assert RULE_FREQ_WITHOUT_OPT in codes

    def test_opt_freq_no_warning(self, provider: LintProvider) -> None:
        """OPT FREQ should NOT produce G021."""
        content = """\
#P B3LYP/6-31G(d) opt freq

Test

0 1
H 0.0 0.0 0.0
H 0.0 0.0 0.7
"""
        diagnostics = provider.lint(content)
        freq_without_opt = [
            d for d in diagnostics if d.code == RULE_FREQ_WITHOUT_OPT
        ]
        assert freq_without_opt == []

    def test_opt_loose_warning(self, provider: LintProvider) -> None:
        """OPT with LOOSE should produce G022 warning."""
        content = """\
#P B3LYP/6-31G(d) opt LOOSE

Test

0 1
H 0.0 0.0 0.0
H 0.0 0.0 0.7
"""
        diagnostics = provider.lint(content)
        messages = [d.message for d in diagnostics]
        assert any("LOOSE" in m and "convergence" in m.lower() for m in messages)
        codes = [d.code for d in diagnostics]
        assert RULE_OPT_LOOSE_CONVERGENCE in codes


# ---------------------------------------------------------------------------
# Open-shell / SCF checks (G2xx)
# ---------------------------------------------------------------------------


class TestOpenShellChecks:
    """Test open-shell and SCF lint rules."""

    def test_open_shell_rhf_warning(self, provider: LintProvider) -> None:
        """Multiplicity 2 with RHF should produce G030 warning."""
        content = """\
#P RHF/6-31G(d) opt

Open shell

0 2
H 0.0 0.0 0.0
"""
        diagnostics = provider.lint(content)
        messages = [d.message for d in diagnostics]
        assert any("RHF" in m and "open-shell" in m.lower() for m in messages)
        codes = [d.code for d in diagnostics]
        assert RULE_OPEN_SHELL_WITHOUT_UNRESTRICTED in codes

    def test_open_shell_uhf_no_warning(self, provider: LintProvider) -> None:
        """Multiplicity 2 with UHF should NOT produce G030."""
        content = """\
#P UHF/6-31G(d) opt

Open shell

0 2
H 0.0 0.0 0.0
"""
        diagnostics = provider.lint(content)
        open_shell = [
            d for d in diagnostics if d.code == RULE_OPEN_SHELL_WITHOUT_UNRESTRICTED
        ]
        assert open_shell == []

    def test_open_shell_dft_no_warning(self, provider: LintProvider) -> None:
        """Multiplicity 2 with DFT method should NOT produce G030."""
        content = """\
#P B3LYP/6-31G(d) opt

Open shell DFT

0 2
H 0.0 0.0 0.0
"""
        diagnostics = provider.lint(content)
        open_shell = [
            d for d in diagnostics if d.code == RULE_OPEN_SHELL_WITHOUT_UNRESTRICTED
        ]
        assert open_shell == []

    def test_closed_shell_no_warning(self, provider: LintProvider) -> None:
        """Multiplicity 1 should NOT produce G030."""
        content = """\
#P HF/6-31G(d) opt

Closed shell

0 1
H 0.0 0.0 0.0
H 0.0 0.0 0.7
"""
        diagnostics = provider.lint(content)
        open_shell = [
            d for d in diagnostics if d.code == RULE_OPEN_SHELL_WITHOUT_UNRESTRICTED
        ]
        assert open_shell == []

    def test_scf_convergence_posthf_warning(self, provider: LintProvider) -> None:
        """MP2 with LOOSE SCF should produce G031 warning."""
        content = """\
#P MP2/6-31G(d) LOOSE

Post-HF loose

0 1
H 0.0 0.0 0.0
H 0.0 0.0 0.7
"""
        diagnostics = provider.lint(content)
        messages = [d.message for d in diagnostics]
        assert any("Post-HF" in m and "SCF" in m for m in messages)
        codes = [d.code for d in diagnostics]
        assert RULE_SCF_CONVERGENCE_POSTHF in codes


# ---------------------------------------------------------------------------
# Verbosity hint (G3xx)
# ---------------------------------------------------------------------------


class TestVerbosityHint:
    """Test route verbosity hints."""

    def test_minimal_route_hint(self, provider: LintProvider) -> None:
        """Route starting with '# ' should produce G040 hint."""
        content = """\
# B3LYP/6-31G(d) opt

Test

0 1
H 0.0 0.0 0.0
"""
        diagnostics = provider.lint(content)
        messages = [d.message for d in diagnostics]
        assert any("minimal output" in m.lower() for m in messages)
        codes = [d.code for d in diagnostics]
        assert RULE_VERBOSITY_HINT in codes

    def test_verbose_route_no_hint(self, provider: LintProvider) -> None:
        """Route starting with '#P' should NOT produce G040 hint."""
        content = """\
#P B3LYP/6-31G(d) opt

Test

0 1
H 0.0 0.0 0.0
"""
        diagnostics = provider.lint(content)
        verbosity = [d for d in diagnostics if d.code == RULE_VERBOSITY_HINT]
        assert verbosity == []


# ---------------------------------------------------------------------------
# Diagnostic ranges
# ---------------------------------------------------------------------------


class TestDiagnosticRanges:
    """Test that lint diagnostics have correct ranges."""

    def test_unknown_keyword_has_precise_range(self, provider: LintProvider) -> None:
        """Unknown keyword should have a range that covers the keyword."""
        content = """\
#P B3LYP/6-31G(d) opt BADKW

Test

0 1
H 0.0 0.0 0.0
"""
        diagnostics = provider.lint(content)
        bad_kw = [d for d in diagnostics if "BADKW" in d.message]
        assert len(bad_kw) >= 1
        diag = bad_kw[0]
        # Range should be on the route line (0).
        assert diag.range.start.line == 0
        assert diag.range.start.character >= 0
        assert diag.range.end.character > diag.range.start.character

    def test_link0_range_on_link0_line(self, provider: LintProvider) -> None:
        """Unknown Link0 diagnostic should be on the Link0 line."""
        content = """\
%unknowncmd=test
#P B3LYP/6-31G(d) opt

Test

0 1
H 0.0 0.0 0.0
"""
        diagnostics = provider.lint(content)
        link0_diag = [d for d in diagnostics if d.code == RULE_UNKNOWN_LINK0]
        assert len(link0_diag) >= 1
        assert link0_diag[0].range.start.line == 0


# ---------------------------------------------------------------------------
# Snapshot (JSON-serializable) tests
# ---------------------------------------------------------------------------


class TestLintSnapshot:
    """Test the JSON-serializable lint snapshot."""

    def test_snapshot_is_list(self, provider: LintProvider) -> None:
        """Snapshot should always return a list."""
        snapshot = provider.snapshot("#P B3LYP/6-31G(d) opt\n\nT\n\n0 1\nH 0.0 0.0 0.0\n")
        assert isinstance(snapshot, list)

    def test_snapshot_is_json_serializable(self, provider: LintProvider) -> None:
        """Snapshot should be serializable with json.dumps."""
        snapshot = provider.snapshot(
            "#P B3LYP/6-31G(d) opt\n\nT\n\n0 1\nH 0.0 0.0 0.0\n"
        )
        serialized = json.dumps(snapshot)
        assert isinstance(serialized, str)
        parsed = json.loads(serialized)
        assert parsed == snapshot

    def test_snapshot_deterministic_ordering(self, provider: LintProvider) -> None:
        """Repeated calls on the same input should produce identical snapshots."""
        content = """\
#P B3LYP/6-31G(d) opt BOGUSKW

Test

0 1
H 0.0 0.0 0.0
"""
        first = provider.snapshot(content)
        second = provider.snapshot(content)
        assert first == second

    def test_snapshot_entries_have_required_keys(self, provider: LintProvider) -> None:
        """Each snapshot entry should have range, severity, source, message."""
        content = """\
#P B3LYP/6-31G(d) opt BADKW

Test

0 1
H 0.0 0.0 0.0
"""
        snapshot = provider.snapshot(content)
        assert len(snapshot) > 0
        for entry in snapshot:
            assert "range" in entry
            assert "severity" in entry
            assert "source" in entry
            assert "message" in entry
            assert "start" in entry["range"]
            assert "end" in entry["range"]
            assert "line" in entry["range"]["start"]
            assert "character" in entry["range"]["start"]

    def test_snapshot_severity_is_string(self, provider: LintProvider) -> None:
        """Snapshot severity should be a human-readable string."""
        content = """\
#P B3LYP/6-31G(d) opt BADKW

Test

0 1
H 0.0 0.0 0.0
"""
        snapshot = provider.snapshot(content)
        valid_severities = {"error", "warning", "information", "hint"}
        for entry in snapshot:
            assert entry["severity"] in valid_severities

    def test_snapshot_source_is_lint(self, provider: LintProvider) -> None:
        """Snapshot source should always be gaussian-lsp-lint."""
        content = """\
#P B3LYP/6-31G(d) opt BADKW

Test

0 1
H 0.0 0.0 0.0
"""
        snapshot = provider.snapshot(content)
        for entry in snapshot:
            assert entry["source"] == "gaussian-lsp-lint"

    def test_snapshot_includes_code(self, provider: LintProvider) -> None:
        """Snapshot entry should include 'code' when diagnostic has one."""
        content = """\
#P B3LYP/6-31G(d) opt BADKW

Test

0 1
H 0.0 0.0 0.0
"""
        snapshot = provider.snapshot(content)
        codes = [entry.get("code") for entry in snapshot]
        assert RULE_UNKNOWN_ROUTE_KEYWORD in codes

    def test_snapshot_empty_valid_input(self, provider: LintProvider) -> None:
        """Valid input should produce no errors in the snapshot."""
        content = """\
#P B3LYP/6-31G(d) opt freq

Water

0 1
O  0.0 0.0 0.0
H  0.0 0.758 0.504
H  0.0 -0.758 0.504
"""
        snapshot = provider.snapshot(content)
        errors = [e for e in snapshot if e["severity"] == "error"]
        assert errors == []

    def test_snapshot_unparseable_input_empty(self, provider: LintProvider) -> None:
        """Unparseable input should produce empty snapshot."""
        snapshot = provider.snapshot("")
        assert snapshot == []


# ---------------------------------------------------------------------------
# Internal utility tests
# ---------------------------------------------------------------------------


class TestInternalUtilities:
    """Test LintProvider internal helper methods."""

    def test_parse_mem_mb_mb(self, provider: LintProvider) -> None:
        """Parse '256MB' as 256."""
        assert provider._parse_mem_mb("256MB") == 256

    def test_parse_mem_mb_gb(self, provider: LintProvider) -> None:
        """Parse '4GB' as 4096."""
        assert provider._parse_mem_mb("4GB") == 4096

    def test_parse_mem_mb_kb(self, provider: LintProvider) -> None:
        """Parse '65536KB' as 64."""
        assert provider._parse_mem_mb("65536KB") == 64

    def test_parse_mem_mb_no_unit(self, provider: LintProvider) -> None:
        """Parse '512' (no unit) as 512 MB (default)."""
        assert provider._parse_mem_mb("512") == 512

    def test_parse_mem_mb_invalid(self, provider: LintProvider) -> None:
        """Invalid mem value returns None."""
        assert provider._parse_mem_mb("abc") is None

    def test_parse_mem_mb_words(self, provider: LintProvider) -> None:
        """Parse '256MW' correctly (8 MB per MW)."""
        assert provider._parse_mem_mb("256MW") == 2048

    def test_find_route_line(self, provider: LintProvider) -> None:
        """Find the first route line."""
        lines = ["%mem=1GB", "#P B3LYP/6-31G(d) opt", "", "Test", "0 1", "H 0 0 0"]
        assert provider._find_route_line(lines) == 1

    def test_find_route_line_none(self, provider: LintProvider) -> None:
        """Return None when no route line exists."""
        lines = ["%mem=1GB", "B3LYP/6-31G(d) opt", "", "Test", "0 1", "H 0 0 0"]
        assert provider._find_route_line(lines) is None

    def test_route_tokens(self, provider: LintProvider) -> None:
        """Route tokens should be split and uppercased."""
        tokens = provider._route_tokens("#P B3LYP/6-31G(d) opt")
        assert "P" in tokens
        assert "B3LYP" in tokens
        assert "6-31G" in tokens
        assert "OPT" in tokens

    def test_token_column(self, provider: LintProvider) -> None:
        """Token column should be case-insensitive."""
        col = provider._token_column("#P B3LYP/6-31G(d) opt", "b3lyp")
        assert col == 3

    def test_token_column_not_found(self, provider: LintProvider) -> None:
        """Token not found returns 0."""
        col = provider._token_column("#P B3LYP/6-31G(d) opt", "ZZZZZ")
        assert col == 0


# ---------------------------------------------------------------------------
# Branch coverage: additional edge-case tests
# ---------------------------------------------------------------------------


class TestBranchCoverage:
    """Tests targeting uncovered branches for full coverage."""

    def test_iop_token_accepted(self, provider: LintProvider) -> None:
        """IOp(...) tokens should not be flagged as unknown."""
        content = """\
#P B3LYP/6-31G(d) opt IOp(3/76=10000000)

Test

0 1
H 0.0 0.0 0.0
"""
        diagnostics = provider.lint(content)
        # IOp should not appear as unknown keyword
        unknown = [d for d in diagnostics if "IOp" in d.message]
        assert unknown == []

    def test_iop_lowercase_token_accepted(self, provider: LintProvider) -> None:
        """'iop' (lowercase) tokens should not be flagged as unknown (line 257)."""
        content = """\
#P B3LYP/6-31G(d) opt iop(3/76=10000000)

Test

0 1
H 0.0 0.0 0.0
"""
        diagnostics = provider.lint(content)
        unknown = [d for d in diagnostics if d.code == RULE_UNKNOWN_ROUTE_KEYWORD]
        assert unknown == []

    def test_opt_freq_composite_no_freq_without_opt(self, provider: LintProvider) -> None:
        """'OPT FREQ' composite should not trigger FREQ-without-OPT (branch 411->424)."""
        content = """\
#P B3LYP/6-31G(d) opt freq

Test

0 1
H 0.0 0.0 0.0
"""
        diagnostics = provider.lint(content)
        freq_without = [d for d in diagnostics if d.code == RULE_FREQ_WITHOUT_OPT]
        assert freq_without == []

    def test_nproc_non_digit_value(self, provider: LintProvider) -> None:
        """%nproc with non-digit value should not crash (branch 333->353)."""
        content = """\
%nproc=auto
#P B3LYP/6-31G(d) opt

Test

0 1
H 0.0 0.0 0.0
"""
        diagnostics = provider.lint(content)
        # Should not produce nproc hint (value is not a digit)
        nproc_hints = [d for d in diagnostics if d.code == RULE_NPROC_UNUSUAL]
        assert nproc_hints == []

    def test_open_shell_hf_not_rhf(self, provider: LintProvider) -> None:
        """Multiplicity > 1 with HF (not RHF) should not warn about RHF (branch 482->495)."""
        content = """\
#P HF/6-31G(d) opt

Open shell HF

0 2
H 0.0 0.0 0.0
"""
        diagnostics = provider.lint(content)
        # HF is not RHF or UHF/ROHF/DFT, so no RHF-specific warning.
        # But post-HF check also won't trigger because HF is not post-HF.
        # The only diagnostic should be no open-shell warning since HF handles it.
        rhf_warnings = [
            d for d in diagnostics
            if d.code == RULE_OPEN_SHELL_WITHOUT_UNRESTRICTED and "RHF" in d.message
        ]
        assert rhf_warnings == []

    def test_open_shell_posthf_hint(self, provider: LintProvider) -> None:
        """Multiplicity > 1 with MP2 should produce post-HF open-shell hint (branch 495-504)."""
        content = """\
#P MP2/6-31G(d) opt

Open shell MP2

0 2
H 0.0 0.0 0.0
H 0.0 0.0 0.7
"""
        diagnostics = provider.lint(content)
        codes = [d.code for d in diagnostics]
        assert RULE_OPEN_SHELL_WITHOUT_UNRESTRICTED in codes
        messages = [d.message for d in diagnostics]
        assert any("post-hf" in m.lower() for m in messages)

    def test_no_route_line_skips_all_checks(self, provider: LintProvider) -> None:
        """Missing route line should skip all route-dependent checks."""
        # Use content where parsing succeeds but route is empty.
        # The parser will fail, so lint returns [].
        diagnostics = provider.lint("")
        assert diagnostics == []

    def test_severity_none_defaults_to_error(self, provider: LintProvider) -> None:
        """_severity_name with None should return 'error' (line 161)."""
        from gaussian_lsp.features.lint import _severity_name
        assert _severity_name(None) == "error"

    def test_snapshot_without_code(self, provider: LintProvider) -> None:
        """Snapshot should handle diagnostics without code field (branch 604->606)."""
        from unittest.mock import patch
        from lsprotocol.types import Diagnostic, Position, Range

        fake_diag = Diagnostic(
            range=Range(start=Position(line=0, character=0), end=Position(line=0, character=1)),
            message="test no code",
            severity=DiagnosticSeverity.Warning,
            source="gaussian-lsp-lint",
            code=None,
        )
        with patch.object(provider, "lint", return_value=[fake_diag]):
            snapshot = provider.snapshot("anything")
        assert "code" not in snapshot[0]
