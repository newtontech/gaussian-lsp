"""Final coverage tests to reach 100%."""

import pytest

from gaussian_lsp.parser.gjf_parser import GJFParser


class TestFinal100Coverage:
    """Tests specifically targeting uncovered lines."""

    def test_modredundant_after_empty_line_in_geometry(self):
        """Test ModRedundant detection after empty line in geometry section.

        Covers lines 435-451: geometry section ends with empty line,
        then ModRedundant section follows.
        """
        content = """%chk=test.chk
# B3LYP/6-31G(d) opt

Test

0 1
O 0.0 0.0 0.0
H 1.0 0.0 0.0

B 1 2
"""
        parser = GJFParser()
        job = parser.parse(content)
        assert len(job.modredundant) == 1
        assert job.modredundant[0] == "B 1 2"

    def test_modredundant_single_letter_after_empty_line(self):
        """Test single letter ModRedundant commands after empty line."""
        content = """%chk=test.chk
# B3LYP/6-31G(d) opt

Test

0 1
O 0.0 0.0 0.0

M
"""
        parser = GJFParser()
        job = parser.parse(content)
        assert len(job.modredundant) == 1
        assert job.modredundant[0] == "M"

    def test_route_section_already_set_multiline(self):
        """Test multiline route section when route_section is already set.

        Covers line 478: route_section already exists, append to it.
        This happens when route section continues with lines starting with # or %
        """
        content = """%chk=test.chk
# B3LYP/6-31G(d)
# opt freq

Test

0 1
O 0.0 0.0 0.0
"""
        parser = GJFParser()
        job = parser.parse(content)
        assert "B3LYP/6-31G(d)" in job.route_section
        assert "opt" in job.route_section
        assert "freq" in job.route_section

    def test_route_section_with_percent_continue(self):
        """Test route section continuation with % line."""
        content = """%chk=test.chk
# B3LYP/6-31G(d)
%mem=2GB

Test

0 1
O 0.0 0.0 0.0
"""
        parser = GJFParser()
        job = parser.parse(content)
        assert "B3LYP/6-31G(d)" in job.route_section
        assert "%mem=2GB" in job.route_section

    def test_charge_mult_match_continue(self):
        """Test charge/mult match with continue statement.

        Covers lines 484-489: charge/mult match followed by continue.
        """
        content = """# HF/6-31G

Test

0 1
H 0.0 0.0 0.0
"""
        parser = GJFParser()
        job = parser.parse(content)
        assert job.charge == 0
        assert job.multiplicity == 1
        assert len(job.atoms) == 1

    def test_no_modredundant_after_empty_line(self):
        """Test that section ends correctly when no ModRedundant follows."""
        content = """# HF/6-31G

Test

0 1
H 0.0 0.0 0.0

"""
        parser = GJFParser()
        job = parser.parse(content)
        assert len(job.atoms) == 1
        assert len(job.modredundant) == 0

    def test_geometry_end_with_modred_pattern_false(self):
        """Test geometry section ends when next line doesn't match ModRed."""
        content = """# HF/6-31G

Test

0 1
H 0.0 0.0 0.0

X
"""
        parser = GJFParser()
        job = parser.parse(content)
        # X is a valid dummy atom symbol, not ModRed
        assert len(job.atoms) == 1
