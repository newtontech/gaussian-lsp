"""Smart coverage tests - find inputs that trigger uncovered branches."""

import pytest

from gaussian_lsp.parser.gjf_parser import GJFParser


class TestBranch435To451:
    """Branch 435->451: Geometry blank line, no ModRedundant follows.

    The code at line 451 is: if not modred_started: section = "end"
    This happens when:
    1. We're in geometry section and geometry_started is True
    2. We encounter a blank line
    3. We check the next non-empty line
    4. It's NOT a ModRedundant line (so modred_started stays False)
    5. We execute 'if not modred_started: section = "end"'
    """

    def test_geometry_blank_then_end(self):
        """Test geometry with blank line then end of file."""
        content = """# HF/STO-3G

Test

0 1
H 0.0 0.0 0.0
"""
        parser = GJFParser()
        job = parser.parse(content)
        assert len(job.atoms) == 1
        assert job.atoms[0][0] == "H"

    def test_geometry_blank_then_another_blank(self):
        """Test geometry with blank lines."""
        content = """# HF/STO-3G

Test

0 1
H 0.0 0.0 0.0


"""
        parser = GJFParser()
        job = parser.parse(content)
        assert len(job.atoms) == 1

    def test_geometry_blank_then_route_like_line(self):
        """Test geometry blank then a line that looks like route (not ModRed)."""
        content = """# HF/STO-3G

Test

0 1
H 0.0 0.0 0.0

# This looks like a route
"""
        parser = GJFParser()
        job = parser.parse(content)
        assert len(job.atoms) == 1


class TestBranch478:
    """Branch 478: First route line when route_section is empty.

    Line 478: self.job.route_section = line
    This happens when:
    1. We're in route section (section == 'route')
    2. Line starts with # or %
    3. self.job.route_section is falsy/empty

    The route section is entered either:
    - From link0 section when line starts with # (line 466-468)
    - Or we're already in route section
    """

    def test_route_from_link0_first_line(self):
        """Test first route line after link0 sets route_section."""
        content = """%mem=1GB
# B3LYP/6-31G

Title

0 1
H 0.0 0.0 0.0
"""
        parser = GJFParser()
        job = parser.parse(content)
        # This should trigger line 478 (first route line sets route_section)
        assert job.route_section == "# B3LYP/6-31G"

    def test_route_direct_start(self):
        """Test starting directly with route (no link0)."""
        content = """# HF/STO-3G

Title

0 1
H 0.0 0.0 0.0
"""
        parser = GJFParser()
        job = parser.parse(content)
        # This enters route section at line 466-468, then line 478
        assert job.route_section == "# HF/STO-3G"


class TestBranch484To489:
    """Branch 484->489: Skip title assignment when already set.

    Line 484: if not self.job.title:
    The arrow 484->489 means the condition is False (title is set)
    and we jump to line 489 (if section == "charge_mult").

    This would require:
    1. section == "title"
    2. job.title is already set (not falsy)
    3. So we skip lines 485-487 and go to 489

    But looking at the code flow:
    - Once we set title at line 486, we continue (line 487)
    - So we never come back to this if block with title already set
    - Unless there's a way to set title without the continue...

    This might be a dead branch or very hard to trigger.
    """

    def test_potential_title_branch(self):
        """Attempt to trigger the title branch."""
        # This might not be triggerable in normal parsing
        # The branch might be for defensive programming
        pass


class TestCombinedScenarios:
    """Combined test scenarios."""

    def test_complex_file_structure(self):
        """Test complex file with multiple elements."""
        content = """%mem=2GB
%nproc=4
# B3LYP/6-31G(d) Opt Freq

Water Molecule

0 1
O  0.000000  0.000000  0.117300
H  0.000000  0.756950 -0.469200
H  0.000000 -0.756950 -0.469200

"""
        parser = GJFParser()
        job = parser.parse(content)
        assert len(job.atoms) == 3
        assert job.link0["mem"] == "2GB"
        assert "B3LYP" in job.route_section

    def test_no_link0_direct_route(self):
        """Test file starting directly with route."""
        content = """# MP2/cc-pVTZ

Methane

0 1
C  0.000000  0.000000  0.000000
H  0.626700  0.626700  0.626700
"""
        parser = GJFParser()
        job = parser.parse(content)
        assert job.route_section == "# MP2/cc-pVTZ"
        assert len(job.atoms) == 2
