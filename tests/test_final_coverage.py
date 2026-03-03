"""Final tests to achieve 100% coverage."""

import pytest

from gaussian_lsp.parser.gjf_parser import GJFParser


class TestFinalCoverageGaps:
    """Test remaining coverage gaps."""

    def test_geometry_ends_without_modred_line_435(self):
        """Test geometry section ends properly when no ModRedundant follows.

        Covers line 435->451: section = "end" when geometry_started and no modred
        """
        content = """# B3LYP/6-31G(d) opt

Test

0 1
H 0.0 0.0 0.0

Some extra content after geometry
"""
        parser = GJFParser()
        job = parser.parse(content)

        assert len(job.atoms) == 1
        assert job.modredundant == []

    def test_route_section_set_in_route_section_line_478(self):
        """Test route section already set but another route line follows.

        Covers line 478: route_section already set, appending to it
        """
        content = """# B3LYP/6-31G(d)
# opt freq

Test

0 1
H 0.0 0.0 0.0
"""
        parser = GJFParser()
        job = parser.parse(content)

        assert "# B3LYP/6-31G(d)" in job.route_section
        assert "# opt freq" in job.route_section

    def test_charge_mult_continue_to_geometry_line_484(self):
        """Test parsing continues from charge/mult to geometry.

        Covers line 484->489: continue after charge_mult match
        """
        content = """# HF/STO-3G

Test

0 1
H 0.0 0.0 0.0
C 1.0 0.0 0.0
"""
        parser = GJFParser()
        job = parser.parse(content)

        assert job.charge == 0
        assert job.multiplicity == 1
        assert len(job.atoms) == 2

    def test_geometry_with_modred_single_letter(self):
        """Test geometry with single letter ModRedundant command."""
        content = """# B3LYP/6-31G(d) opt

Test

0 1
H 0.0 0.0 0.0
H 1.0 0.0 0.0

B
"""
        parser = GJFParser()
        job = parser.parse(content)

        assert len(job.atoms) == 2
        assert "B" in job.modredundant
