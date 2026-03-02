"""Additional tests for 100% coverage."""

import pytest
from pathlib import Path

from gaussian_lsp.parser.gjf_parser import (
    GJFParser,
    GaussianJob,
    parse_gjf,
    parse_gjf_file,
)
from gaussian_lsp.server import parse_gjf_document


class TestCoverageGaps:
    """Tests to fill coverage gaps."""

    def test_job_to_gjf_with_link0(self):
        """Test to_gjf() with link0 section (lines 27-29)."""
        job = GaussianJob(
            route_section="# B3LYP/6-31G(d)",
            title="Test",
            charge=0,
            multiplicity=1,
            atoms=[("H", 0.0, 0.0, 0.0)],
            link0={"chk": "test.chk", "mem": "1GB"}
        )
        
        result = job.to_gjf()
        assert "%chk=test.chk" in result
        assert "%mem=1GB" in result

    def test_parse_multiline_route(self):
        """Test parsing multiline route section (line 102)."""
        content = """# B3LYP/6-31G(d) opt freq
#

Test calculation

0 1
H 0.0 0.0 0.0
"""
        parser = GJFParser()
        job = parser.parse(content)
        # Should have combined route section
        assert "B3LYP" in job.route_section

    def test_parse_with_blank_line_in_geometry(self):
        """Test parsing with blank line ending geometry (line 130)."""
        content = """# HF/STO-3G

Test

0 1
H 0.0 0.0 0.0

Some variable section
"""
        parser = GJFParser()
        job = parser.parse(content)
        assert len(job.atoms) == 1

    def test_validate_unknown_element(self):
        """Test validation with unknown element (line 132)."""
        content = """# HF/STO-3G

Test

0 1
Xx 0.0 0.0 0.0
"""
        parser = GJFParser()
        is_valid, errors = parser.validate(content)
        assert not is_valid
        assert any("Unknown element" in e for e in errors)

    def test_parse_gjf_document_success(self):
        """Test parse_gjf_document with valid content."""
        content = """# B3LYP/6-31G(d)

Test

0 1
H 0.0 0.0 0.0
"""
        result = parse_gjf_document(content)
        assert result is not None
        assert result.route_section == "# B3LYP/6-31G(d)"

    def test_parse_gjf_document_none(self):
        """Test parse_gjf_document returns None for empty."""
        result = parse_gjf_document(None)
        assert result is None
