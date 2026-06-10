"""Tests for the rename provider.

Covers:
  - Z-matrix variable rename (definitions and references)
  - prepareRename validation
  - Rejection of keywords, route tokens, element symbols, unresolved symbols
  - Same-file multi-reference renames
  - Backwards-compatible API tests (is_valid_rename, provider creation)
"""

from __future__ import annotations

import pytest
from lsprotocol.types import Position

from gaussian_lsp.features.rename import (
    RenameProvider,
    _collect_variable_occurrences,
    _find_sections,
    _is_gaussian_keyword,
    _is_valid_variable_name,
    _looks_like_number,
    get_rename_provider,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def provider() -> RenameProvider:
    """Create a RenameProvider instance for testing."""
    return get_rename_provider()


# ---------------------------------------------------------------------------
# Helper GJF texts
# ---------------------------------------------------------------------------

# A minimal Gaussian input with Z-matrix variables
ZMATRIX_GJF = """\
#p B3LYP/6-31G(d) opt

Water molecule

0 1
O
H 1 R1
H 1 R1 2 A1

R1=0.96
A1=104.5
"""

# GJF with repeated variable references
ZMATRIX_MULTI_REF = """\
#p B3LYP/6-31G(d) opt

Ethanol

0 1
C
C 1 CC
O 1 CO 2 ACO
H 1 CH 2 ACH 3 T1
H 1 CH 2 ACH 3 T2

CC=1.54
CO=1.43
CH=1.09
ACO=109.5
ACH=109.5
T1=120.0
T2=120.0
"""

# Simple Cartesian GJF (no Z-matrix variables)
CARTESIAN_GJF = """\
#p B3LYP/6-31G(d) opt

Water molecule

0 1
O  0.000000  0.000000  0.117790
H  0.000000  0.755530 -0.471160
H  0.000000 -0.755530 -0.471160

"""


# ---------------------------------------------------------------------------
# Unit tests: helper functions
# ---------------------------------------------------------------------------


class TestIsValidVariableName:
    """Tests for _is_valid_variable_name."""

    def test_simple_name(self) -> None:
        assert _is_valid_variable_name("R1") is True

    def test_underscore_start(self) -> None:
        assert _is_valid_variable_name("_dist") is True

    def test_leading_digit_rejected(self) -> None:
        assert _is_valid_variable_name("1abc") is False

    def test_empty_rejected(self) -> None:
        assert _is_valid_variable_name("") is False

    def test_spaces_rejected(self) -> None:
        assert _is_valid_variable_name("has space") is False


class TestIsGaussianKeyword:
    """Tests for _is_gaussian_keyword."""

    def test_method_keyword(self) -> None:
        assert _is_gaussian_keyword("B3LYP") is True

    def test_basis_set_keyword(self) -> None:
        assert _is_gaussian_keyword("6-31G") is True

    def test_job_type_keyword(self) -> None:
        assert _is_gaussian_keyword("OPT") is True

    def test_link0_command(self) -> None:
        assert _is_gaussian_keyword("mem") is True

    def test_route_keyword(self) -> None:
        assert _is_gaussian_keyword("SCF") is True

    def test_variable_name_not_keyword(self) -> None:
        assert _is_gaussian_keyword("R1") is False

    def test_myvar_not_keyword(self) -> None:
        assert _is_gaussian_keyword("myvar") is False


class TestLooksLikeNumber:
    """Tests for _looks_like_number."""

    def test_integer(self) -> None:
        assert _looks_like_number("42") is True

    def test_float(self) -> None:
        assert _looks_like_number("1.54") is True

    def test_negative(self) -> None:
        assert _looks_like_number("-0.5") is True

    def test_scientific(self) -> None:
        assert _looks_like_number("1.5e-3") is True

    def test_variable_name(self) -> None:
        assert _looks_like_number("R1") is False

    def test_empty(self) -> None:
        assert _looks_like_number("") is False


class TestFindSections:
    """Tests for _find_sections."""

    def test_finds_charge_and_geometry_end(self) -> None:
        charge_line, geom_end = _find_sections(ZMATRIX_GJF)
        assert charge_line is not None
        assert geom_end is not None

    def test_cartesian_has_no_zmatrix_vars(self) -> None:
        charge_line, geom_end = _find_sections(CARTESIAN_GJF)
        assert charge_line is not None
        assert geom_end is not None


class TestCollectVariableOccurrences:
    """Tests for _collect_variable_occurrences."""

    def test_finds_definition(self) -> None:
        occs = _collect_variable_occurrences(ZMATRIX_GJF, "R1")
        defs = [o for o in occs if o.kind == "definition"]
        assert len(defs) >= 1

    def test_finds_reference(self) -> None:
        occs = _collect_variable_occurrences(ZMATRIX_GJF, "R1")
        refs = [o for o in occs if o.kind == "reference"]
        assert len(refs) >= 1

    def test_no_match(self) -> None:
        occs = _collect_variable_occurrences(ZMATRIX_GJF, "NONEXISTENT")
        assert len(occs) == 0

    def test_both_definition_and_reference(self) -> None:
        occs = _collect_variable_occurrences(ZMATRIX_GJF, "R1")
        kinds = {o.kind for o in occs}
        assert "definition" in kinds
        assert "reference" in kinds

    def test_multiple_references(self) -> None:
        occs = _collect_variable_occurrences(ZMATRIX_MULTI_REF, "CH")
        refs = [o for o in occs if o.kind == "reference"]
        # CH is referenced twice (lines with H 1 CH ...)
        assert len(refs) == 2

    def test_cartesian_no_zmatrix_vars(self) -> None:
        occs = _collect_variable_occurrences(CARTESIAN_GJF, "R1")
        assert len(occs) == 0


# ---------------------------------------------------------------------------
# prepareRename tests
# ---------------------------------------------------------------------------


class TestPrepareRename:
    """Tests for prepareRename validation."""

    def test_variable_definition(self, provider: RenameProvider) -> None:
        # R1 is on the line "R1=0.96" which is line 10 in ZMATRIX_GJF
        result = provider.prepare_rename(ZMATRIX_GJF, Position(line=10, character=1))
        assert result is not None
        assert result.start.character == 0
        assert result.end.character == 2

    def test_variable_reference_in_geometry(self, provider: RenameProvider) -> None:
        # "H 1 R1" is line 7, R1 starts at column 4
        result = provider.prepare_rename(ZMATRIX_GJF, Position(line=7, character=5))
        assert result is not None

    def test_route_keyword_rejected(self, provider: RenameProvider) -> None:
        # Route line is "#p B3LYP/6-31G(d) opt"
        result = provider.prepare_rename(ZMATRIX_GJF, Position(line=0, character=10))
        assert result is None

    def test_element_symbol_rejected(self, provider: RenameProvider) -> None:
        # "O" on line 6 is an element, not a variable
        result = provider.prepare_rename(ZMATRIX_GJF, Position(line=6, character=0))
        assert result is None

    def test_empty_document(self, provider: RenameProvider) -> None:
        result = provider.prepare_rename("", Position(line=0, character=0))
        assert result is None

    def test_out_of_range(self, provider: RenameProvider) -> None:
        result = provider.prepare_rename("hello", Position(line=99, character=0))
        assert result is None

    def test_cartesian_no_rename(self, provider: RenameProvider) -> None:
        # Cartesian coordinates have no Z-matrix variables to rename
        result = provider.prepare_rename(CARTESIAN_GJF, Position(line=6, character=10))
        assert result is None

    def test_title_rejected(self, provider: RenameProvider) -> None:
        # Title line "Water molecule"
        result = provider.prepare_rename(ZMATRIX_GJF, Position(line=2, character=3))
        assert result is None

    def test_charge_mult_rejected(self, provider: RenameProvider) -> None:
        # "0 1" line
        result = provider.prepare_rename(ZMATRIX_GJF, Position(line=5, character=1))
        assert result is None

    def test_numeric_in_geometry_rejected(self, provider: RenameProvider) -> None:
        # "1" (atom index) in "H 1 R1"
        result = provider.prepare_rename(ZMATRIX_GJF, Position(line=7, character=3))
        assert result is None


# ---------------------------------------------------------------------------
# get_rename_edits tests
# ---------------------------------------------------------------------------


class TestRenameVariable:
    """Tests for renaming Z-matrix variables."""

    def test_rename_definition_only(self, provider: RenameProvider) -> None:
        """Rename a variable that is defined but only referenced once."""
        text = ZMATRIX_GJF
        # Position on R1 definition (line 10)
        edits = provider.get_rename_edits(
            text, "file:///test.gjf", Position(line=10, character=1), "BondLen"
        )
        assert edits is not None
        changes = edits.changes["file:///test.gjf"]
        # Should rename both definition and reference
        assert len(changes) >= 2
        new_texts = [c.new_text for c in changes]
        assert "BondLen" in new_texts

    def test_rename_from_reference(self, provider: RenameProvider) -> None:
        """Renaming should work when initiated from a variable reference."""
        text = ZMATRIX_GJF
        # Position on R1 reference in "H 1 R1" (line 7)
        edits = provider.get_rename_edits(
            text, "file:///test.gjf", Position(line=7, character=5), "BondLen"
        )
        assert edits is not None
        changes = edits.changes["file:///test.gjf"]
        assert len(changes) >= 2

    def test_rename_multiple_references(self, provider: RenameProvider) -> None:
        """Rename a variable with multiple references."""
        text = ZMATRIX_MULTI_REF
        # Position on CH definition
        edits = provider.get_rename_edits(
            text, "file:///test.gjf", Position(line=15, character=1), "CH_new"
        )
        assert edits is not None
        changes = edits.changes["file:///test.gjf"]
        # 1 definition + 2 references = 3 edits
        assert len(changes) == 3

    def test_rename_rejects_invalid_new_name(self, provider: RenameProvider) -> None:
        """Leading digits are not valid variable names."""
        text = ZMATRIX_GJF
        edits = provider.get_rename_edits(
            text, "file:///test.gjf", Position(line=10, character=1), "123invalid"
        )
        assert edits is None

    def test_rename_rejects_empty_new_name(self, provider: RenameProvider) -> None:
        text = ZMATRIX_GJF
        edits = provider.get_rename_edits(
            text, "file:///test.gjf", Position(line=10, character=1), ""
        )
        assert edits is None

    def test_unresolved_reference_rejected(self, provider: RenameProvider) -> None:
        """A variable reference with no definition should be rejected."""
        # Create a GJF with a reference that has no definition
        text = """\
#p B3LYP/6-31G(d) opt

Test

0 1
O
H 1 UNDEF

"""
        edits = provider.get_rename_edits(
            text, "file:///test.gjf", Position(line=6, character=5), "newname"
        )
        assert edits is None

    def test_route_keyword_rename_rejected(self, provider: RenameProvider) -> None:
        text = ZMATRIX_GJF
        # Route section B3LYP
        edits = provider.get_rename_edits(
            text, "file:///test.gjf", Position(line=0, character=5), "MP2"
        )
        assert edits is None

    def test_element_rename_rejected(self, provider: RenameProvider) -> None:
        text = ZMATRIX_GJF
        # Element O on line 6
        edits = provider.get_rename_edits(
            text, "file:///test.gjf", Position(line=6, character=0), "N"
        )
        assert edits is None

    def test_empty_document(self, provider: RenameProvider) -> None:
        edits = provider.get_rename_edits(
            "", "file:///test.gjf", Position(line=0, character=0), "newname"
        )
        assert edits is None

    def test_out_of_range(self, provider: RenameProvider) -> None:
        edits = provider.get_rename_edits(
            "hello", "file:///test.gjf", Position(line=99, character=0), "newname"
        )
        assert edits is None

    def test_not_on_variable(self, provider: RenameProvider) -> None:
        text = ZMATRIX_GJF
        # Title line
        edits = provider.get_rename_edits(
            text, "file:///test.gjf", Position(line=2, character=3), "newname"
        )
        assert edits is None

    def test_cartesian_no_rename(self, provider: RenameProvider) -> None:
        edits = provider.get_rename_edits(
            CARTESIAN_GJF, "file:///test.gjf", Position(line=6, character=10), "newname"
        )
        assert edits is None

    def test_edit_positions_correct(self, provider: RenameProvider) -> None:
        """Verify edit ranges map to the correct positions."""
        text = ZMATRIX_GJF
        edits = provider.get_rename_edits(
            text, "file:///test.gjf", Position(line=10, character=1), "BondLen"
        )
        assert edits is not None
        changes = edits.changes["file:///test.gjf"]

        # Find the definition edit (should be on line 10)
        def_edits = [c for c in changes if c.range.start.line == 10]
        assert len(def_edits) == 1
        assert def_edits[0].new_text == "BondLen"
        assert def_edits[0].range.start.character == 0
        assert def_edits[0].range.end.character == 2  # "R1"

        # Find reference edits (should be on geometry lines, not line 10)
        ref_edits = [c for c in changes if c.range.start.line != 10]
        assert len(ref_edits) >= 1


# ---------------------------------------------------------------------------
# is_valid_rename tests
# ---------------------------------------------------------------------------


class TestIsValidRename:
    """Tests for the is_valid_rename check."""

    def test_valid_variable_rename(self, provider: RenameProvider) -> None:
        text = ZMATRIX_GJF
        assert provider.is_valid_rename(text, Position(line=10, character=1), "NewDist") is True

    def test_invalid_variable_name(self, provider: RenameProvider) -> None:
        text = ZMATRIX_GJF
        assert provider.is_valid_rename(text, Position(line=10, character=1), "1bad") is False

    def test_not_on_variable(self, provider: RenameProvider) -> None:
        text = ZMATRIX_GJF
        assert provider.is_valid_rename(text, Position(line=0, character=5), "MP2") is False

    def test_empty_document(self, provider: RenameProvider) -> None:
        assert provider.is_valid_rename("", Position(line=0, character=0), "newname") is False


# ---------------------------------------------------------------------------
# Backwards-compatible / provider creation tests
# ---------------------------------------------------------------------------


class TestRenameProvider:
    """Test rename provider creation and basic API."""

    def test_provider_creation(self) -> None:
        provider = RenameProvider()
        assert provider is not None
        assert provider.server is None

    def test_get_rename_provider(self) -> None:
        provider = get_rename_provider()
        assert provider is not None

    def test_get_rename_provider_with_server(self) -> None:
        provider = get_rename_provider(server=None)
        assert provider is not None


# ---------------------------------------------------------------------------
# Integration-style: realistic Gaussian inputs
# ---------------------------------------------------------------------------


class TestRenameRealisticInput:
    """Tests with realistic Gaussian input files."""

    @pytest.fixture
    def provider(self) -> RenameProvider:
        return get_rename_provider()

    def test_rename_in_full_zmatrix_input(self, provider: RenameProvider) -> None:
        text = ZMATRIX_GJF
        # Rename R1 -> BondLen
        edits = provider.get_rename_edits(
            text, "file:///water.gjf", Position(line=10, character=1), "BondLen"
        )
        assert edits is not None
        changes = edits.changes["file:///water.gjf"]
        # 1 definition + 2 references (H 1 R1 appears twice)
        assert len(changes) >= 2

    def test_prepare_rename_in_realistic_input(self, provider: RenameProvider) -> None:
        text = ZMATRIX_GJF
        # On variable definition
        result = provider.prepare_rename(text, Position(line=10, character=1))
        assert result is not None

        # On variable reference
        result = provider.prepare_rename(text, Position(line=7, character=5))
        assert result is not None

    def test_prepare_rename_route_rejected(self, provider: RenameProvider) -> None:
        text = ZMATRIX_GJF
        result = provider.prepare_rename(text, Position(line=0, character=3))
        assert result is None

    def test_rename_preserves_other_variables(self, provider: RenameProvider) -> None:
        """Renaming R1 should not affect A1."""
        text = ZMATRIX_GJF
        edits = provider.get_rename_edits(
            text, "file:///water.gjf", Position(line=10, character=1), "BondLen"
        )
        assert edits is not None
        changes = edits.changes["file:///water.gjf"]
        # All edits should rename R1 -> BondLen
        for change in changes:
            assert change.new_text == "BondLen"

    def test_rename_angle_variable(self, provider: RenameProvider) -> None:
        """Test renaming an angle variable (A1)."""
        text = ZMATRIX_GJF
        # A1 is defined on line 10 ("A1=104.5")
        edits = provider.get_rename_edits(
            text, "file:///water.gjf", Position(line=10, character=1), "Angle"
        )
        assert edits is not None
        changes = edits.changes["file:///water.gjf"]
        # 1 definition + 1 reference
        assert len(changes) == 2
        for change in changes:
            assert change.new_text == "Angle"

    def test_rename_with_link0_section(self, provider: RenameProvider) -> None:
        """Test that Link0 commands are not renameable."""
        text = """\
%chk=molecule.chk
%mem=4GB
#p B3LYP/6-31G(d) opt

Water

0 1
O
H 1 R1
H 1 R1 2 A1

R1=0.96
A1=104.5
"""
        # Try to rename "mem" - should fail since it's a keyword
        edits = provider.get_rename_edits(
            text, "file:///test.gjf", Position(line=1, character=3), "memory"
        )
        assert edits is None

        # Rename the Z-matrix variable instead (R1 definition is on line 11)
        edits = provider.get_rename_edits(
            text, "file:///test.gjf", Position(line=11, character=1), "BondLen"
        )
        assert edits is not None
