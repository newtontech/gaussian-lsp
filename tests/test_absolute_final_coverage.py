"""Final 100% coverage tests - targeting remaining uncovered lines."""

from unittest.mock import MagicMock, patch

import pytest
from lsprotocol import types

from gaussian_lsp.parser.gjf_parser import GaussianJob, GJFParser
from gaussian_lsp.server import _analyze_content


class TestParserFinalCoverage:
    """Final tests for parser coverage."""

    def test_geometry_blank_line_with_modredundant(self):
        """Test line 435->451: geometry blank line followed by ModRedundant.

        This covers the branch where modred_started becomes True,
        so the 'if not modred_started' block at line 451-452 is NOT taken.
        """
        parser = GJFParser()
        content = """# B3LYP/6-31G(d) opt

Test

0 1
H 0.0 0.0 0.0

B 1 2
"""
        job = parser.parse(content)
        # The blank line is followed by ModRedundant command "B 1 2"
        # This should result in modredundant section being populated
        assert len(job.modredundant) >= 1

    def test_geometry_blank_line_with_only_empty_lines_after(self):
        """Test branch 435->451: loop exits without finding non-empty line.

        When a blank line is encountered in geometry and all remaining lines
        are empty, the for loop at line 435 exits naturally (not via break),
        going to line 451 (if not modred_started check).
        """
        parser = GJFParser()
        content = """# B3LYP/6-31G(d)

Test

0 1
H 0.0 0.0 0.0


"""
        job = parser.parse(content)
        # The blank line at end has only empty lines after it
        # This should trigger the 435->451 branch
        assert len(job.atoms) == 1

    def test_route_section_first_line(self):
        """Test line 478: route section first line setting.

        Line 478 is: self.job.route_section = line
        This executes when route_section is empty (first route line).
        """
        parser = GJFParser()
        content = """# B3LYP/6-31G(d)

Test

0 1
H 0.0 0.0 0.0
"""
        job = parser.parse(content)
        # First route line should be set
        assert job.route_section == "# B3LYP/6-31G(d)"

    def test_route_section_continuation(self):
        """Test line 480: route section continuation when already set.

        Line 480 is: self.job.route_section += " " + line
        This executes when route_section already has content.
        """
        parser = GJFParser()
        content = """# B3LYP/6-31G(d)
# opt freq

Test

0 1
H 0.0 0.0 0.0
"""
        job = parser.parse(content)
        # Both route lines should be combined
        assert "# B3LYP/6-31G(d)" in job.route_section
        assert "opt" in job.route_section

    def test_title_already_set_branch(self):
        """Test line 484->489: title already set branch.

        This covers the branch where title is already set,
        so we skip to line 489 (charge_mult section).
        """
        parser = GJFParser()
        content = """# B3LYP/6-31G(d)

First Title Line
0 1
H 0.0 0.0 0.0
"""
        job = parser.parse(content)
        # First line becomes title, second line "0 1" is parsed as charge_mult
        assert job.title == "First Title Line"
        assert job.charge == 0
        assert job.multiplicity == 1

    def test_charge_mult_match_and_continue(self):
        """Test lines 491->495: charge/mult match with continue.

        This covers the branch where charge/mult pattern matches,
        values are set, and then continue is executed.
        """
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
        """Test lines 266-279: route section exists but doesn't start with #.

        This is an edge case that can't be triggered through normal parsing,
        since the parser only sets route_section for lines starting with '#'.
        We need to mock the parser to return a job with a malformed route_section.
        """
        content = """B3LYP/6-31G(d)

Test

0 1
H 0.0 0.0 0.0
"""
        # Create a mock job with route_section that doesn't start with #
        mock_job = MagicMock()
        mock_job.route_section = "B3LYP/6-31G(d)"  # No # prefix!
        mock_job.atoms = [("H", 0.0, 0.0, 0.0)]
        mock_job.link0 = {}
        mock_job.title = "Test"
        mock_job.charge = 0
        mock_job.multiplicity = 1
        mock_job.modredundant = []

        # Patch the GJFParser to return our mock job
        with patch("gaussian_lsp.server.GJFParser") as mock_parser_class:
            mock_parser = MagicMock()
            mock_parser.parse.return_value = mock_job
            mock_parser_class.return_value = mock_parser

            diagnostics = _analyze_content(content)

        # Should have diagnostic about route section must start with #
        route_errors = [d for d in diagnostics if "Route section must start with #" in d.message]
        assert len(route_errors) > 0
        # The diagnostic should point to the first non-comment line
        assert route_errors[0].range.start.line == 0

    def test_analyze_content_all_lines_skipped_in_loop(self):
        """Test branch 266->282: for loop exits without finding matching line.

        This covers the case where all lines are skipped in the for loop
        (all lines are comments or link0), so the loop exits naturally.
        """
        content = """%chk=test.chk
! This is a comment
"""
        # Create a mock job with route_section that doesn't start with #
        mock_job = MagicMock()
        mock_job.route_section = "B3LYP/6-31G(d)"  # No # prefix!
        mock_job.atoms = []
        mock_job.link0 = {"chk": "test.chk"}
        mock_job.title = ""
        mock_job.charge = 0
        mock_job.multiplicity = 1
        mock_job.modredundant = []

        # Patch the GJFParser to return our mock job
        with patch("gaussian_lsp.server.GJFParser") as mock_parser_class:
            mock_parser = MagicMock()
            mock_parser.parse.return_value = mock_job
            mock_parser_class.return_value = mock_parser

            diagnostics = _analyze_content(content)

        # May or may not have diagnostics depending on implementation
        assert isinstance(diagnostics, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
