"""Final tests to achieve exactly 100% coverage for remaining branches."""

import pytest

from gaussian_lsp.parser.gjf_parser import GJFParser


class TestFinalBranches:
    """Cover the last 3 uncovered branches:
    - 435->451: Empty line in geometry, check if next non-empty is ModRed
    - 478: MODRED_PATTERN.match(line) in geometry section
    - 484->489: Single letter ModRed command (M,B,A,D,L,R,S,F,C,K)
    """

    def test_line_435_geometry_blank_with_modred_after(self):
        """Cover branch 435->451: blank line in geometry with ModRed pattern after.

        When there's a blank line in geometry section, the code checks
        if the next non-empty line is a ModRed command. If yes, it continues.
        """
        content = """%chk=test.chk
#p B3LYP/6-31G(d) opt=ModRedundant

test

0 1
C 0.0 0.0 0.0
H 1.0 0.0 0.0

M
1 2
"""
        parser = GJFParser()
        job = parser.parse(content)
        # M should be captured in modredundant
        assert "M" in job.modredundant

    def test_line_478_modred_pattern_in_geometry(self):
        """Cover line 478: MODRED_PATTERN.match(line) in geometry section.

        This happens when a line in geometry section matches the MODRED_PATTERN
        (starts with M,B,A,D,R,L,S,F,C,K followed by whitespace).
        """
        content = """%chk=test.chk
#p B3LYP/6-31G(d) opt=ModRedundant

test

0 1
C 0.0 0.0 0.0
H 1.0 0.0 0.0

B 1 2
"""
        parser = GJFParser()
        job = parser.parse(content)
        # B 1 2 should be captured
        assert any("B" in m for m in job.modredundant)

    def test_line_484_single_letter_modred_k(self):
        """Cover line 484->489: Single letter K command in ModRedundant.

        The K command should trigger the single-letter branch.
        """
        content = """%chk=test.chk
#p B3LYP/6-31G(d) opt

test

0 1
C 0.0 0.0 0.0
H 1.0 0.0 0.0

K
1 2
"""
        parser = GJFParser()
        job = parser.parse(content)
        assert "K" in job.modredundant


class TestEdgeCasesForCoverage:
    """Additional edge cases to ensure complete coverage."""

    def test_geometry_blank_not_modred(self):
        """Test blank line followed by non-ModRed content ends geometry."""
        content = """%chk=test.chk
#p B3LYP/6-31G(d)

test

0 1
C 0.0 0.0 0.0


"""
        parser = GJFParser()
        job = parser.parse(content)
        assert len(job.atoms) == 1

    def test_all_single_letter_modred_commands(self):
        """Test all single letter ModRedundant commands."""
        commands = ["M", "B", "A", "D", "L", "R", "S", "F", "C", "K"]
        for cmd in commands:
            content = f"""%chk=test.chk
#p B3LYP/6-31G(d) opt

test

0 1
C 0.0 0.0 0.0
H 1.0 0.0 0.0

{cmd}
1
"""
            parser = GJFParser()
            job = parser.parse(content)
            assert cmd in job.modredundant, f"Command {cmd} not found in modredundant"
