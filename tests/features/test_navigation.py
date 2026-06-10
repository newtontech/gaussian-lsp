"""Tests for definition, hover, and references navigation features."""

import pytest
from lsprotocol.types import Position

from gaussian_lsp.features.definition import DefinitionProvider, get_definition_provider
from gaussian_lsp.features.references import ReferencesProvider, get_references_provider

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

WATER_GJF = """\
# B3LYP/6-31G(d) opt freq

Water optimization

0 1
O  0.000000  0.000000  0.000000
H  0.000000  0.758602  0.504284
H  0.000000 -0.758602  0.504284
"""

ZMATRIX_GJF = """\
# HF/STO-3G

Z-matrix water

0 1
O
H 1 R1
H 1 R2 2 A1

R1=0.960
R2=0.960
A1=104.5
"""

MULTI_ROUTE_GJF = """\
#P B3LYP/6-31G(d) opt freq

Multi-section

0 1
O  0.0 0.0 0.0
H  0.0 0.758 0.504
H  0.0 -0.758 0.504
"""

URI = "file:///test.gjf"


@pytest.fixture
def definition_provider() -> DefinitionProvider:
    """Create a DefinitionProvider instance for testing."""
    return DefinitionProvider()


@pytest.fixture
def references_provider() -> ReferencesProvider:
    """Create a ReferencesProvider instance for testing."""
    return ReferencesProvider()


# ---------------------------------------------------------------------------
# Factory functions
# ---------------------------------------------------------------------------


class TestFactoryFunctions:
    """Test factory functions."""

    def test_get_definition_provider(self) -> None:
        """Test definition provider factory."""
        provider = get_definition_provider()
        assert isinstance(provider, DefinitionProvider)

    def test_get_references_provider(self) -> None:
        """Test references provider factory."""
        provider = get_references_provider()
        assert isinstance(provider, ReferencesProvider)


# ---------------------------------------------------------------------------
# Definition provider -- route keywords
# ---------------------------------------------------------------------------


class TestDefinitionRouteKeywords:
    """Test go-to-definition for route keywords."""

    def test_definition_method_in_route(self, definition_provider: DefinitionProvider) -> None:
        """Hovering over B3LYP in a route line jumps to the route line."""
        pos = Position(line=0, character=3)  # Position on "B3LYP"
        result = definition_provider.get_definition(WATER_GJF, URI, pos)
        assert result is not None
        assert result.uri == URI
        assert result.range.start.line == 0
        # The matched keyword should contain B3LYP
        assert (
            "B3LYP"
            in WATER_GJF.split("\n")[0][result.range.start.character : result.range.end.character]
        )

    def test_definition_basis_set_in_route(self, definition_provider: DefinitionProvider) -> None:
        """Hovering over 6-31G(d) jumps to the route line."""
        pos = Position(line=0, character=12)  # Position on "6-31G(d)"
        result = definition_provider.get_definition(WATER_GJF, URI, pos)
        assert result is not None
        assert result.range.start.line == 0

    def test_definition_job_type_in_route(self, definition_provider: DefinitionProvider) -> None:
        """Hovering over OPT jumps to the route line."""
        pos = Position(line=0, character=20)  # Position on "opt"
        result = definition_provider.get_definition(WATER_GJF, URI, pos)
        assert result is not None
        assert result.range.start.line == 0

    def test_definition_unknown_keyword_returns_none(
        self, definition_provider: DefinitionProvider
    ) -> None:
        """Unknown keywords return None."""
        pos = Position(line=2, character=0)  # Blank line
        result = definition_provider.get_definition(WATER_GJF, URI, pos)
        assert result is None

    def test_definition_out_of_bounds_returns_none(
        self, definition_provider: DefinitionProvider
    ) -> None:
        """Out-of-bounds position returns None."""
        pos = Position(line=999, character=0)
        result = definition_provider.get_definition(WATER_GJF, URI, pos)
        assert result is None


# ---------------------------------------------------------------------------
# Definition provider -- Z-matrix variables
# ---------------------------------------------------------------------------


class TestDefinitionZmatrix:
    """Test go-to-definition for Z-matrix variables."""

    def test_definition_zmatrix_variable(self, definition_provider: DefinitionProvider) -> None:
        """Jump from R1 reference in geometry to R1=0.960 definition."""
        pos = Position(line=6, character=6)  # Position on "R1" in "H 1 R1"
        result = definition_provider.get_definition(ZMATRIX_GJF, URI, pos)
        assert result is not None
        assert result.uri == URI
        # Should jump to the line "R1=0.960"
        assert result.range.start.line >= 9  # Variable definitions start after geometry

    def test_definition_zmatrix_variable_undefined_returns_none(
        self, definition_provider: DefinitionProvider
    ) -> None:
        """Undefined Z-matrix variable returns None."""
        content = """\
# HF/STO-3G

Undefined var

0 1
O
H 1 UNDEFINED
"""
        pos = Position(line=5, character=6)  # Position on "UNDEFINED"
        result = definition_provider.get_definition(content, URI, pos)
        assert result is None

    def test_definition_cartesian_not_zmatrix(
        self, definition_provider: DefinitionProvider
    ) -> None:
        """Cartesian coordinates do not trigger Z-matrix variable definition."""
        pos = Position(line=5, character=5)  # Position on an O coordinate
        result = definition_provider.get_definition(WATER_GJF, URI, pos)
        # Should return None because Cartesian lines have no variable refs
        assert result is None


# ---------------------------------------------------------------------------
# References provider -- route keywords
# ---------------------------------------------------------------------------


class TestReferencesRouteKeywords:
    """Test find-references for route keywords."""

    def test_references_method_in_route(self, references_provider: ReferencesProvider) -> None:
        """B3LYP should find at least one reference in the route line."""
        pos = Position(line=0, character=3)  # On "B3LYP"
        result = references_provider.get_references(WATER_GJF, URI, pos)
        assert len(result) >= 1
        assert all(loc.uri == URI for loc in result)

    def test_references_basis_set_in_route(self, references_provider: ReferencesProvider) -> None:
        """6-31G(d) should find at least one reference."""
        pos = Position(line=0, character=12)
        result = references_provider.get_references(WATER_GJF, URI, pos)
        assert len(result) >= 1

    def test_references_unknown_keyword_returns_empty(
        self, references_provider: ReferencesProvider
    ) -> None:
        """Unknown tokens return empty references."""
        pos = Position(line=2, character=0)  # Title line
        result = references_provider.get_references(WATER_GJF, URI, pos)
        assert result == []

    def test_references_out_of_bounds_returns_empty(
        self, references_provider: ReferencesProvider
    ) -> None:
        """Out-of-bounds position returns empty."""
        pos = Position(line=999, character=0)
        result = references_provider.get_references(WATER_GJF, URI, pos)
        assert result == []


# ---------------------------------------------------------------------------
# References provider -- Z-matrix variables
# ---------------------------------------------------------------------------


class TestReferencesZmatrix:
    """Test find-references for Z-matrix variables."""

    def test_references_zmatrix_variable(self, references_provider: ReferencesProvider) -> None:
        """R1 should find references in geometry and definition."""
        pos = Position(line=6, character=6)  # On "R1" in geometry
        result = references_provider.get_references(ZMATRIX_GJF, URI, pos)
        assert len(result) >= 2  # At least geometry ref + definition ref
        assert all(loc.uri == URI for loc in result)

    def test_references_zmatrix_variable_from_definition(
        self, references_provider: ReferencesProvider
    ) -> None:
        """References from the definition line should also work."""
        # Position at character 1 on the "R1=0.960" line so the word
        # extraction captures just "R1" (inside the = sign).
        pos = Position(line=9, character=1)  # Inside "R1" on "R1=0.960"
        result = references_provider.get_references(ZMATRIX_GJF, URI, pos)
        assert len(result) >= 2

    def test_references_non_variable_returns_empty(
        self, references_provider: ReferencesProvider
    ) -> None:
        """Non-variable text returns empty references."""
        pos = Position(line=5, character=0)  # "O" element
        result = references_provider.get_references(ZMATRIX_GJF, URI, pos)
        assert result == []


# ---------------------------------------------------------------------------
# Edge cases and multi-file scenarios
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Test edge cases for navigation features."""

    def test_definition_empty_input(self, definition_provider: DefinitionProvider) -> None:
        """Empty input returns None."""
        pos = Position(line=0, character=0)
        result = definition_provider.get_definition("", URI, pos)
        assert result is None

    def test_references_empty_input(self, references_provider: ReferencesProvider) -> None:
        """Empty input returns empty list."""
        pos = Position(line=0, character=0)
        result = references_provider.get_references("", URI, pos)
        assert result == []

    def test_definition_no_route_section(self, definition_provider: DefinitionProvider) -> None:
        """Input without route section returns None for keywords."""
        content = "Some text without route\n\n0 1\nH 0.0 0.0 0.0\n"
        pos = Position(line=0, character=0)
        result = definition_provider.get_definition(content, URI, pos)
        assert result is None

    def test_references_no_route_section(self, references_provider: ReferencesProvider) -> None:
        """Input without route section returns empty for keywords."""
        content = "Some text\n\n0 1\nH 0.0 0.0 0.0\n"
        pos = Position(line=0, character=0)
        result = references_provider.get_references(content, URI, pos)
        assert result == []

    def test_definition_word_at_end_of_line(self, definition_provider: DefinitionProvider) -> None:
        """Position at end of line still extracts word correctly."""
        line = "# B3LYP/6-31G(d) opt freq"
        # Position at the end of "freq"
        pos = Position(line=0, character=len(line) - 1)
        result = definition_provider.get_definition(WATER_GJF, URI, pos)
        assert result is not None

    def test_references_include_declaration_false(
        self, references_provider: ReferencesProvider
    ) -> None:
        """include_declaration=False still returns results."""
        pos = Position(line=0, character=3)  # On "B3LYP"
        result = references_provider.get_references(WATER_GJF, URI, pos, include_declaration=False)
        # Should still return the route-line occurrences (they are both
        # declarations and references in Gaussian).
        assert len(result) >= 1

    def test_definition_multi_section_file(self, definition_provider: DefinitionProvider) -> None:
        """Multi-section file navigates to correct route line."""
        pos = Position(line=0, character=3)  # On "B3LYP"
        result = definition_provider.get_definition(MULTI_ROUTE_GJF, URI, pos)
        assert result is not None
        assert result.range.start.line == 0

    def test_definition_position_on_blank_word(
        self, definition_provider: DefinitionProvider
    ) -> None:
        """Position on whitespace returns None."""
        pos = Position(line=1, character=0)  # Blank line
        result = definition_provider.get_definition(WATER_GJF, URI, pos)
        assert result is None

    def test_references_position_on_blank_word(
        self, references_provider: ReferencesProvider
    ) -> None:
        """Position on whitespace returns empty list."""
        pos = Position(line=1, character=0)  # Blank line
        result = references_provider.get_references(WATER_GJF, URI, pos)
        assert result == []

    def test_definition_zmatrix_no_charge_line(
        self, definition_provider: DefinitionProvider
    ) -> None:
        """Z-matrix definition without charge line returns None."""
        content = "# HF/STO-3G\n\nNo charge\n\nO\nH 1 R1\n\nR1=0.9\n"
        pos = Position(line=5, character=6)
        result = definition_provider.get_definition(content, URI, pos)
        # No charge/mult line means no geometry section detected
        assert result is None
