"""Tests to cover exact branch conditions."""

import pytest

from gaussian_lsp.parser.gjf_parser import GJFParser


class TestExactBranchCoverage:
    """Cover specific uncovered branches."""

    def test_geometry_empty_line_no_modred(self):
        """Cover branch 435->451: empty line in geometry, no ModRed follows.

        This tests when geometry section has an empty line and the next
        non-empty line is NOT a ModRedundant command (section becomes 'end').
        """
        content = """# B3LYP/6-31G(d)

Test

0 1
O 0.0 0.0 0.0
H 0.0 0.0 0.8

X
"""
        parser = GJFParser()
        job = parser.parse(content)
        # After empty line in geometry, if no ModRed detected, section becomes 'end'
        # X is not parsed as atom because section is 'end'
        assert len(job.atoms) == 2
        assert len(job.modredundant) == 0

    def test_route_section_append(self):
        """Cover line 478: route section append when already set.

        This tests the else branch where route_section is already set
        and we append to it.
        """
        content = """# B3LYP/6-31G(d)
# opt freq

Test

0 1
O 0.0 0.0 0.0
"""
        parser = GJFParser()
        job = parser.parse(content)
        assert "# B3LYP/6-31G(d)" in job.route_section
        assert "# opt freq" in job.route_section

    def test_charge_mult_continue(self):
        """Cover lines 484->489: charge/mult match with continue.

        This tests the continue statement after charge/mult match.
        The key is that after matching, we continue to next iteration.
        """
        content = """# B3LYP/6-31G(d)

Test

0 1
O 0.0 0.0 0.0
H 0.0 0.0 0.8
"""
        parser = GJFParser()
        job = parser.parse(content)
        assert job.charge == 0
        assert job.multiplicity == 1
        assert len(job.atoms) == 2

    def test_no_link0_direct_route(self):
        """Test parsing without link0 section."""
        content = """# HF/6-31G

Test

0 1
H 0.0 0.0 0.0
"""
        parser = GJFParser()
        job = parser.parse(content)
        assert job.route_section == "# HF/6-31G"
        assert job.title == "Test"
