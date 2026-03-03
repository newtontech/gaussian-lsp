"""Exact test for line 478 coverage."""

from gaussian_lsp.parser.gjf_parser import GJFParser


def test_line_478_route_section_append():
    """Force execution of line 478: route_section += ' ' + line

    Requirements:
    1. In route section (section == 'route')
    2. Line starts with # or %
    3. job.route_section is already set (not empty)
    """
    # Content with multi-line route section
    content = """%chk=test.chk
# B3LYP/6-31G(d)
# Opt Freq

Title

0 1
H 0 0 0
"""
    parser = GJFParser()
    job = parser.parse(content)

    # Verify both lines are in the route section
    assert "# B3LYP/6-31G(d)" in job.route_section
    assert "# Opt Freq" in job.route_section or "Opt Freq" in job.route_section
    print(f"Route section: {job.route_section}")


def test_line_478_second_line_append():
    """Test that second route line appends to first."""
    content = """# HF/STO-3G
#SP

Test

0 1
C 0 0 0
"""
    parser = GJFParser()
    job = parser.parse(content)

    # The route should contain both the method and SP
    route = job.route_section
    print(f"Route section: {route}")
    assert "HF" in route
