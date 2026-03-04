"""Final tests to achieve 100% code coverage."""

import pytest

from gaussian_lsp.parser.gjf_parser import GaussianJob, GJFParser


class TestFinalCoverage100:
    """Tests for the remaining uncovered code paths."""

    def test_route_section_first_line_empty_in_route_section(self):
        """Test the case where route_section is empty in route section.

        This covers line 478: if not self.job.route_section:
        """
        parser = GJFParser()

        # Create a scenario where we enter route section without setting route_section first
        # This can happen if there's a line starting with # but we bypass the link0 section check
        content = """%chk=test.chk
# B3LYP/6-31G(d)

Test

0 1
H 0.0 0.0 0.0
"""
        job = parser.parse(content)
        assert job.route_section == "# B3LYP/6-31G(d)"

    def test_multiline_route_section_second_line(self):
        """Test multi-line route section where second line is captured."""
        parser = GJFParser()

        content = """# B3LYP/6-31G(d)
# opt freq

Test

0 1
H 0.0 0.0 0.0
"""
        job = parser.parse(content)
        assert "B3LYP" in job.route_section
        assert "opt" in job.route_section or "freq" in job.route_section

    def test_modredundant_loop_completion(self):
        """Test ModRedundant detection loop completion branch.

        This covers the branch where the loop checking for ModRedundant completes
        without finding a ModRedundant line.
        """
        parser = GJFParser()

        # Create content where geometry section ends with empty lines
        # and there's no ModRedundant section
        content = """# B3LYP/6-31G(d)

Test

0 1
H 0.0 0.0 0.0


"""
        job = parser.parse(content)
        assert len(job.atoms) == 1
        assert len(job.modredundant) == 0

    def test_geometry_end_with_empty_lines_then_end(self):
        """Test geometry section ending with empty lines."""
        parser = GJFParser()

        content = """# B3LYP/6-31G(d)

Test

0 1
H 0.0 0.0 0.0


"""
        job = parser.parse(content)
        assert job.atoms == [("H", 0.0, 0.0, 0.0)]

    def test_modredundant_with_single_letter_commands(self):
        """Test ModRedundant section with single letter commands."""
        parser = GJFParser()

        content = """# B3LYP/6-31G(d) opt

Test

0 1
H 0.0 0.0 0.0

B 1 2
"""
        job = parser.parse(content)
        assert len(job.modredundant) == 1
        assert job.modredundant[0] == "B 1 2"

    def test_modredundant_loop_with_no_match(self):
        """Test that ModRedundant detection loop completes without match.

        This specifically tests lines 435-451 branch where we check if next
        non-empty line is ModRedundant but it's not.
        """
        parser = GJFParser()

        # Content where geometry ends and there's content that's NOT ModRedundant
        # but we have empty lines between
        content = """# B3LYP/6-31G(d)

Test

0 1
H 0.0 0.0 0.0


--Link1--
"""
        job = parser.parse(content)
        # Should parse without error and have 1 atom
        assert len(job.atoms) == 1

    def test_geometry_with_empty_lines(self):
        """Test geometry section with empty lines after charge/mult."""
        parser = GJFParser()

        # Content with empty lines after charge/mult
        content = """# B3LYP/6-31G(d)

Test

0 1


"""
        job = parser.parse(content)
        assert len(job.atoms) == 0

    def test_route_section_with_continuation(self):
        """Test route section with continuation lines."""
        parser = GJFParser()

        content = """# B3LYP/6-31G(d)
# opt
# freq

Test

0 1
H 0.0 0.0 0.0
"""
        job = parser.parse(content)
        assert "B3LYP" in job.route_section

    def test_link0_then_route_directly(self):
        """Test going from link0 section to route section directly."""
        parser = GJFParser()

        content = """%mem=1GB
%nproc=4
# B3LYP/6-31G(d)

Test

0 1
H 0.0 0.0 0.0
"""
        job = parser.parse(content)
        assert job.route_section == "# B3LYP/6-31G(d)"
        assert job.link0.get("mem") == "1GB"
        assert job.link0.get("nproc") == "4"


class TestLine478Specifically:
    """Specific tests for line 478 coverage."""

    def test_line_478_route_section_append_path(self, monkeypatch):
        """Test the specific line 478 path where route_section is appended."""
        parser = GJFParser()

        # Create a custom parse scenario
        content = """# HF/STO-3G
# opt

Test

0 1
H 0.0 0.0 0.0
"""

        # This should trigger the line where we append to route_section
        job = parser.parse(content)
        assert "HF" in job.route_section
        assert "opt" in job.route_section

    def test_exact_line_478_execution(self):
        """Directly test line 478 execution path."""
        from gaussian_lsp.parser.gjf_parser import GJFParser

        parser = GJFParser()
        parser.job = GaussianJob()

        # Simulate being in route section with empty route_section
        # This is an artificial scenario to trigger line 478
        lines = ["%mem=1GB", "# HF/STO-3G", "", "Test", "", "0 1", "H 0.0 0.0 0.0"]

        # Manually set up state
        parser.job.route_section = ""

        # Parse normally - the first line starting with # should set route_section
        content = "\n".join(lines)
        job = parser.parse(content)

        # The route section should be set correctly
        assert "HF" in job.route_section


class TestBranch435To451:
    """Specific tests for branch 435->451 coverage."""

    def test_modredundant_loop_completion_branch(self):
        """Test ModRedundant loop completion branch (lines 435-451)."""
        parser = GJFParser()

        # Create content where after geometry, there's an empty line
        # then a non-ModRedundant line, triggering the loop completion
        content = """# B3LYP/6-31G(d)

Test

0 1
H 0.0 0.0 0.0

--Link1--
%chk=next.chk
# HF/STO-3G

Next

0 1
He 0.0 0.0 0.0
"""

        # Only the first job should be parsed
        job = parser.parse(content)
        assert len(job.atoms) == 1
        assert job.atoms[0][0] == "H"

    def test_geometry_end_no_modredundant(self):
        """Test geometry section ending without ModRedundant."""
        parser = GJFParser()

        # Multiple empty lines after geometry - triggers the loop
        content = """# B3LYP/6-31G(d)

Test

0 1
H 0.0 0.0 0.0




"""
        job = parser.parse(content)
        assert len(job.atoms) == 1
        assert len(job.modredundant) == 0

    def test_geometry_with_empty_then_comment(self):
        """Test geometry followed by empty lines then comment."""
        parser = GJFParser()

        content = """# B3LYP/6-31G(d)

Test

0 1
H 0.0 0.0 0.0

! This is a comment
"""
        job = parser.parse(content)
        assert len(job.atoms) == 1


class TestCombinedScenarios:
    """Combined scenarios for edge cases."""

    def test_complex_input_with_all_sections(self):
        """Test complex input with all sections."""
        parser = GJFParser()

        content = """%chk=complex.chk
%mem=2GB
%nproc=8
# B3LYP/6-31G(d,p) opt freq scrf=(smd,solvent=water)

Complex Molecule

0 1
C 0.000000 0.000000 0.000000
H 1.089000 0.000000 0.000000
H -0.544500 0.943096 0.000000
H -0.544500 -0.943096 0.000000

B 1 2
"""
        job = parser.parse(content)
        assert len(job.atoms) == 4
        assert len(job.modredundant) == 1
        assert job.link0.get("chk") == "complex.chk"

    def test_route_without_hash_then_fixed(self):
        """Test input that might trigger route without hash detection."""
        parser = GJFParser()

        # This is a valid input with proper route section
        content = """# PBE/STO-3G opt

Test

0 1
He 0.0 0.0 0.0
"""
        job = parser.parse(content)
        assert "PBE" in job.route_section

    def test_multiple_empty_lines_between_sections(self):
        """Test multiple empty lines between sections."""
        parser = GJFParser()

        content = """# HF/STO-3G



Test Title



0 1


H 0.0 0.0 0.0
"""
        job = parser.parse(content)
        assert job.title == "Test Title"
        assert len(job.atoms) == 1
