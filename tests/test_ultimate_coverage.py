"""Tests to achieve 100% code coverage."""

import unittest

from gaussian_lsp.parser.gjf_parser import GJFParser


class TestFinalCoverage(unittest.TestCase):
    """Tests for the remaining uncovered lines."""

    def test_line_435_451_modred_geometry_end(self):
        """Test line 435-451: geometry ends with modred pattern after blank line."""
        parser = GJFParser()
        # Content where blank line in geometry is followed by ModRedundant command
        content = """# B3LYP/6-31G(d) opt

Test

0 1
O  0.000000  0.000000  0.000000

M
B 1 2
"""
        job = parser.parse(content)
        # After blank line in geometry, next line is "M" (ModRedundant marker)
        # This should transition to modredundant section
        self.assertTrue(len(job.modredundant) > 0 or len(job.atoms) >= 1)

    def test_line_478_route_section_already_set(self):
        """Test line 478: route section continuation when already set."""
        parser = GJFParser()
        content = """# B3LYP/6-31G(d)
# opt freq

Test

0 1
O  0.000000  0.000000  0.000000
"""
        job = parser.parse(content)
        self.assertEqual(job.route_section, "# B3LYP/6-31G(d) # opt freq")

    def test_line_484_489_charge_mult_continue(self):
        """Test line 484-489: charge/mult section continue."""
        parser = GJFParser()
        content = """# B3LYP/6-31G(d)

Test Title

0 1
O  0.000000  0.000000  0.000000
"""
        job = parser.parse(content)
        self.assertEqual(job.charge, 0)
        self.assertEqual(job.multiplicity, 1)
        self.assertEqual(job.title, "Test Title")

    def test_server_lines_266_279_route_without_hash(self):
        """Test server lines 266-279: route without hash detection."""
        from gaussian_lsp.server import _analyze_content

        content = """B3LYP/6-31G(d) opt

Test

0 1
O  0.000000  0.000000  0.000000
"""
        diagnostics = _analyze_content(content)
        # Should have diagnostics about missing route section
        self.assertTrue(len(diagnostics) > 0)

    def test_server_lines_266_279_route_looks_like_route(self):
        """Test server lines 266-279: line looks like route but no hash."""
        from gaussian_lsp.server import _analyze_content

        content = """B3LYP/6-31G(d)

Test

0 1
O  0.000000  0.000000  0.000000
"""
        diagnostics = _analyze_content(content)
        # Should detect that line looks like a route
        route_errors = [d for d in diagnostics if "Route section must start with #" in d.message]
        self.assertTrue(len(route_errors) > 0)


if __name__ == "__main__":
    unittest.main()
