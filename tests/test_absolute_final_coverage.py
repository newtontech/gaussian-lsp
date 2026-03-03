"""Final 100% coverage tests - targeting remaining uncovered lines."""

from unittest.mock import MagicMock, patch

import pytest
from lsprotocol import types

from gaussian_lsp.parser.gjf_parser import GaussianJob, GJFParser
from gaussian_lsp.server import _analyze_content


class TestParserFinalCoverage:
    """Final tests for parser coverage."""

    def test_geometry_blank_line_with_modredundant(self):
        """Test line 435->451: geometry blank line followed by ModRedundant."""
        parser = GJFParser()
        content = """# B3LYP/6-31G(d) opt

Test

0 1
H 0.0 0.0 0.0

B 1 2
"""
        job = parser.parse(content)
        assert len(job.modredundant) >= 1

    def test_geometry_blank_line_with_multiple_blanks_then_modred(self):
        """Test branch 435->451: blank line followed by more blanks then ModRed."""
        parser = GJFParser()
        content = """# B3LYP/6-31G(d)

Test

0 1
H 0.0 0.0 0.0


B 1 2
"""
        job = parser.parse(content)
        assert len(job.atoms) == 1
        assert len(job.modredundant) >= 1

    def test_route_section_continuation(self):
        """Test line 480: route section continuation when already set."""
        parser = GJFParser()
        content = """# B3LYP/6-31G(d)
# opt freq

Test

0 1
H 0.0 0.0 0.0
"""
        job = parser.parse(content)
        assert "# B3LYP/6-31G(d)" in job.route_section
        assert "opt" in job.route_section

    def test_charge_mult_match_and_continue(self):
        """Test lines 491->495: charge/mult match with continue."""
        parser = GJFParser()
        content = """# B3LYP/6-31G(d)

Test Title

0 1
H 0.0 0.0 0.0
"""
        job = parser.parse(content)
        assert job.charge == 0
        assert job.multiplicity == 1


class TestServerFinalCoverage:
    """Final tests for server coverage - targeting lines 266-279."""

    def test_analyze_content_route_without_hash_mocked(self):
        """Test lines 266-279: route section exists but doesn't start with #."""
        content = """B3LYP/6-31G(d)

Test

0 1
H 0.0 0.0 0.0
"""
        mock_job = MagicMock()
        mock_job.route_section = "B3LYP/6-31G(d)"
        mock_job.atoms = [("H", 0.0, 0.0, 0.0)]
        mock_job.link0 = {}
        mock_job.title = "Test"
        mock_job.charge = 0
        mock_job.multiplicity = 1
        mock_job.modredundant = []

        with patch("gaussian_lsp.server.GJFParser") as mock_parser_class:
            mock_parser = MagicMock()
            mock_parser.parse.return_value = mock_job
            mock_parser_class.return_value = mock_parser

            diagnostics = _analyze_content(content)

        route_errors = [d for d in diagnostics if "Route section must start with #" in d.message]
        assert len(route_errors) > 0

    def test_analyze_content_route_without_hash_loop_else(self):
        """Test branch 266->282: for loop completes without finding match.

        This covers the case where all lines are skipped (comments/link0 only),
        so the for loop exits naturally (the 'else' case).
        """
        content = """%chk=test.chk
! Comment line
"""
        mock_job = MagicMock()
        mock_job.route_section = "B3LYP/6-31G(d)"  # No # prefix!
        mock_job.atoms = []
        mock_job.link0 = {"chk": "test.chk"}
        mock_job.title = ""
        mock_job.charge = 0
        mock_job.multiplicity = 1
        mock_job.modredundant = []

        with patch("gaussian_lsp.server.GJFParser") as mock_parser_class:
            mock_parser = MagicMock()
            mock_parser.parse.return_value = mock_job
            mock_parser_class.return_value = mock_parser

            diagnostics = _analyze_content(content)

        # Should still work even if no matching line found
        assert isinstance(diagnostics, list)

    def test_analyze_content_route_without_hash_some_skipped_lines(self):
        """Test branch 267->266: some lines are skipped in the loop.

        This covers the case where some lines don't match the condition
        (empty lines, comments, link0), so the loop continues.
        """
        content = """%chk=test.chk

! Comment
B3LYP/6-31G(d)
"""
        mock_job = MagicMock()
        mock_job.route_section = "B3LYP/6-31G(d)"  # No # prefix!
        mock_job.atoms = []
        mock_job.link0 = {"chk": "test.chk"}
        mock_job.title = ""
        mock_job.charge = 0
        mock_job.multiplicity = 1
        mock_job.modredundant = []

        with patch("gaussian_lsp.server.GJFParser") as mock_parser_class:
            mock_parser = MagicMock()
            mock_parser.parse.return_value = mock_job
            mock_parser_class.return_value = mock_parser

            diagnostics = _analyze_content(content)

        # Should find the B3LYP line
        route_errors = [d for d in diagnostics if "Route section must start with #" in d.message]
        assert len(route_errors) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
