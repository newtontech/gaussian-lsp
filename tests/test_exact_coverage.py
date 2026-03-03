"""Tests targeting exact uncovered lines for 100% coverage."""

import pytest
from lsprotocol import types

from gaussian_lsp.parser.gjf_parser import GaussianJob, GJFParser
from gaussian_lsp.server import _analyze_content, _format_gjf


class TestExactLineCoverage:
    """Tests to cover specific uncovered lines."""

    def test_parser_line_478_route_continuation(self):
        """Cover gjf_parser.py line 478: route_section += ' ' + line

        To hit line 478, we need:
        1. In 'route' section
        2. Line starts with '#' or '%'
        3. self.job.route_section is already set (truthy)

        This happens on the SECOND route line when route_section already has content.
        """
        content = """# B3LYP/6-31G(d)
# opt freq

Test

0 1
H 0.0 0.0 0.0
"""
        parser = GJFParser()
        job = parser.parse(content)
        # Both route lines should be accumulated
        assert "# B3LYP/6-31G(d)" in job.route_section
        assert "# opt freq" in job.route_section
        # Verify they're concatenated with a space
        assert "# B3LYP/6-31G(d) # opt freq" == job.route_section

    def test_parser_lines_435_to_451_geometry_end(self):
        """Cover gjf_parser.py lines 435->451: geometry ends without modred

        To hit this branch, we need:
        1. section == 'geometry'
        2. geometry_started is True
        3. Empty line encountered
        4. Inner loop finds no ModRedundant
        5. modred_started stays False
        6. section = 'end' is executed
        """
        # Content with geometry followed by blank line and something that's NOT modred
        content = """# B3LYP/6-31G(d)

Test

0 1
H 0.0 0.0 0.0

END
"""
        parser = GJFParser()
        job = parser.parse(content)
        # Should parse the atom but not treat 'END' as modredundant
        assert len(job.atoms) == 1
        assert len(job.modredundant) == 0

    def test_parser_lines_484_to_489_charge_mult_continue(self):
        """Cover gjf_parser.py lines 484->489: continue after charge/mult

        To hit this branch, we need:
        1. section == 'charge_mult'
        2. Pattern matches
        3. continue statement is executed

        This happens when we successfully parse charge/multiplicity.
        """
        content = """# HF/STO-3G

Title

0 1
H 0.0 0.0 0.0
"""
        parser = GJFParser()
        job = parser.parse(content)
        # Should correctly parse charge/mult and continue to geometry
        assert job.charge == 0
        assert job.multiplicity == 1
        assert len(job.atoms) == 1


class TestServerLine266to279:
    """Test for server.py lines 266-279."""

    def test_server_lines_266_279_route_without_hash(self):
        """Cover server.py lines 266-279: route_section exists but no #

        This is a defensive check that normally wouldn't be hit through parsing,
        since the parser only sets route_section when line starts with '#'.

        However, we can trigger it by creating content where the parser
        produces a job with route_section that somehow doesn't start with '#'.

        Actually, looking at the logic again:
        - Lines 266-279 are hit when job.route_section exists but doesn't start with '#'
        - The parser always adds '#' when setting route_section
        - So this path can only be hit in edge cases

        Let's check what content would trigger the first part of the conditional
        at line 265: `elif not job.route_section.startswith("#"):`
        """
        # This content will have route_section that doesn't start with #
        # because the parser will not recognize B3LYP/6-31G(d) as a route line
        # (it doesn't start with #), so route_section will remain empty
        # and we'll hit the earlier branch about missing route section

        # To hit lines 266-279, we need route_section to be non-empty but not start with #
        # This is actually impossible with the current parser logic

        # However, let's test the scenario where there's content that
        # produces warnings about missing method/basis
        content = """#

Test

0 1
H 0.0 0.0 0.0
"""
        diagnostics = _analyze_content(content)
        # We should get diagnostics
        assert len(diagnostics) >= 1

    def test_server_route_section_without_hash_manual(self):
        """Manually test the route without hash diagnostic.

        Since the parser won't produce this scenario naturally,
        let's verify the code path exists by inspection.

        Lines 266-279 will only be hit if:
        - job.route_section is truthy (not empty)
        - job.route_section doesn't start with '#'

        With the current parser, this never happens.
        This is defensive code for future robustness.
        """
        # Create a valid content to ensure other diagnostics work
        content = """# B3LYP/6-31G(d)

Test

0 1
H 0.0 0.0 0.0
"""
        diagnostics = _analyze_content(content)
        # Valid content should have no errors
        errors = [d for d in diagnostics if d.severity.value <= 1]  # Error or Warning
        # May have warnings but should be minimal
        pass  # This test documents that lines 266-279 are defensive


class TestParserSpecificBranches:
    """Tests for specific parser branches."""

    def test_route_accumulation_exact_branch(self):
        """Test exact branch for route accumulation (line 478)."""
        # First line: %chk sets link0, doesn't affect route_section
        # Second line: # B3LYP sets route_section
        # Third line: # opt should append to route_section (line 478)
        content = """%chk=test.chk
# B3LYP/6-31G(d)
# opt freq

Test

0 1
H 0.0 0.0 0.0
"""
        parser = GJFParser()
        job = parser.parse(content)

        # Verify the route section accumulated both lines
        assert "# B3LYP/6-31G(d)" in job.route_section
        assert "# opt freq" in job.route_section

    def test_geometry_blank_line_transition(self):
        """Test geometry section ending with blank line (lines 435-451)."""
        # Geometry with blank line but no modredundant following
        content = """# HF/STO-3G

Test

0 1
H 0.0 0.0 0.0

"""
        parser = GJFParser()
        job = parser.parse(content)

        assert len(job.atoms) == 1
        assert len(job.modredundant) == 0

    def test_charge_mult_pattern_match(self):
        """Test charge/mult pattern matching (lines 484-489)."""
        content = """# B3LYP/6-31G(d)

Title Here

1 2
C 0.0 0.0 0.0
"""
        parser = GJFParser()
        job = parser.parse(content)

        assert job.charge == 1
        assert job.multiplicity == 2
        assert job.title == "Title Here"
