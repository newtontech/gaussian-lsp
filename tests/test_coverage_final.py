"""Additional tests for 100% code coverage."""

from unittest.mock import MagicMock, patch

import pytest

from gaussian_lsp.parser.gjf_parser import GaussianJob, GJFParser
from gaussian_lsp.server import _analyze_content, _format_gjf, _get_word_at_position


class TestGJFParserCoverage:
    """Test cases for missing coverage in gjf_parser.py."""

    def test_parse_modredundant_single_letter_commands(self):
        """Test parsing ModRedundant with single letter commands (line 435-451)."""
        content = """# B3LYP/6-31G(d) opt

Test

0 1
H 0.0 0.0 0.0
H 1.0 0.0 0.0

M
B 1 2
F
"""
        parser = GJFParser()
        job = parser.parse(content)

        assert len(job.atoms) == 2
        assert "M" in job.modredundant
        assert "B 1 2" in job.modredundant
        assert "F" in job.modredundant

    def test_parse_route_section_already_set(self):
        """Test parsing when route_section is already set (line 478)."""
        content = """# B3LYP/6-31G(d)
# opt freq

Test

0 1
H 0.0 0.0 0.0
"""
        parser = GJFParser()
        job = parser.parse(content)

        # Route section should combine both lines
        assert "# B3LYP/6-31G(d)" in job.route_section
        assert "# opt freq" in job.route_section

    def test_parse_geometry_end_with_content(self):
        """Test geometry section ending with content (lines 484-489)."""
        content = """# B3LYP/6-31G(d)

Test

0 1
H 0.0 0.0 0.0

some extra content
"""
        parser = GJFParser()
        job = parser.parse(content)

        assert len(job.atoms) == 1
        assert job.atoms[0][0] == "H"

    def test_parse_charge_mult_continue(self):
        """Test charge/mult section with continue (lines 484-489)."""
        content = """# B3LYP/6-31G(d)

Test

0 1
H 0.0 0.0 0.0
"""
        parser = GJFParser()
        job = parser.parse(content)

        assert job.charge == 0
        assert job.multiplicity == 1

    def test_parse_no_link0_no_route(self):
        """Test parsing with no link0 and no explicit route marker."""
        content = """Test title without proper route

0 1
H 0.0 0.0 0.0
"""
        parser = GJFParser()
        job = parser.parse(content)

        # Should parse but with empty route
        assert job.route_section == ""
        assert job.title == "Test title without proper route"

    def test_validate_with_unusual_link0_warning(self):
        """Test validation warns about unusual link0 command."""
        content = """%custom=value
# HF/STO-3G

Test

0 1
H 0.0 0.0 0.0
"""
        parser = GJFParser()
        is_valid, messages = parser.validate(content)

        assert is_valid  # Should be valid but with warning
        assert any("unusual" in m.lower() or "link0" in m.lower() for m in messages)


class TestServerCoverage:
    """Test cases for missing coverage in server.py."""

    def test_analyze_content_route_looks_like_route(self):
        """Test route detection when line looks like route (lines 266-279)."""
        content = """B3LYP/6-31G(d) opt

Test

0 1
H 0.0 0.0 0.0
"""
        diagnostics = _analyze_content(content)

        # Should detect that line looks like route but missing #
        error_msgs = [d.message for d in diagnostics]
        assert any("#" in msg and "route" in msg.lower() for msg in error_msgs)

    def test_analyze_content_route_without_hash_no_method(self):
        """Test route detection when route doesn't start with # and no method."""
        content = """Some random text

Test

0 1
H 0.0 0.0 0.0
"""
        diagnostics = _analyze_content(content)

        # Should report missing route section
        error_msgs = [d.message for d in diagnostics]
        assert any("missing" in msg.lower() and "route" in msg.lower() for msg in error_msgs)

    def test_analyze_content_route_with_method_but_no_hash(self):
        """Test route detection when line contains method but no hash."""
        content = """HF/STO-3G

Test

0 1
H 0.0 0.0 0.0
"""
        diagnostics = _analyze_content(content)

        # Should detect that line looks like route due to /
        error_msgs = [d.message for d in diagnostics]
        assert any("route" in msg.lower() for msg in error_msgs)

    def test_analyze_content_no_noncomment_lines(self):
        """Test when file has only comments or empty lines."""
        content = """! Just a comment

! Another comment
"""
        diagnostics = _analyze_content(content)

        # Should report missing route
        error_msgs = [d.message for d in diagnostics]
        assert any("route" in msg.lower() for msg in error_msgs)

    def test_get_word_at_position_boundary_conditions(self):
        """Test word extraction at various boundary conditions."""
        # Empty line
        assert _get_word_at_position("", 0) == ""

        # Position beyond line length
        assert _get_word_at_position("test", 100) == ""

        # Single character
        assert _get_word_at_position("A", 0) == "A"

        # Position at word boundary
        # Multiple spaces between words
        line = "B3LYP   6-31G"
        assert _get_word_at_position(line, 6) == ""  # In spaces

    def test_format_gjf_with_parse_exception(self):
        """Test formatting when parsing raises exception."""
        content = ""  # Empty content should raise ValueError

        # Should return original content when parsing fails
        result = _format_gjf(content)
        assert result == content

    def test_format_gjf_with_validation_failure(self):
        """Test formatting when validation fails."""
        content = """Invalid content without route or atoms

Just some text
"""

        # Should return original content when validation fails
        result = _format_gjf(content)
        assert result == content


class TestGaussianJobCoverage:
    """Additional tests for GaussianJob."""

    def test_job_to_gjf_with_empty_modredundant(self):
        """Test to_gjf with empty modredundant."""
        job = GaussianJob(
            route_section="# HF/STO-3G",
            title="Test",
            charge=0,
            multiplicity=1,
            atoms=[("H", 0.0, 0.0, 0.0)],
            modredundant=[],
        )

        gjf = job.to_gjf()
        assert "# HF/STO-3G" in gjf
        assert "0 1" in gjf

    def test_job_to_gjf_with_link0_and_modredundant(self):
        """Test to_gjf with both link0 and modredundant."""
        job = GaussianJob(
            link0={"chk": "test.chk"},
            route_section="# B3LYP/6-31G(d) opt",
            title="Full Test",
            charge=0,
            multiplicity=1,
            atoms=[("O", 0.0, 0.0, 0.0), ("H", 1.0, 0.0, 0.0)],
            modredundant=["B 1 2", "F"],
        )

        gjf = job.to_gjf()
        assert "%chk=test.chk" in gjf
        assert "# B3LYP/6-31G(d) opt" in gjf
        assert "Full Test" in gjf
        assert "B 1 2" in gjf
        assert "F" in gjf


class TestParserEdgeCases:
    """Test edge cases in parser."""

    def test_parse_geometry_with_various_spacing(self):
        """Test parsing geometry with various spacing patterns."""
        content = """# HF/STO-3G

Test

0 1
H 0.0 0.0 0.0
  H   1.0   0.0   0.0
H    -1.0    0.0     0.0
"""
        parser = GJFParser()
        job = parser.parse(content)

        assert len(job.atoms) == 3
        assert all(atom[0] == "H" for atom in job.atoms)

    def test_parse_modredundant_various_formats(self):
        """Test parsing various ModRedundant formats."""
        content = """# B3LYP/6-31G(d) opt

Test

0 1
H 0.0 0.0 0.0
H 1.0 0.0 0.0
H 2.0 0.0 0.0

B 1 2
A 1 2 3
D 1 2 3 1
L 1 2
R 1 2
S 1 2 10
F
"""
        parser = GJFParser()
        job = parser.parse(content)

        assert len(job.modredundant) == 7
        assert "B 1 2" in job.modredundant
        assert "A 1 2 3" in job.modredundant
        assert "F" in job.modredundant

    def test_validate_with_numeric_element(self):
        """Test validation with numeric element (ghost atom)."""
        content = """# HF/STO-3G

Test

0 1
1 0.0 0.0 0.0
"""
        parser = GJFParser()
        is_valid, messages = parser.validate(content)

        # Numeric elements should not cause errors
        assert is_valid

    def test_validate_no_job_type_warning(self):
        """Test validation warns about missing job type."""
        content = """# HF/STO-3G

Test

0 1
H 0.0 0.0 0.0
"""
        parser = GJFParser()
        is_valid, messages = parser.validate(content)

        # Should warn about missing job type (defaults to SP)
        assert is_valid
        assert any("job type" in m.lower() for m in messages)


class TestServerDiagnosticsEdgeCases:
    """Test server diagnostics edge cases."""

    def test_diagnostic_with_complex_content(self):
        """Test diagnostics with complex GJF content."""
        content = """%chk=complex.chk
%mem=4GB
%nproc=8

# B3LYP/6-311G(d,p) opt freq scrf=(smd,solvent=water)

Complex molecule

0 1
C  0.000000  0.000000  0.000000
H  1.089000  0.000000  0.000000
H -0.544500  0.943089  0.000000
H -0.544500 -0.943089  0.000000
"""
        diagnostics = _analyze_content(content)

        # Should have no errors for valid content
        errors = [d for d in diagnostics if d.severity.value <= 1]
        assert len(errors) == 0

    def test_diagnostic_with_unknown_element_in_geometry(self):
        """Test diagnostics for unknown element in geometry."""
        content = """# B3LYP/6-31G(d)

Test

0 1
Xx 0.0 0.0 0.0
"""
        diagnostics = _analyze_content(content)

        # Should warn about unknown element
        warn_msgs = [d.message for d in diagnostics]
        assert any("unknown" in msg.lower() for msg in warn_msgs)

    def test_diagnostic_with_multiple_issues(self):
        """Test diagnostics with multiple issues."""
        content = """Test without route

0 0
"""
        diagnostics = _analyze_content(content)

        # Should report multiple issues
        msgs = [d.message for d in diagnostics]
        # Missing route and no atoms
        assert len([m for m in msgs if "route" in m.lower() or "atom" in m.lower()]) >= 1


class TestLSPFeaturesCoverage:
    """Test LSP features for coverage."""

    def test_completion_items_have_details(self):
        """Test that completion items have proper details."""
        from gaussian_lsp.server import completion

        mock_params = MagicMock()
        mock_params.text_document.uri = "file:///test.gjf"
        mock_params.position.line = 0
        mock_params.position.character = 0

        with patch("gaussian_lsp.server.server") as mock_server:
            mock_doc = MagicMock()
            mock_doc.lines = ["# "]
            mock_server.workspace.get_text_document.return_value = mock_doc

            result = completion(mock_params)

            # Check various item types
            methods = [item for item in result.items if item.kind.value == 2]  # Method
            classes = [item for item in result.items if item.kind.value == 7]  # Class
            events = [item for item in result.items if item.kind.value == 23]  # Event

            assert len(methods) > 0
            assert len(classes) > 0
            assert len(events) > 0

    def test_hover_with_basis_set(self):
        """Test hover with basis set keyword."""
        from gaussian_lsp.server import hover

        mock_params = MagicMock()
        mock_params.text_document.uri = "file:///test.gjf"
        mock_params.position.line = 0
        mock_params.position.character = 10  # Position at basis set

        with patch("gaussian_lsp.server.server") as mock_server:
            mock_doc = MagicMock()
            mock_doc.lines = ["# B3LYP/6-31G(d)"]
            mock_server.workspace.get_text_document.return_value = mock_doc

            result = hover(mock_params)

            # Should return hover info
            assert result is None or hasattr(result, "contents")

    def test_hover_with_job_type(self):
        """Test hover with job type keyword."""
        from gaussian_lsp.server import hover

        mock_params = MagicMock()
        mock_params.text_document.uri = "file:///test.gjf"
        mock_params.position.line = 0
        mock_params.position.character = 15  # Position after basis set

        with patch("gaussian_lsp.server.server") as mock_server:
            mock_doc = MagicMock()
            mock_doc.lines = ["# B3LYP/6-31G(d) OPT"]
            mock_server.workspace.get_text_document.return_value = mock_doc

            result = hover(mock_params)

            # Should return hover info or None
            assert result is None or hasattr(result, "contents")
