"""Additional tests to achieve 100% coverage."""

from unittest.mock import MagicMock, PropertyMock, patch

import pytest
from lsprotocol import types

from gaussian_lsp.parser.gjf_parser import VALID_ELEMENTS, GaussianJob, GJFParser
from gaussian_lsp.server import (
    _analyze_content,
    _format_gjf,
    _get_word_at_position,
    completion,
    hover,
    server,
)


class TestParserCoverage:
    """Test parser edge cases for full coverage."""

    def test_parse_modredundant_with_bond(self):
        """Test parsing ModRedundant with B command."""
        content = """# B3LYP/6-31G(d) opt

Test

0 1
H 0.0 0.0 0.0
H 1.0 0.0 0.0

B 1 2 1.0
F
"""
        parser = GJFParser()
        job = parser.parse(content)
        assert len(job.modredundant) >= 1

    def test_parse_modredundant_with_angle(self):
        """Test parsing ModRedundant with A command."""
        content = """# B3LYP/6-31G(d) opt

Test

0 1
H 0.0 0.0 0.0
H 1.0 0.0 0.0
H 0.0 1.0 0.0

A 1 2 3
F
"""
        parser = GJFParser()
        job = parser.parse(content)
        assert len(job.modredundant) >= 1

    def test_parse_modredundant_with_dihedral(self):
        """Test parsing ModRedundant with D command."""
        content = """# B3LYP/6-31G(d) opt

Test

0 1
H 0.0 0.0 0.0
H 1.0 0.0 0.0
H 0.0 1.0 0.0
H 0.0 0.0 1.0

D 1 2 3 4 180.0
F
"""
        parser = GJFParser()
        job = parser.parse(content)
        assert len(job.modredundant) >= 1

    def test_parse_modredundant_stepwise(self):
        """Test parsing multiple ModRedundant lines."""
        content = """# B3LYP/6-31G(d) opt

Test

0 1
H 0.0 0.0 0.0
H 1.0 0.0 0.0

B 1 2
S 10 0.1
F
"""
        parser = GJFParser()
        job = parser.parse(content)
        assert len(job.modredundant) >= 2

    def test_parse_with_l(self):
        """Test parsing ModRedundant with L (linear bend)."""
        content = """# B3LYP/6-31G(d) opt

Test

0 1
H 0.0 0.0 0.0
H 1.0 0.0 0.0
O 2.0 0.0 0.0

L 1 2 3
F
"""
        parser = GJFParser()
        job = parser.parse(content)
        assert len(job.modredundant) >= 1

    def test_parse_multi_line_route_continuation(self):
        """Test parsing route that continues on multiple lines."""
        content = """%chk=test.chk
# B3LYP/6-31G(d)
# opt freq
# scrf=iefpcm

Test

0 1
H 0.0 0.0 0.0
"""
        parser = GJFParser()
        job = parser.parse(content)
        assert "# B3LYP/6-31G(d)" in job.route_section
        assert "# opt freq" in job.route_section
        assert "# scrf=iefpcm" in job.route_section

    def test_validate_known_element_lowercase(self):
        """Test validation recognizes lowercase elements."""
        content = """# HF/STO-3G

Test

0 1
h 0.0 0.0 0.0
c 1.0 0.0 0.0
o 0.0 1.0 0.0
"""
        parser = GJFParser()
        is_valid, errors = parser.validate(content)
        # Should be valid (lowercase elements are normalized)
        assert is_valid

    def test_validate_with_numeric_atom_type(self):
        """Test validation handles numeric atom types (ghost atoms)."""
        content = """# HF/STO-3G

Test

0 1
1 0.0 0.0 0.0
"""
        parser = GJFParser()
        is_valid, errors = parser.validate(content)
        # Numeric atom types should be allowed
        assert is_valid

    def test_validate_suspicious_charge_mult(self):
        """Test validation allows various charge/mult combinations."""
        content = """# UHF/6-31G(d)

Test

1 2
H 0.0 0.0 0.0
"""
        parser = GJFParser()
        is_valid, errors = parser.validate(content)
        assert is_valid

    def test_validate_job_types(self):
        """Test validation with various job types."""
        for job_type in ["IRC", "SCAN", "TS", "RAMAN", "POLAR"]:
            content = f"""# B3LYP/6-31G(d) {job_type}

Test

0 1
H 0.0 0.0 0.0
"""
            parser = GJFParser()
            is_valid, errors = parser.validate(content)
            assert is_valid, f"Failed for job type {job_type}"

    def test_validate_with_counterpoise(self):
        """Test validation with counterpoise."""
        content = """# B3LYP/6-31G(d) Counterpoise=2

Test

0 1 0 1
H 0.0 0.0 0.0
H 1.0 0.0 0.0
"""
        parser = GJFParser()
        is_valid, errors = parser.validate(content)
        # Should have warnings but be valid
        error_msgs = [e for e in errors if "error" in e.lower()]
        assert len(error_msgs) == 0


class TestServerCoverage:
    """Test server features for full coverage."""

    def test_completion_feature_extended(self):
        """Test completion with full mock setup."""
        mock_params = MagicMock()
        mock_params.text_document.uri = "file:///test.gjf"
        mock_params.position.line = 0

        with patch("gaussian_lsp.server.server") as mock_server:
            mock_doc = MagicMock()
            mock_doc.lines = ["# B3LYP/"]
            mock_server.workspace.get_text_document.return_value = mock_doc

            result = completion(mock_params)

            assert result is not None
            assert hasattr(result, "items")
            assert len(result.items) > 0

    def test_hover_with_basis_set(self):
        """Test hover for basis set keywords."""
        mock_params = MagicMock()
        mock_params.text_document.uri = "file:///test.gjf"
        mock_params.position.line = 0
        mock_params.position.character = 10

        with patch("gaussian_lsp.server.server") as mock_server:
            mock_doc = MagicMock()
            mock_doc.lines = ["# B3LYP/6-31G(d)"]
            mock_server.workspace.get_text_document.return_value = mock_doc

            result = hover(mock_params)
            # May return info or None depending on position
            assert result is None or hasattr(result, "contents")

    def test_get_word_at_extended_positions(self):
        """Test word extraction at various positions."""
        line = "# B3LYP/6-31G(d) opt freq"

        # Position at start of line
        word = _get_word_at_position(line, 0)
        assert word == ""

        # Position at B
        word = _get_word_at_position(line, 2)
        assert word == "B3LYP"

        # Position at end of line
        word = _get_word_at_position(line, len(line))
        assert word == ""

    def test_diagnostic_with_valid_content_no_warnings(self):
        """Test diagnostic with valid content has no errors."""
        content = """%chk=test.chk
# B3LYP/6-31G(d) opt

Test

0 1
H 0.0 0.0 0.0
"""
        diagnostics = _analyze_content(content)

        # Should have no errors
        errors = [d for d in diagnostics if d.severity == types.DiagnosticSeverity.Error]
        assert len(errors) == 0

    def test_diagnostic_missing_route_no_hash(self):
        """Test diagnostic catches route without hash."""
        content = """B3LYP/6-31G(d)

Test

0 1
H 0.0 0.0 0.0
"""
        diagnostics = _analyze_content(content)

        error_msgs = [d.message for d in diagnostics]
        assert any("route" in m.lower() and "#" in m for m in error_msgs)

    def test_diagnostic_with_known_element(self):
        """Test diagnostic doesn't flag valid elements."""
        content = """# B3LYP/6-31G(d)

Test

0 1
C 0.0 0.0 0.0
N 1.0 0.0 0.0
O 0.0 1.0 0.0
H 0.0 0.0 1.0
"""
        diagnostics = _analyze_content(content)

        # Should not have warnings about unknown elements
        for d in diagnostics:
            assert "Unknown element" not in d.message

    def test_diagnostic_with_link0(self):
        """Test diagnostic handles files with Link0."""
        content = """%chk=test.chk
%mem=2GB
%nproc=4
# B3LYP/6-31G(d) opt

Test

0 1
H 0.0 0.0 0.0
"""
        diagnostics = _analyze_content(content)

        # Should be valid
        errors = [d for d in diagnostics if d.severity == types.DiagnosticSeverity.Error]
        assert len(errors) == 0

    def test_format_gjf_with_valid_input(self):
        """Test formatting with valid input."""
        content = """%chk=test.chk
# B3LYP/6-31G(d) opt

Test calculation

0 1
H   0.0   0.0   0.0
"""
        formatted = _format_gjf(content)

        assert "%chk=test.chk" in formatted
        assert "# B3LYP/6-31G(d) opt" in formatted
        assert "Test calculation" in formatted

    def test_format_gjf_with_invalid_route(self):
        """Test formatting returns original for invalid route."""
        content = """Test

0 1
H 0.0 0.0 0.0
"""
        formatted = _format_gjf(content)
        assert formatted == content

    def test_server_initialization(self):
        """Test server is properly initialized."""
        assert server.name == "gaussian-lsp"
        assert server.version == "0.2.0"


class TestParserHelperMethods:
    """Test parser helper methods."""

    def test_parser_get_methods(self):
        """Test get_methods returns list."""
        parser = GJFParser()
        methods = parser.get_methods()
        assert isinstance(methods, list)
        assert len(methods) > 0
        assert "B3LYP" in methods

    def test_parser_get_basis_sets(self):
        """Test get_basis_sets returns list."""
        parser = GJFParser()
        basis_sets = parser.get_basis_sets()
        assert isinstance(basis_sets, list)
        assert len(basis_sets) > 0
        assert "6-31G(d)" in basis_sets

    def test_parser_get_job_types(self):
        """Test get_job_types returns list."""
        parser = GJFParser()
        job_types = parser.get_job_types()
        assert isinstance(job_types, list)
        assert len(job_types) > 0
        assert "OPT" in job_types


class TestGaussianJobMethods:
    """Test GaussianJob methods."""

    def test_to_gjf_empty_modredundant(self):
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
