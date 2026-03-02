"""Tests for Gaussian GJF parser."""

import pytest
from pathlib import Path

from gaussian_lsp.parser.gjf_parser import (
    GJFParser,
    GaussianJob,
    parse_gjf,
    parse_gjf_file,
)


class TestGaussianJob:
    """Test GaussianJob dataclass."""
    
    def test_job_creation(self):
        """Test creating a GaussianJob."""
        job = GaussianJob(
            route_section="# B3LYP/6-31G(d) opt",
            title="Test calculation",
            charge=0,
            multiplicity=1,
            atoms=[("C", 0.0, 0.0, 0.0), ("H", 1.0, 0.0, 0.0)]
        )
        
        assert job.route_section == "# B3LYP/6-31G(d) opt"
        assert job.title == "Test calculation"
        assert job.charge == 0
        assert job.multiplicity == 1
        assert len(job.atoms) == 2
        assert job.atoms[0] == ("C", 0.0, 0.0, 0.0)
    
    def test_job_to_gjf(self):
        """Test converting job back to GJF format."""
        job = GaussianJob(
            route_section="# B3LYP/6-31G(d) opt",
            title="Test",
            charge=0,
            multiplicity=1,
            atoms=[("H", 0.0, 0.0, 0.0)]
        )
        
        gjf = job.to_gjf()
        assert "# B3LYP/6-31G(d) opt" in gjf
        assert "Test" in gjf
        assert "0 1" in gjf
        assert "H" in gjf


class TestGJFParser:
    """Test GJFParser class."""
    
    def test_parse_simple_gjf(self):
        """Test parsing a simple GJF file."""
        content = """# B3LYP/6-31G(d) opt

Test calculation

0 1
H 0.0 0.0 0.0
"""
        parser = GJFParser()
        job = parser.parse(content)
        
        assert job.route_section == "# B3LYP/6-31G(d) opt"
        assert job.title == "Test calculation"
        assert job.charge == 0
        assert job.multiplicity == 1
        assert len(job.atoms) == 1
        assert job.atoms[0] == ("H", 0.0, 0.0, 0.0)
    
    def test_parse_with_link0(self):
        """Test parsing GJF with Link0 section."""
        content = """%chk=test.chk
%mem=1GB
%nproc=4

# B3LYP/6-31G(d) opt

Test with link0

0 1
H 0.0 0.0 0.0
"""
        parser = GJFParser()
        job = parser.parse(content)
        
        assert job.link0["chk"] == "test.chk"
        assert job.link0["mem"] == "1GB"
        assert job.link0["nproc"] == "4"
    
    def test_parse_multiple_atoms(self):
        """Test parsing GJF with multiple atoms."""
        content = """# B3LYP/6-31G(d)

Water molecule

0 1
O  0.000000  0.000000  0.000000
H  0.757160  0.586260  0.000000
H -0.757160  0.586260  0.000000
"""
        parser = GJFParser()
        job = parser.parse(content)
        
        assert len(job.atoms) == 3
        assert job.atoms[0][0] == "O"
        assert job.atoms[1][0] == "H"
        assert abs(job.atoms[1][1] - 0.757160) < 0.0001
    
    def test_parse_empty_content(self):
        """Test parsing empty content raises error."""
        parser = GJFParser()
        with pytest.raises(ValueError, match="Empty"):
            parser.parse("")
    
    def test_parse_file_not_found(self, tmp_path):
        """Test parsing non-existent file."""
        parser = GJFParser()
        with pytest.raises(FileNotFoundError):
            parser.parse_file(str(tmp_path / "nonexistent.gjf"))
    
    def test_parse_file_success(self, tmp_path):
        """Test parsing existing file."""
        gjf_file = tmp_path / "test.gjf"
        gjf_file.write_text("""# HF/STO-3G

Test file

0 1
H 0.0 0.0 0.0
""")
        
        parser = GJFParser()
        job = parser.parse_file(str(gjf_file))
        
        assert job.route_section == "# HF/STO-3G"
        assert job.title == "Test file"
    
    def test_validate_valid_gjf(self):
        """Test validation of valid GJF."""
        content = """# B3LYP/6-31G(d)

Valid

0 1
H 0.0 0.0 0.0
"""
        parser = GJFParser()
        is_valid, errors = parser.validate(content)
        
        assert is_valid
        assert len(errors) == 0
    
    def test_validate_missing_route(self):
        """Test validation catches missing route."""
        content = """Test

0 1
H 0.0 0.0 0.0
"""
        parser = GJFParser()
        is_valid, errors = parser.validate(content)
        
        assert not is_valid
        assert any("route" in e.lower() for e in errors)
    
    def test_validate_missing_atoms(self):
        """Test validation catches missing atoms."""
        content = """# B3LYP/6-31G(d)

Test

0 1
"""
        parser = GJFParser()
        is_valid, errors = parser.validate(content)
        
        assert not is_valid
        assert any("atom" in e.lower() for e in errors)


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    def test_parse_gjf_function(self):
        """Test parse_gjf convenience function."""
        content = """# HF/STO-3G

Test

0 1
H 0.0 0.0 0.0
"""
        job = parse_gjf(content)
        
        assert job.route_section == "# HF/STO-3G"
        assert job.title == "Test"
    
    def test_parse_gjf_file_function(self, tmp_path):
        """Test parse_gjf_file convenience function."""
        gjf_file = tmp_path / "test.gjf"
        gjf_file.write_text("""# MP2/6-31G(d)

Test func

0 1
C 0.0 0.0 0.0
""")
        
        job = parse_gjf_file(str(gjf_file))
        
        assert job.route_section == "# MP2/6-31G(d)"
        assert job.title == "Test func"
