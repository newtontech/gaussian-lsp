"""Tests for achieving 100% coverage - targeting specific missing lines."""

import pytest

from gaussian_lsp.parser.gjf_parser import GaussianJob, GJFParser
from gaussian_lsp.server import _analyze_content


class TestParserLine435to451:
    """Test coverage for line 435->451: ModRedundant detection loop completion."""

    def test_geometry_blank_loop_completes_no_modred(self):
        """Test that the for loop at line 435 completes without finding ModRedundant."""
        content = """# B3LYP/6-31G(d) opt

Test molecule

0 1
O  0.000000  0.000000  0.000000
H  0.757160  0.586260  0.000000

"""
        parser = GJFParser()
        job = parser.parse(content)
        assert len(job.atoms) == 2


class TestParserLine478:
    """Test coverage for line 478: Route section already set."""

    def test_route_section_continuation(self):
        """Test that route section accumulates multiple lines."""
        content = """# B3LYP/6-31G(d)
# opt freq

Test molecule

0 1
O  0.000000  0.000000  0.000000
"""
        parser = GJFParser()
        job = parser.parse(content)
        assert "B3LYP" in job.route_section
        assert "opt" in job.route_section or "freq" in job.route_section


class TestParserLine484to489:
    """Test coverage for line 484->489: Charge/mult match continue."""

    def test_charge_mult_match_continue_branch(self):
        """Test that charge/mult match triggers continue at line 484->489."""
        content = """# HF/3-21G

Water

0 1
O  0.000  0.000  0.000
H  0.757  0.586  0.000
H -0.757  0.586  0.000
"""
        parser = GJFParser()
        job = parser.parse(content)
        assert job.charge == 0
        assert job.multiplicity == 1
        assert len(job.atoms) == 3


class TestServerLines266to279:
    """Test coverage for server lines 266-279: Route without hash detection."""

    def test_analyze_content_route_without_hash(self):
        """Test diagnostics when route section doesn't start with #."""
        content = """B3LYP/6-31G(d) opt

Test

0 1
H 0 0 0
"""
        diagnostics = _analyze_content(content)
        error_messages = [
            d.message for d in diagnostics if "#" in d.message or "Route" in d.message
        ]
        assert len(error_messages) > 0 or len(diagnostics) > 0


class TestParserLine478Exact:
    """Test specifically for line 478 - route section already set."""

    def test_line_478_exact_coverage(self):
        """Force execution of line 478: job.route_section += ' ' + line.

        This requires:
        1. In route section
        2. Line starts with # or %
        3. job.route_section is already set (truthy)
        """
        content = """# HF/STO-3G
# Opt

Test

0 1
H 0 0 0
"""
        parser = GJFParser()
        job = parser.parse(content)
        # The route should contain both lines
        assert "HF" in job.route_section
        assert "Opt" in job.route_section


class TestServerBranchesExact:
    """Test for specific branch coverage in server.py."""

    def test_server_branch_266_to_282(self):
        """Test branch 266-282: route section without hash."""
        from gaussian_lsp.server import _analyze_content

        content = "B3LYP/6-31G(d) opt\n\nTitle Line\n\n0 1\nH 0.0 0.0 0.0\n"
        diagnostics = _analyze_content(content)
        assert any("#" in d.message for d in diagnostics)
