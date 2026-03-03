"""Final tests to achieve 100% coverage."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from lsprotocol import types

from gaussian_lsp.parser.gjf_parser import GaussianJob, GJFParser
from gaussian_lsp.server import _analyze_content, _format_gjf, diagnostic, formatting, hover, server


class TestFinalCoverageBranches:
    """Test remaining uncovered branches."""

    def test_modred_started_true_branch(self) -> None:
        """Test the branch where modred_started is True (line 435->451)."""
        # This test covers the case where a blank line is encountered in geometry
        # section, and the next line IS a ModRedundant command
        content = """# B3LYP/6-31G(d) opt

Test

0 1
H 0.0 0.0 0.0
H 1.0 0.0 0.0

B 1 2
"""
        parser = GJFParser()
        job = parser.parse(content)
        assert len(job.atoms) == 2
        assert len(job.modredundant) >= 1

    def test_charge_mult_continue_branch(self) -> None:
        """Test the continue in charge_mult section (line 478)."""
        # This covers line 484->489 where after setting charge/mult, we continue
        content = """# B3LYP/6-31G(d)

Test

0 1
H 0.0 0.0 0.0
"""
        parser = GJFParser()
        job = parser.parse(content)
        assert job.charge == 0
        assert job.multiplicity == 1
        assert len(job.atoms) == 1

    def test_title_already_set_branch(self) -> None:
        """Test when title is already set (line 484->489)."""
        # After title is set, subsequent lines in title section should be handled
        content = """# B3LYP/6-31G(d)

First Line
Second Line

0 1
H 0.0 0.0 0.0
"""
        parser = GJFParser()
        job = parser.parse(content)
        # The first line becomes title, second line is also part of title or
        # might start charge_mult section depending on parsing
        assert job.title == "First Line"


class TestServerRouteWithoutHash:
    """Test server diagnostics for route without hash (lines 266-279)."""

    def test_diagnostic_route_without_hash_exact(self) -> None:
        """Test exact branch for route section not starting with #."""
        from gaussian_lsp.server import _analyze_content

        # Content with route section that doesn't start with #
        # This should trigger lines 266-279
        content = """B3LYP/6-31G(d)

Test

0 1
H 0.0 0.0 0.0
"""
        diagnostics = _analyze_content(content)
        # Should have error about route section must start with #
        error_messages = [d.message for d in diagnostics]
        assert any("Route section must start with #" in msg for msg in error_messages)

    def test_diagnostic_route_section_empty_but_present(self) -> None:
        """Test diagnostic when route section exists but is empty string."""
        content = """%chk=test.chk

Test

0 1
H 0.0 0.0 0.0
"""
        diagnostics = _analyze_content(content)
        error_messages = [d.message for d in diagnostics]
        # Should have error about missing or invalid route
        assert any("route" in msg.lower() for msg in error_messages)


class TestEdgeCasesForCoverage:
    """Test various edge cases."""

    def test_parse_empty_geometry_section(self) -> None:
        """Test parsing when geometry section is empty."""
        content = """# B3LYP/6-31G(d)

Test

0 1
"""
        parser = GJFParser()
        job = parser.parse(content)
        assert len(job.atoms) == 0

    def test_validate_returns_false_on_parse_error(self) -> None:
        """Test that validate returns False when parsing fails."""
        parser = GJFParser()
        # Empty content should cause parse error
        is_valid, errors = parser.validate("")
        assert is_valid is False
        assert any("error" in e.lower() or "empty" in e.lower() for e in errors)

    def test_server_diagnostic_with_valid_job(self) -> None:
        """Test server diagnostic with completely valid job."""
        content = """%chk=water.chk
%mem=2GB
%nproc=4

# B3LYP/6-31G(d) opt freq

Water molecule

0 1
O   0.000000    0.000000    0.000000
H   0.757160    0.586260    0.000000
H  -0.757160    0.586260    0.000000
"""
        diagnostics = _analyze_content(content)
        # Should have no errors for valid content
        errors = [d for d in diagnostics if d.severity == types.DiagnosticSeverity.Error]
        assert len(errors) == 0


class TestFormattingEdgeCases:
    """Test formatting edge cases."""

    def test_format_gjf_with_parse_exception(self) -> None:
        """Test format_gjf when parsing raises exception."""
        # Completely invalid content that will cause parse to fail
        result = _format_gjf("")
        # Should return original content when parsing fails
        assert result == ""

    def test_format_valid_job(self) -> None:
        """Test formatting a valid job."""
        content = """# B3LYP/6-31G(d)

Test

0 1
H 0.0 0.0 0.0
"""
        result = _format_gjf(content)
        # Should successfully format
        assert "# B3LYP/6-31G(d)" in result
        assert "H" in result
