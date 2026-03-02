"""Tests for Gaussian GJF parser."""


import pytest

from gaussian_lsp.parser.gjf_parser import (
    GAUSSIAN_BASIS_SETS,
    GAUSSIAN_JOB_TYPES,
    GAUSSIAN_METHODS,
    LINK0_COMMANDS,
    VALID_ELEMENTS,
    GaussianJob,
    GJFParser,
    parse_com,
    parse_com_file,
    parse_gjf,
    parse_gjf_file,
    validate_gjf,
)


class TestConstants:
    """Test module constants."""

    def test_valid_elements(self):
        """Test valid elements include common atoms."""
        assert "H" in VALID_ELEMENTS
        assert "C" in VALID_ELEMENTS
        assert "N" in VALID_ELEMENTS
        assert "O" in VALID_ELEMENTS
        assert "Fe" in VALID_ELEMENTS
        assert "Au" in VALID_ELEMENTS
        assert "Og" in VALID_ELEMENTS

    def test_gaussian_methods(self):
        """Test methods list is populated."""
        assert "B3LYP" in GAUSSIAN_METHODS
        assert "HF" in GAUSSIAN_METHODS
        assert "MP2" in GAUSSIAN_METHODS

    def test_gaussian_basis_sets(self):
        """Test basis sets list is populated."""
        assert "6-31G(d)" in GAUSSIAN_BASIS_SETS
        assert "cc-pVTZ" in GAUSSIAN_BASIS_SETS

    def test_gaussian_job_types(self):
        """Test job types list is populated."""
        assert "OPT" in GAUSSIAN_JOB_TYPES
        assert "FREQ" in GAUSSIAN_JOB_TYPES

    def test_link0_commands(self):
        """Test Link0 commands list."""
        assert "chk" in LINK0_COMMANDS
        assert "mem" in LINK0_COMMANDS
        assert "nproc" in LINK0_COMMANDS


class TestGaussianJob:
    """Test GaussianJob dataclass."""

    def test_job_creation(self):
        """Test creating a GaussianJob."""
        job = GaussianJob(
            route_section="# B3LYP/6-31G(d) opt",
            title="Test calculation",
            charge=0,
            multiplicity=1,
            atoms=[("C", 0.0, 0.0, 0.0), ("H", 1.0, 0.0, 0.0)],
        )

        assert job.route_section == "# B3LYP/6-31G(d) opt"
        assert job.title == "Test calculation"
        assert job.charge == 0
        assert job.multiplicity == 1
        assert len(job.atoms) == 2
        assert job.atoms[0] == ("C", 0.0, 0.0, 0.0)
        assert job.modredundant == []

    def test_job_to_gjf(self):
        """Test converting job back to GJF format."""
        job = GaussianJob(
            route_section="# B3LYP/6-31G(d) opt",
            title="Test",
            charge=0,
            multiplicity=1,
            atoms=[("H", 0.0, 0.0, 0.0)],
        )

        gjf = job.to_gjf()
        assert "# B3LYP/6-31G(d) opt" in gjf
        assert "Test" in gjf
        assert "0 1" in gjf
        assert "H" in gjf

    def test_job_to_gjf_with_link0(self):
        """Test converting job with Link0 to GJF."""
        job = GaussianJob(
            link0={"chk": "test.chk", "mem": "1GB"},
            route_section="# HF/STO-3G",
            title="Test",
            charge=0,
            multiplicity=1,
            atoms=[("H", 0.0, 0.0, 0.0)],
        )

        gjf = job.to_gjf()
        assert "%chk=test.chk" in gjf
        assert "%mem=1GB" in gjf
        assert "# HF/STO-3G" in gjf

    def test_job_to_gjf_with_modredundant(self):
        """Test converting job with ModRedundant."""
        job = GaussianJob(
            route_section="# B3LYP/6-31G(d) opt",
            title="Test",
            charge=0,
            multiplicity=1,
            atoms=[("H", 0.0, 0.0, 0.0), ("H", 1.0, 0.0, 0.0)],
            modredundant=["B 1 2", "F"],
        )

        gjf = job.to_gjf()
        assert "B 1 2" in gjf
        assert "F" in gjf

    def test_job_default_values(self):
        """Test job default values."""
        job = GaussianJob()
        assert job.route_section == ""
        assert job.title == ""
        assert job.charge == 0
        assert job.multiplicity == 1
        assert job.atoms == []
        assert job.link0 == {}
        assert job.modredundant == []


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

    def test_parse_with_comments(self):
        """Test parsing GJF with comments."""
        content = """! This is a comment
# B3LYP/6-31G(d)

! Another comment
Test

0 1
H 0.0 0.0 0.0
"""
        parser = GJFParser()
        job = parser.parse(content)

        assert job.route_section == "# B3LYP/6-31G(d)"
        assert job.title == "Test"

    def test_parse_multi_line_route(self):
        """Test parsing multi-line route section."""
        content = """# B3LYP/6-31G(d)
# opt freq

Test

0 1
H 0.0 0.0 0.0
"""
        parser = GJFParser()
        job = parser.parse(content)

        assert "# B3LYP/6-31G(d)" in job.route_section
        assert "# opt freq" in job.route_section

    def test_parse_with_modredundant(self):
        """Test parsing with ModRedundant section."""
        content = """# B3LYP/6-31G(d) opt

Test

0 1
H 0.0 0.0 0.0
H 1.0 0.0 0.0

B 1 2
F
"""
        parser = GJFParser()
        job = parser.parse(content)

        assert len(job.atoms) == 2
        assert "B 1 2" in job.modredundant
        assert "F" in job.modredundant

    def test_parse_oniom_layer(self):
        """Test parsing with ONIOM layer specification."""
        content = """# ONIOM(B3LYP/6-31G(d):PM6)

Test ONIOM

0 1
C(High) 0.0 0.0 0.0
H(Low)  1.0 0.0 0.0
"""
        parser = GJFParser()
        job = parser.parse(content)

        assert job.atoms[0][0] == "C"
        assert job.atoms[1][0] == "H"

    def test_parse_empty_content(self):
        """Test parsing empty content raises error."""
        parser = GJFParser()
        with pytest.raises(ValueError, match="Empty"):
            parser.parse("")

    def test_parse_whitespace_only_content(self):
        """Test parsing whitespace-only content raises error."""
        parser = GJFParser()
        with pytest.raises(ValueError, match="Empty"):
            parser.parse("   \n   \n   ")

    def test_parse_file_not_found(self, tmp_path):
        """Test parsing non-existent file."""
        parser = GJFParser()
        with pytest.raises(FileNotFoundError):
            parser.parse_file(str(tmp_path / "nonexistent.gjf"))

    def test_parse_file_success(self, tmp_path):
        """Test parsing existing file."""
        gjf_file = tmp_path / "test.gjf"
        gjf_file.write_text(
            """# HF/STO-3G

Test file

0 1
H 0.0 0.0 0.0
"""
        )

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
        # May have warnings but no errors
        assert not any("Parse error" in e or "Missing" in e or "No atoms" in e for e in errors)

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

    def test_validate_route_without_hash(self):
        """Test validation catches route without hash."""
        content = """B3LYP/6-31G(d)

Test

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

    def test_validate_unknown_element(self):
        """Test validation treats unknown element as error."""
        content = """# B3LYP/6-31G(d)

Test

0 1
Xx 0.0 0.0 0.0
"""
        parser = GJFParser()
        is_valid, errors = parser.validate(content)

        # Unknown elements are treated as errors
        assert not is_valid
        assert any("Unknown element" in e for e in errors)

    def test_validate_invalid_multiplicity(self):
        """Test validation catches invalid multiplicity."""
        content = """# B3LYP/6-31G(d)

Test

0 0
H 0.0 0.0 0.0
"""
        parser = GJFParser()
        is_valid, errors = parser.validate(content)

        assert not is_valid
        assert any("multiplicity" in e.lower() for e in errors)

    def test_validate_no_method(self):
        """Test validation warns about missing method."""
        content = """# 6-31G(d)

Test

0 1
H 0.0 0.0 0.0
"""
        parser = GJFParser()
        is_valid, errors = parser.validate(content)

        # Should have warning about method
        assert any("method" in e.lower() for e in errors)

    def test_validate_no_basis(self):
        """Test validation warns about missing basis."""
        content = """# HF

Test

0 1
H 0.0 0.0 0.0
"""
        parser = GJFParser()
        is_valid, errors = parser.validate(content)

        # Should have warning about basis
        assert any("basis" in e.lower() for e in errors)

    def test_validate_with_gen_basis(self):
        """Test validation accepts Gen basis."""
        content = """# HF/Gen

Test

0 1
H 0.0 0.0 0.0
"""
        parser = GJFParser()
        is_valid, errors = parser.validate(content)

        # Should not warn about missing basis when using Gen
        assert not any("basis set" in e.lower() for e in errors)

    def test_validate_unusual_link0(self):
        """Test validation warns about unusual Link0 command."""
        content = """%unusual=value
# HF/STO-3G

Test

0 1
H 0.0 0.0 0.0
"""
        parser = GJFParser()
        is_valid, errors = parser.validate(content)

        assert is_valid  # It's a warning
        assert any("unusual" in e.lower() for e in errors)

    def test_validate_parse_error(self):
        """Test validation handles parse error."""
        content = ""
        parser = GJFParser()
        is_valid, errors = parser.validate(content)

        assert not is_valid
        assert any("parse" in e.lower() for e in errors)

    def test_get_methods(self):
        """Test get_methods returns copy."""
        parser = GJFParser()
        methods = parser.get_methods()
        assert len(methods) > 0
        assert methods is not GAUSSIAN_METHODS  # Should be a copy

    def test_get_basis_sets(self):
        """Test get_basis_sets returns copy."""
        parser = GJFParser()
        basis_sets = parser.get_basis_sets()
        assert len(basis_sets) > 0
        assert basis_sets is not GAUSSIAN_BASIS_SETS

    def test_get_job_types(self):
        """Test get_job_types returns copy."""
        parser = GJFParser()
        job_types = parser.get_job_types()
        assert len(job_types) > 0
        assert job_types is not GAUSSIAN_JOB_TYPES


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
        gjf_file.write_text(
            """# MP2/6-31G(d)

Test func

0 1
C 0.0 0.0 0.0
"""
        )

        job = parse_gjf_file(str(gjf_file))

        assert job.route_section == "# MP2/6-31G(d)"
        assert job.title == "Test func"

    def test_parse_com_function(self):
        """Test parse_com convenience function."""
        content = """# HF/STO-3G

Test

0 1
H 0.0 0.0 0.0
"""
        job = parse_com(content)

        assert job.route_section == "# HF/STO-3G"

    def test_parse_com_file_function(self, tmp_path):
        """Test parse_com_file convenience function."""
        com_file = tmp_path / "test.com"
        com_file.write_text(
            """# B3LYP/6-31G(d)

Test COM file

0 1
O 0.0 0.0 0.0
"""
        )

        job = parse_com_file(str(com_file))

        assert job.route_section == "# B3LYP/6-31G(d)"
        assert job.title == "Test COM file"

    def test_validate_gjf_function(self):
        """Test validate_gjf convenience function."""
        content = """# HF/STO-3G

Valid

0 1
H 0.0 0.0 0.0
"""
        is_valid, errors = validate_gjf(content)

        assert is_valid
        # May have warnings but no errors
        assert not any("Parse error" in e or "Missing" in e or "No atoms" in e for e in errors)
