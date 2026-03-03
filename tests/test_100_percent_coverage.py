"""Additional tests to achieve 100% coverage - Targeted gaps."""

import pytest
from lsprotocol import types

from gaussian_lsp.parser.gjf_parser import GaussianJob, GJFParser
from gaussian_lsp.server import _analyze_content, _format_gjf, parse_gjf_document


class TestParserLine478Coverage:
    """Test for gjf_parser.py line 478: route_section += ' ' + line."""

    def test_route_section_continuation_with_existing_route(self):
        """Test line 478: route section continues when already set.

        Condition: section == 'route' AND line starts with '#'
        AND self.job.route_section is already set (truthy)
        """
        content = """%chk=test.chk
# B3LYP/6-31G(d)
# opt freq

Test

0 1
H 0.0 0.0 0.0
"""
        parser = GJFParser()
        job = parser.parse(content)
        # The route should include both lines
        assert "# B3LYP/6-31G(d)" in job.route_section
        assert "# opt freq" in job.route_section


class TestParserLine484to489Coverage:
    """Test for gjf_parser.py lines 484->489: continue after charge/mult."""

    def test_charge_mult_match_continues(self):
        """Test lines 484->489: continue after setting charge/mult.

        Condition: section == 'charge_mult' AND pattern matches
        The continue statement should be executed.
        """
        content = """# HF/STO-3G

Test

0 1
H 0.0 0.0 0.0
"""
        parser = GJFParser()
        job = parser.parse(content)
        assert job.charge == 0
        assert job.multiplicity == 1


class TestParserLines435to451Coverage:
    """Test for gjf_parser.py lines 435->451: geometry end without modred."""

    def test_geometry_end_no_modred_branch_coverage(self):
        """Test lines 435->451: geometry section ends, no modred found.

        Condition: section == 'geometry', geometry_started is True,
        line is empty, and the inner loop doesn't find modred.
        The `if not modred_started: section = 'end'` branch.
        """
        content = """# HF/STO-3G

Test

0 1
H 0.0 0.0 0.0

"""
        parser = GJFParser()
        job = parser.parse(content)
        # Should successfully parse with no modredundant
        assert len(job.atoms) == 1
        assert len(job.modredundant) == 0


class TestServerLines266to279Coverage:
    """Test for server.py lines 266-279: route_section exists but no #."""

    def test_route_section_without_hash(self):
        """Test lines 266-279: job.route_section exists but doesn't start with #.

        This requires manually creating a job with route_section set to
        something that doesn't start with '#'.
        """
        # Create a job with route_section that doesn't start with #
        job = GaussianJob(
            route_section="B3LYP/6-31G(d)",  # No # at start
            title="Test",
            charge=0,
            multiplicity=1,
            atoms=[("H", 0.0, 0.0, 0.0)],
        )

        # Manually test the _analyze_content logic for this case
        # We need to create content that parses to this state
        content = """B3LYP/6-31G(d)

Test

0 1
H 0.0 0.0 0.0
"""
        diagnostics = _analyze_content(content)
        # Should have a diagnostic about route section needing #
        # This covers lines 266-279
        assert len(diagnostics) > 0
        messages = [d.message for d in diagnostics]
        # Check that we get the route section error
        assert any("#" in m for m in messages)


class TestParserRouteContinuationEdgeCase:
    """Test edge case for route continuation."""

    def test_multi_line_route_accumulation_exact(self):
        """Test exact condition for line 478.

        First line sets route_section, second line appends to it.
        """
        content = """# B3LYP/6-31G(d)
# opt

Title

0 1
H 0.0 0.0 0.0
"""
        parser = GJFParser()
        job = parser.parse(content)
        # route_section should accumulate both lines
        assert "# B3LYP/6-31G(d)" in job.route_section
        assert "# opt" in job.route_section


class TestChargeMultExactPath:
    """Test exact path through charge/mult section."""

    def test_charge_mult_sets_values_and_continues(self):
        """Test that charge/mult section sets values and continues."""
        content = """# HF/STO-3G

My Title

1 2
C 0.0 0.0 0.0
"""
        parser = GJFParser()
        job = parser.parse(content)
        assert job.charge == 1
        assert job.multiplicity == 2
        assert job.title == "My Title"


class TestGeometryEndsExact:
    """Test exact geometry ending path."""

    def test_geometry_blank_line_no_modred(self):
        """Test geometry ends with blank line, no modred follows."""
        content = """# B3LYP/6-31G(d)

Test

0 1
H 0.0 0.0 0.0


"""
        parser = GJFParser()
        job = parser.parse(content)
        assert len(job.atoms) == 1
        assert job.atoms[0][0] == "H"


class TestServerRouteWithoutHashExact:
    """Test server path for route without hash - exact condition."""

    def test_analyze_content_route_no_hash(self):
        """Test _analyze_content with route that doesn't start with #.

        This should trigger lines 266-279.
        """
        # Content where first non-comment line looks like a route but has no #
        content = """B3LYP/6-31G(d)

Test

0 1
H 0.0 0.0 0.0
"""
        diagnostics = _analyze_content(content)
        # Check that we hit the route without hash diagnostic
        route_diagnostics = [
            d for d in diagnostics if "Route section must start with #" in d.message
        ]
        assert len(route_diagnostics) >= 1
        # Verify the diagnostic is on line 0 (first non-comment line)
        assert route_diagnostics[0].range.start.line == 0


class TestExactCoverageBranches:
    """Tests targeting exact uncovered branches."""

    def test_parser_line_478_exact(self):
        """Test parser line 478: route_section accumulation.

        Condition: in route section, line starts with #, route_section already set.
        """
        content = """# HF/STO-3G
# opt

Title

0 1
H 0.0 0.0 0.0
"""
        parser = GJFParser()
        job = parser.parse(content)
        # Should have accumulated route
        parts = job.route_section.split()
        assert "#" in parts or "#" in job.route_section
        assert "HF/STO-3G" in job.route_section or "opt" in job.route_section

    def test_parser_lines_484_489_exact(self):
        """Test parser lines 484-489: continue after charge/mult.

        The continue statement after setting charge/mult should be hit.
        """
        content = """# B3LYP/6-31G(d)

Test

0 1
H 0.0 0.0 0.0
"""
        parser = GJFParser()
        job = parser.parse(content)
        # After charge/mult match, should continue to geometry
        assert job.charge == 0
        assert job.multiplicity == 1
        assert len(job.atoms) == 1

    def test_server_lines_266_279_exact(self):
        """Test server lines 266-279: route section without hash.

        job.route_section exists but doesn't start with #.
        This requires content that parses incorrectly or a specific edge case.
        """
        # Content that triggers the "route without hash" diagnostic
        content = """B3LYP/6-31G(d)

Test

0 1
H 0.0 0.0 0.0
"""
        diagnostics = _analyze_content(content)
        # Find the diagnostic about route needing hash
        found = False
        for d in diagnostics:
            if "Route section must start with #" in d.message and d.range.start.line == 0:
                found = True
                break
        assert (
            found
        ), f"Expected route without hash diagnostic, got: {[d.message for d in diagnostics]}"
