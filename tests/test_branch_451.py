"""Test for branch 435->451 coverage."""
from gaussian_lsp.parser.gjf_parser import GJFParser


def test_geometry_blank_then_comment():
    """Test blank line in geometry followed by comment (not ModRedundant).

    This should trigger branch 435->451:
    1. section == 'geometry' and geometry_started == True
    2. Blank line encountered
    3. Check next non-empty line - it's a comment
    4. Comment is not ModRedundant, so modred_started stays False
    5. Execute: if not modred_started: section = 'end'
    """
    content = """# HF/STO-3G

Test

0 1
H 0.0 0.0 0.0

! This is a comment after blank line
"""
    parser = GJFParser()
    job = parser.parse(content)
    assert len(job.atoms) == 1
    assert job.modredundant == []


def test_geometry_blank_then_route_like():
    """Test blank line followed by route-like line (not ModRed)."""
    content = """# HF/STO-3G

Test

0 1
H 0.0 0.0 0.0

# B3LYP/6-31G
"""
    parser = GJFParser()
    job = parser.parse(content)
    assert len(job.atoms) == 1
