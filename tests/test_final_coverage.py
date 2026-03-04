"""Tests to achieve 100% coverage."""

import pytest

from gaussian_lsp.parser.gjf_parser import GJFParser, parse_gjf


class TestFinalCoverage:
    """Tests to cover remaining uncovered lines."""

    def test_line_478_route_section_append(self):
        """Test line 478: route_section += " " + line."""
        # Multi-line route section - lines starting with # or % continue
        content = """%chk=test.chk
# B3LYP/6-31G(d)
# opt freq

Test

0 1
O 0.0 0.0 0.0
"""
        parser = GJFParser()
        job = parser.parse(content)
        assert "B3LYP" in job.route_section
        assert "opt freq" in job.route_section

    def test_line_478_with_continuation(self):
        """Test route section continuation over multiple lines with # prefix."""
        content = """%chk=test.chk
# B3LYP/6-31G(d)
# opt
# freq

Test

0 1
O 0.0 0.0 0.0
"""
        parser = GJFParser()
        job = parser.parse(content)
        assert "# B3LYP/6-31G(d)" in job.route_section
        assert "opt" in job.route_section
        assert "freq" in job.route_section

    def test_line_484_489_charge_mult_continue(self):
        """Test line 484->489: charge_mult continue branch."""
        # After setting charge/mult, it should continue to next line
        content = """# B3LYP/6-31G(d)

Test

0 1
O 0.0 0.0 0.0
"""
        parser = GJFParser()
        job = parser.parse(content)
        assert job.charge == 0
        assert job.multiplicity == 1
        assert len(job.atoms) == 1

    def test_line_435_451_modredundant_loop_not_triggered(self):
        """Test that ModRedundant loop completion branch is covered."""
        # Geometry ends without ModRedundant - triggers the branch where modred_started stays False
        content = """# B3LYP/6-31G(d) opt

Test

0 1
O 0.0 0.0 0.0
H 1.0 0.0 0.0

"""
        parser = GJFParser()
        job = parser.parse(content)
        assert len(job.atoms) == 2
        assert len(job.modredundant) == 0

    def test_line_435_451_geometry_end_branch(self):
        """Test line 435->451: geometry section end detection."""
        # Empty line after geometry without ModRedundant
        content = """# B3LYP/6-31G(d)

Test

0 1
O 0.0 0.0 0.0

"""
        parser = GJFParser()
        job = parser.parse(content)
        assert len(job.atoms) == 1

    def test_exact_line_478_scenario(self):
        """Test exact scenario for line 478 with # continuation."""
        content = """%mem=2GB
# B3LYP/6-31G(d)
# opt
# freq

Water

0 1
O 0.0 0.0 0.0
"""
        parser = GJFParser()
        job = parser.parse(content)
        assert "B3LYP" in job.route_section
        assert "opt" in job.route_section
        assert "freq" in job.route_section

    def test_charge_mult_with_immediate_geometry(self):
        """Test charge/mult followed immediately by geometry."""
        content = """# HF/STO-3G

Test Title

0 1
H 0.0 0.0 0.0
"""
        parser = GJFParser()
        job = parser.parse(content)
        assert job.charge == 0
        assert job.multiplicity == 1
        assert job.atoms[0][0] == "H"

    def test_geometry_end_with_blank_line(self):
        """Test geometry section ending with blank line."""
        content = """# HF/STO-3G

Title

0 1
H 0.0 0.0 0.0

"""
        parser = GJFParser()
        job = parser.parse(content)
        assert len(job.atoms) == 1
