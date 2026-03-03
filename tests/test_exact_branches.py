"""Tests to cover exact missing branches."""

import unittest

from gaussian_lsp.parser.gjf_parser import GJFParser
from gaussian_lsp.server import _analyze_content


class TestMissingBranches(unittest.TestCase):
    """Test missing coverage branches."""

    def test_route_section_append_line_478(self):
        """Test line 478: append to existing route_section.

        This tests the branch where route_section is already set
        and another # line is encountered in route section.
        """
        parser = GJFParser()
        # Multi-line route section where second line also starts with #
        content = """# B3LYP/6-31G(d) opt
# freq

Test

0 1
H 0.0 0.0 0.0
"""
        job = parser.parse(content)
        # Verify route_section contains both parts
        self.assertIn("B3LYP", job.route_section)
        self.assertIn("freq", job.route_section)

    def test_geometry_ends_with_empty_line_435_451(self):
        """Test line 435->451: geometry section ends without ModRedundant.

        This tests the branch where geometry_started is True,
        an empty line is encountered, but next non-empty line is NOT ModRedundant.
        """
        parser = GJFParser()
        # Geometry followed by empty line, then non-ModRedundant content
        content = """# HF/STO-3G

Test

0 1
H 0.0 0.0 0.0

Variables
X=1.0
"""
        job = parser.parse(content)
        self.assertEqual(len(job.atoms), 1)
        # section should transition to "end"

    def test_charge_mult_with_atom_following_484_489(self):
        """Test line 484->489: charge/mult match with atom following.

        This tests the branch where after matching charge/mult,
        the continue is executed and atoms are properly parsed.
        """
        parser = GJFParser()
        content = """# HF/STO-3G

Test

0 1
O 0.0 0.0 0.0
H 0.75 0.0 0.0
H -0.75 0.0 0.0
"""
        job = parser.parse(content)
        self.assertEqual(job.charge, 0)
        self.assertEqual(job.multiplicity, 1)
        self.assertEqual(len(job.atoms), 3)

    def test_server_route_without_hash_266_279(self):
        """Test server lines 266-279: route_section exists but doesn't start with #."""
        # Create content where route_section is set but not starting with #
        # This requires a specific parse scenario
        content = """%chk=test.chk
B3LYP/6-31G(d)

Test

0 1
H 0.0 0.0 0.0
"""
        diagnostics = _analyze_content(content)
        # Should have error about route not starting with #
        route_errors = [d for d in diagnostics if "Route section must start with #" in d.message]
        self.assertGreater(len(route_errors), 0)


if __name__ == "__main__":
    unittest.main()
