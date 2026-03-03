"""Additional tests to achieve 100% coverage - Final gaps."""

import pytest
from lsprotocol import types

from gaussian_lsp.parser.gjf_parser import GaussianJob, GJFParser
from gaussian_lsp.server import _analyze_content, _format_gjf


class TestFinalCoverageGaps:
    """Test the final missing coverage gaps."""

    # ========== gjf_parser.py Line 435->451 ==========
    def test_modredundant_detection_loop_no_modred(self) -> None:
        """Test that geometry section ends when no ModRedundant follows.

        This covers lines 435->451 (the branch where modred_started remains False).
        """
        content = """# B3LYP/6-31G(d)

Test

0 1
H 0.0 0.0 0.0

"""
        parser = GJFParser()
        job = parser.parse(content)
        assert len(job.atoms) == 1
        assert len(job.modredundant) == 0

    def test_modredundant_detection_loop_empty_rest(self) -> None:
        """Test geometry section ending with empty lines but no ModRedundant.

        This ensures the loop completes without finding ModRedundant.
        """
        content = """# B3LYP/6-31G(d)

Test

0 1
H 0.0 0.0 0.0



"""
        parser = GJFParser()
        job = parser.parse(content)
        assert len(job.atoms) == 1
        assert len(job.modredundant) == 0

    # ========== gjf_parser.py Line 478 ==========
    def test_route_section_already_set(self) -> None:
        """Test route section accumulation when already set.

        This covers line 478 (when route_section is already set but we append).
        """
        content = """# B3LYP/6-31G(d)
# opt freq

Test

0 1
H 0.0 0.0 0.0
"""
        parser = GJFParser()
        job = parser.parse(content)
        assert "# B3LYP/6-31G(d)" in job.route_section
        assert "opt freq" in job.route_section

    # ========== gjf_parser.py Line 484->489 ==========
    def test_charge_mult_section_normal_flow(self) -> None:
        """Test charge/multiplicity section in normal flow.

        This covers lines 484->489 (the continue after setting charge/mult).
        """
        content = """# B3LYP/6-31G(d)

Test Title

1 2
H 0.0 0.0 0.0
"""
        parser = GJFParser()
        job = parser.parse(content)
        assert job.charge == 1
        assert job.multiplicity == 2
        assert job.title == "Test Title"

    # ========== server.py Line 253 ==========
    def test_no_noncomment_lines_found(self) -> None:
        """Test diagnostics when no non-comment lines exist.

        This covers server.py line 253 (the else branch when no lines found).
        """
        content = """! This is a comment
! Another comment
"""
        diagnostics = _analyze_content(content)
        # Should have a diagnostic about missing route section
        assert len(diagnostics) >= 1
        # Check that one diagnostic mentions missing route
        route_errors = [d for d in diagnostics if "route" in d.message.lower()]
        assert len(route_errors) >= 1

    # ========== server.py Lines 266-279 ==========
    def test_route_without_hash_detection(self) -> None:
        """Test detection of route section without hash.

        This covers server.py lines 266-279 (route without hash diagnostic).
        """
        content = """B3LYP/6-31G(d)

Test

0 1
H 0.0 0.0 0.0
"""
        diagnostics = _analyze_content(content)
        # Should have error about route section must start with #
        route_errors = [d for d in diagnostics if "#" in d.message]
        assert len(route_errors) >= 1

    def test_route_without_hash_with_valid_content(self) -> None:
        """Test that route without hash triggers diagnostic on first line."""
        content = """B3LYP/6-31G(d) opt

Test molecule

0 1
H 0.0 0.0 0.0
H 1.0 0.0 0.0
"""
        diagnostics = _analyze_content(content)
        # Find the diagnostic on the first line
        first_line_errors = [d for d in diagnostics if d.range.start.line == 0 and "#" in d.message]
        assert len(first_line_errors) >= 1


class TestEdgeCasesForCoverage:
    """Additional edge cases for complete coverage."""

    def test_format_gjf_invalid_returns_original(self) -> None:
        """Test that _format_gjf returns original content when invalid."""
        content = """! Invalid content without route
"""
        result = _format_gjf(content)
        # When validation fails, should return original
        assert result == content

    def test_geometry_ends_with_non_modred_line(self) -> None:
        """Test that geometry ends correctly when followed by non-ModRed line."""
        content = """# B3LYP/6-31G(d)

Test

0 1
H 0.0 0.0 0.0

Some other text
"""
        parser = GJFParser()
        job = parser.parse(content)
        # Should parse successfully without treating "Some other text" as ModRedundant
        assert len(job.atoms) == 1

    def test_multi_line_route_accumulation(self) -> None:
        """Test multi-line route section accumulation."""
        content = """# B3LYP/6-31G(d)
# opt freq
# scrf=(pcm,solvent=water)

Test

0 1
H 0.0 0.0 0.0
"""
        parser = GJFParser()
        job = parser.parse(content)
        assert "B3LYP" in job.route_section
        assert "opt" in job.route_section
        assert "scrf" in job.route_section


class TestMoreEdgeCases:
    """More edge cases for 100% coverage."""

    def test_modred_after_geometry_with_non_modred(self) -> None:
        """Test geometry ending when next line is not ModRedundant."""
        content = """# B3LYP/6-31G(d)

Test

0 1
H 0.0 0.0 0.0

X 0.0 0.0 0.0
"""
        parser = GJFParser()
        job = parser.parse(content)
        assert len(job.atoms) == 1

    def test_route_section_continuation(self) -> None:
        """Test route section continues with continuation lines."""
        content = """# B3LYP/6-31G(d) opt
# freq

Test

0 1
H 0.0 0.0 0.0
"""
        parser = GJFParser()
        job = parser.parse(content)
        assert "opt" in job.route_section
        assert "freq" in job.route_section

    def test_charge_mult_with_title_continue(self) -> None:
        """Test charge/mult section is properly recognized."""
        content = """# B3LYP/6-31G(d)
My Title Here
0 1
H 0.0 0.0 0.0
"""
        parser = GJFParser()
        job = parser.parse(content)
        assert job.title == "My Title Here"
        assert job.charge == 0
        assert job.multiplicity == 1

    def test_server_diagnostic_no_hash_route(self) -> None:
        """Test server diagnostic for route without hash."""
        # This triggers the route section validation
        content = """B3LYP/6-31G(d)

Test

0 1
H 0.0 0.0 0.0
"""
        diagnostics = _analyze_content(content)
        # Find diagnostics about route without hash
        hash_errors = [d for d in diagnostics if "must start with #" in d.message]
        assert len(hash_errors) >= 1
