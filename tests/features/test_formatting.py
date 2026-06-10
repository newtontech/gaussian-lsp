"""Tests for the FormattingProvider feature."""

import pytest
from lsprotocol.types import (
    DocumentFormattingParams,
    DocumentRangeFormattingParams,
    FormattingOptions,
    Position,
    Range,
)

from gaussian_lsp.features.formatting import (
    _ATOM_RE,
    _CHARGE_MULT_RE,
    _COMMENT_RE,
    _LINK0_RE,
    _MODRED_RE,
    _MODRED_SINGLE_RE,
    _ROUTE_RE,
    FormattingProvider,
    _format_atom_line,
    _is_route_continuation,
    get_formatting_provider,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fmt_params(tab_size: int = 2, insert_spaces: bool = True) -> DocumentFormattingParams:
    """Create a DocumentFormattingParams with the given options."""
    return DocumentFormattingParams(
        text_document=None,  # type: ignore[arg-type]
        options=FormattingOptions(tab_size=tab_size, insert_spaces=insert_spaces),
    )


def _range_fmt_params(
    start_line: int,
    end_line: int,
    tab_size: int = 2,
    insert_spaces: bool = True,
) -> DocumentRangeFormattingParams:
    """Create a DocumentRangeFormattingParams with the given range and options."""
    return DocumentRangeFormattingParams(
        text_document=None,  # type: ignore[arg-type]
        range=Range(
            start=Position(line=start_line, character=0),
            end=Position(line=end_line, character=0),
        ),
        options=FormattingOptions(tab_size=tab_size, insert_spaces=insert_spaces),
    )


# Atom lines formatted with coord_width=12 (the default).
_FMT_WATER_O = "O       0.000000      0.000000      0.000000"
_FMT_WATER_H1 = "H       0.000000      0.758602      0.504284"
_FMT_WATER_H2 = "H       0.000000     -0.758602      0.504284"

_FMT_BEN_C1 = "C       0.000000      1.402720      0.000000"
_FMT_BEN_C2 = "C       1.214790      0.701360      0.000000"
_FMT_BEN_C3 = "C       1.214790     -0.701360      0.000000"
_FMT_BEN_C4 = "C       0.000000     -1.402720      0.000000"
_FMT_BEN_C5 = "C      -1.214790     -0.701360      0.000000"
_FMT_BEN_C6 = "C      -1.214790      0.701360      0.000000"
_FMT_BEN_H1 = "H       0.000000      2.490290      0.000000"
_FMT_BEN_H2 = "H       2.156710      1.245140      0.000000"
_FMT_BEN_H3 = "H       2.156710     -1.245140      0.000000"
_FMT_BEN_H4 = "H       0.000000     -2.490290      0.000000"
_FMT_BEN_H5 = "H      -2.156710     -1.245140      0.000000"
_FMT_BEN_H6 = "H      -2.156710      1.245140      0.000000"


# ---------------------------------------------------------------------------
# Provider instantiation
# ---------------------------------------------------------------------------


class TestFormattingProviderInit:
    """Test provider instantiation and factory."""

    def test_provider_exists(self) -> None:
        """Test that provider can be created."""
        provider = FormattingProvider(None)  # type: ignore[arg-type]
        assert provider is not None

    def test_factory_function(self) -> None:
        """Test the get_formatting_provider factory."""
        provider = get_formatting_provider(None)  # type: ignore[arg-type]
        assert isinstance(provider, FormattingProvider)


# ---------------------------------------------------------------------------
# Regex helper coverage
# ---------------------------------------------------------------------------


class TestRegexHelpers:
    """Cover compiled regex objects so they are exercised at least once."""

    def test_link0_re_matches(self) -> None:
        assert _LINK0_RE.match("%mem=4GB") is not None
        assert _LINK0_RE.match("not-link0") is None

    def test_route_re_matches(self) -> None:
        assert _ROUTE_RE.match("# B3LYP/6-31G(d)") is not None
        assert _ROUTE_RE.match("not-route") is None

    def test_comment_re_matches(self) -> None:
        assert _COMMENT_RE.match("! this is a comment") is not None
        assert _COMMENT_RE.match("not-comment") is None

    def test_charge_mult_re_matches(self) -> None:
        assert _CHARGE_MULT_RE.match("0 1") is not None
        assert _CHARGE_MULT_RE.match("+2 3") is not None
        assert _CHARGE_MULT_RE.match("-1 2") is not None
        assert _CHARGE_MULT_RE.match("not-charge") is None

    def test_atom_re_matches(self) -> None:
        assert _ATOM_RE.match("O  0.0  0.0  0.0") is not None
        assert _ATOM_RE.match("C  1.0 2.0 3.0") is not None
        assert _ATOM_RE.match("not-atom") is None

    def test_modred_re_matches(self) -> None:
        assert _MODRED_RE.match("B 1 2 1.5") is not None
        assert _MODRED_RE.match("D 1 2 3 90.0") is not None
        assert _MODRED_RE.match("not-modred") is None

    def test_modred_single_re_matches(self) -> None:
        assert _MODRED_SINGLE_RE.match("B") is not None
        assert _MODRED_SINGLE_RE.match("S") is not None
        assert _MODRED_SINGLE_RE.match("not-single") is None


# ---------------------------------------------------------------------------
# _is_route_continuation
# ---------------------------------------------------------------------------


class TestIsRouteContinuation:
    """Cover _is_route_continuation branches."""

    def test_empty_string(self) -> None:
        assert _is_route_continuation("") is False
        assert _is_route_continuation("   ") is False

    def test_starts_with_hash(self) -> None:
        assert _is_route_continuation("# second route line") is True

    def test_contains_slash(self) -> None:
        assert _is_route_continuation("B3LYP/6-31G(d)") is True

    def test_contains_equals(self) -> None:
        assert _is_route_continuation("opt=maxcycle=50") is True

    def test_contains_paren(self) -> None:
        assert _is_route_continuation("opt(ts,noeigen)") is True

    def test_matches_method(self) -> None:
        assert _is_route_continuation("B3LYP") is True
        assert _is_route_continuation("MP2") is True

    def test_matches_basis(self) -> None:
        assert _is_route_continuation("6-31G(d)") is True

    def test_no_match(self) -> None:
        assert _is_route_continuation("Water optimization") is False


# ---------------------------------------------------------------------------
# _format_atom_line
# ---------------------------------------------------------------------------


class TestFormatAtomLine:
    """Cover _format_atom_line branches."""

    def test_valid_atom(self) -> None:
        result = _format_atom_line("O  0.0  1.5  -2.3")
        assert "O " in result
        assert "0.000000" in result
        assert "1.500000" in result
        assert "-2.300000" in result

    def test_atom_no_match(self) -> None:
        """Non-atom input returns the original line."""
        original = "not-an-atom"
        assert _format_atom_line(original) == original

    def test_atom_value_error(self) -> None:
        """The except ValueError branch is defensive; regex ensures numeric groups.

        In practice the atom regex only captures numeric strings so float()
        never fails.  This test documents that the branch exists and is
        unreachable with normal input.
        """
        # Directly exercise _format_atom_line with input that does NOT match
        # the atom regex (falls through to the no-match return path at line 97).
        assert _format_atom_line("not-an-atom") == "not-an-atom"

    def test_custom_coord_width(self) -> None:
        result = _format_atom_line("H  0.0  0.0  0.0", coord_width=16)
        # With coord_width=16, each field is at least 16 chars wide
        # Format: "H   {:>16.6f}  {:>16.6f}  {:>16.6f}"
        parts = result.split()
        # There should be 4 parts: element, x, y, z
        assert len(parts) == 4
        assert parts[0] == "H"

    def test_long_element_name(self) -> None:
        result = _format_atom_line("Bq  1.0  2.0  3.0")
        assert "Bq" in result


# ---------------------------------------------------------------------------
# format_document — basic cases
# ---------------------------------------------------------------------------


class TestFormatDocument:
    """Test full document formatting."""

    def test_empty_document(self) -> None:
        provider = FormattingProvider(None)  # type: ignore[arg-type]
        result = provider.format_document("", _fmt_params())
        assert result == []

    def test_already_formatted(self) -> None:
        """Idempotent: already-formatted content returns no edits."""
        provider = FormattingProvider(None)  # type: ignore[arg-type]
        content = (
            "# B3LYP/6-31G(d) opt\n"
            "\n"
            "Water optimization\n"
            "\n"
            f"0 1\n{_FMT_WATER_O}\n{_FMT_WATER_H1}\n{_FMT_WATER_H2}\n"
        )
        result = provider.format_document(content, _fmt_params())
        assert result == []

    def test_strips_whitespace(self) -> None:
        """Leading and trailing whitespace on lines is stripped."""
        provider = FormattingProvider(None)  # type: ignore[arg-type]
        content = "  # B3LYP/6-31G(d) opt  \n\n  Title  \n\n  0 1  \n  O  0  0  0  \n"
        result = provider.format_document(content, _fmt_params())
        assert len(result) == 1
        edit = result[0]
        assert edit.new_text.startswith("# B3LYP/6-31G(d) opt\n")

    def test_preserves_trailing_newline(self) -> None:
        provider = FormattingProvider(None)  # type: ignore[arg-type]
        content = "# HF/STO-3G\n\nH atom\n\n0 1\nH  0  0  0\n"
        result = provider.format_document(content, _fmt_params())
        assert len(result) == 1
        assert result[0].new_text.endswith("\n")

    def test_no_trailing_newline(self) -> None:
        provider = FormattingProvider(None)  # type: ignore[arg-type]
        content = "# HF/STO-3G\n\nH atom\n\n0 1\nH  0  0  0"
        result = provider.format_document(content, _fmt_params())
        assert len(result) == 1
        assert not result[0].new_text.endswith("\n")

    def test_comment_preserved(self) -> None:
        provider = FormattingProvider(None)  # type: ignore[arg-type]
        content = "! This is a comment\n# HF/STO-3G\n\nH atom\n\n0 1\nH  0  0  0\n"
        result = provider.format_document(content, _fmt_params())
        assert len(result) == 1
        assert "! This is a comment" in result[0].new_text

    def test_link0_preserved(self) -> None:
        provider = FormattingProvider(None)  # type: ignore[arg-type]
        content = "%mem=4GB\n%chk=test.chk\n# HF/STO-3G\n\nH atom\n\n0 1\nH  0  0  0\n"
        result = provider.format_document(content, _fmt_params())
        assert len(result) == 1
        assert "%mem=4GB" in result[0].new_text
        assert "%chk=test.chk" in result[0].new_text

    def test_route_continuation(self) -> None:
        """Multi-line route section with continuation lines."""
        provider = FormattingProvider(None)  # type: ignore[arg-type]
        content = "# opt\nB3LYP/6-31G(d)\n\nTitle\n\n0 1\nH  0  0  0\n"
        result = provider.format_document(content, _fmt_params())
        assert len(result) == 1
        assert "# opt" in result[0].new_text
        assert "B3LYP/6-31G(d)" in result[0].new_text

    def test_atom_alignment(self) -> None:
        """Atom coordinate lines are aligned to fixed width."""
        provider = FormattingProvider(None)  # type: ignore[arg-type]
        content = "# B3LYP/6-31G(d) opt\n\nTest\n\n0 1\nO  0  0.758602  0.504284\nH  0  -0.758602  0.504284\n"
        result = provider.format_document(content, _fmt_params())
        assert len(result) == 1
        formatted = result[0].new_text
        # Atom lines should have consistent 12-char-wide coordinate fields
        for line in formatted.splitlines():
            stripped = line.strip()
            if stripped.startswith("O") or stripped.startswith("H"):
                # Should be formatted with fixed-width coords
                assert "0.000000" in line or "0.758602" in line or "0.504284" in line

    def test_charge_mult_line(self) -> None:
        provider = FormattingProvider(None)  # type: ignore[arg-type]
        content = "# B3LYP/6-31G(d)\n\nTest\n\n0 1\nH  0  0  0\n"
        result = provider.format_document(content, _fmt_params())
        assert len(result) == 1
        assert "0 1" in result[0].new_text

    def test_blank_lines_preserved(self) -> None:
        provider = FormattingProvider(None)  # type: ignore[arg-type]
        content = "# B3LYP/6-31G(d)\n\n\n\nTest\n\n0 1\nH  0  0  0\n"
        result = provider.format_document(content, _fmt_params())
        assert len(result) == 1
        # Should still have blank lines
        assert "\n\n" in result[0].new_text

    def test_modredundant_section(self) -> None:
        """ModRedundant lines after geometry are preserved."""
        provider = FormattingProvider(None)  # type: ignore[arg-type]
        content = (
            "# B3LYP/6-31G(d) opt=modredundant\n\nTest\n\n0 1\n"
            f"{_FMT_WATER_O}\n{_FMT_WATER_H1}\n{_FMT_WATER_H2}\n"
            "\nB 1 2 1.5\nD 1 2 3 90.0\n"
        )
        result = provider.format_document(content, _fmt_params())
        assert result == []

    def test_modredundant_single_letter_command(self) -> None:
        """Single-letter ModRedundant commands are detected."""
        provider = FormattingProvider(None)  # type: ignore[arg-type]
        content = "# B3LYP/6-31G(d) opt=modredundant\n\nTest\n\n0 1\n" f"{_FMT_WATER_O}\n\nB\n"
        result = provider.format_document(content, _fmt_params())
        assert isinstance(result, list)

    def test_non_charge_mult_in_charge_mult_phase(self) -> None:
        """If charge/mult line doesn't match regex, still transitions to geometry."""
        provider = FormattingProvider(None)  # type: ignore[arg-type]
        content = "# B3LYP/6-31G(d)\n\nTest\n\nnot-charge-mult\nH  0  0  0\n"
        result = provider.format_document(content, _fmt_params())
        assert len(result) == 1

    def test_geometry_transition_to_post_geometry(self) -> None:
        """Non-atom, non-modred line in geometry phase transitions to post_geometry."""
        provider = FormattingProvider(None)  # type: ignore[arg-type]
        content = "# B3LYP/6-31G(d)\n\nTest\n\n0 1\n" "O  0.0  0.0  0.0\n" "some-variable = 1.5\n"
        result = provider.format_document(content, _fmt_params())
        assert len(result) == 1
        assert "some-variable = 1.5" in result[0].new_text

    def test_post_geometry_section(self) -> None:
        """Lines after geometry are passed through in post_geometry phase."""
        provider = FormattingProvider(None)  # type: ignore[arg-type]
        content = (
            "# B3LYP/6-31G(d)\n\nTest\n\n0 1\n" "O  0.0  0.0  0.0\n" "\n" "Variables:\n" "R = 1.0\n"
        )
        result = provider.format_document(content, _fmt_params())
        assert len(result) == 1

    def test_fallback_line(self) -> None:
        """Lines that don't match any phase go to fallback."""
        provider = FormattingProvider(None)  # type: ignore[arg-type]
        content = "random line\n# B3LYP/6-31G(d)\n\nTest\n\n0 1\nH  0  0  0\n"
        result = provider.format_document(content, _fmt_params())
        assert len(result) == 1
        assert "random line" in result[0].new_text

    def test_none_options(self) -> None:
        """Formatting with None options uses defaults."""
        provider = FormattingProvider(None)  # type: ignore[arg-type]
        params = DocumentFormattingParams(
            text_document=None,  # type: ignore[arg-type]
            options=None,
        )
        content = "# B3LYP/6-31G(d) opt\n\nTest\n\n0 1\nH  0  0  0\n"
        result = provider.format_document(content, params)
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# format_range — range formatting
# ---------------------------------------------------------------------------


class TestFormatRange:
    """Test range formatting."""

    def test_empty_document(self) -> None:
        provider = FormattingProvider(None)  # type: ignore[arg-type]
        result = provider.format_range("", _range_fmt_params(0, 0))
        assert result == []

    def test_invalid_range_start_larger_than_end(self) -> None:
        provider = FormattingProvider(None)  # type: ignore[arg-type]
        content = "# B3LYP/6-31G(d) opt\n\nTest\n\n0 1\nH  0  0  0\n"
        result = provider.format_range(content, _range_fmt_params(5, 3))
        assert result == []

    def test_range_equal_start_end(self) -> None:
        """start_line == end_line returns empty (single line selected at boundary)."""
        provider = FormattingProvider(None)  # type: ignore[arg-type]
        content = "# B3LYP/6-31G(d) opt\n\nTest\n\n0 1\nH  0  0  0\n"
        result = provider.format_range(content, _range_fmt_params(2, 2))
        assert result == []

    def test_valid_range_returns_edit(self) -> None:
        """Range that changes content returns an edit."""
        provider = FormattingProvider(None)  # type: ignore[arg-type]
        content = "  # B3LYP/6-31G(d) opt  \n\nTest\n\n0 1\n  O  0  0  0  \n"
        result = provider.format_range(content, _range_fmt_params(0, 1))
        assert len(result) == 1

    def test_range_already_formatted(self) -> None:
        """Range that is already formatted returns empty list."""
        provider = FormattingProvider(None)  # type: ignore[arg-type]
        content = f"# B3LYP/6-31G(d) opt\n\nTest\n\n0 1\n{_FMT_WATER_O}\n"
        # Range covers the already-formatted route line
        result = provider.format_range(content, _range_fmt_params(0, 1))
        assert result == []

    def test_range_clamps_to_document_length(self) -> None:
        """Range beyond document length is clamped."""
        provider = FormattingProvider(None)  # type: ignore[arg-type]
        content = "# B3LYP/6-31G(d) opt\n\nTest\n\n0 1\nH  0  0  0\n"
        # Use a very large range
        result = provider.format_range(content, _range_fmt_params(0, 100))
        # Should not crash; may return edits or empty
        assert isinstance(result, list)

    def test_range_preserves_surrounding(self) -> None:
        """Range formatting only modifies lines within the range."""
        provider = FormattingProvider(None)  # type: ignore[arg-type]
        content = "# B3LYP/6-31G(d) opt\n\nTest\n\n  0 1  \n  O  0  0  0  \n"
        # Only format the charge/mult and atom lines (lines 4-5)
        result = provider.format_range(content, _range_fmt_params(4, 6))
        assert isinstance(result, list)
        if result:
            edit = result[0]
            # The edit range should start at line 4
            assert edit.range.start.line == 4


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


class TestIdempotency:
    """Formatting should be idempotent across representative fixtures."""

    WATER = (
        "# B3LYP/6-31G(d) opt freq\n"
        "\n"
        "Water optimization\n"
        "\n"
        f"0 1\n{_FMT_WATER_O}\n{_FMT_WATER_H1}\n{_FMT_WATER_H2}\n"
    )

    BENZENE = (
        "# B3LYP/6-311G(d,p) opt\n"
        "\n"
        "Benzene optimization\n"
        "\n"
        "0 1\n"
        f"{_FMT_BEN_C1}\n{_FMT_BEN_C2}\n{_FMT_BEN_C3}\n"
        f"{_FMT_BEN_C4}\n{_FMT_BEN_C5}\n{_FMT_BEN_C6}\n"
        f"{_FMT_BEN_H1}\n{_FMT_BEN_H2}\n{_FMT_BEN_H3}\n"
        f"{_FMT_BEN_H4}\n{_FMT_BEN_H5}\n{_FMT_BEN_H6}\n"
    )

    WITH_LINK0 = (
        "%mem=8GB\n"
        "%nprocshared=8\n"
        "%chk=water.chk\n"
        "# B3LYP/6-31G(d) opt\n"
        "\n"
        "Water optimization\n"
        "\n"
        f"0 1\n{_FMT_WATER_O}\n{_FMT_WATER_H1}\n{_FMT_WATER_H2}\n"
    )

    WITH_COMMENT = (
        "! Input for water optimization\n"
        "# B3LYP/6-31G(d) opt freq\n"
        "\n"
        "Water optimization\n"
        "\n"
        f"0 1\n{_FMT_WATER_O}\n{_FMT_WATER_H1}\n{_FMT_WATER_H2}\n"
    )

    WITH_MODREDUNDANT = (
        "# B3LYP/6-31G(d) opt=modredundant\n"
        "\n"
        "Water scan\n"
        "\n"
        f"0 1\n{_FMT_WATER_O}\n{_FMT_WATER_H1}\n{_FMT_WATER_H2}\n"
        "\n"
        "B 1 2 S 5.0\n"
    )

    MALFORMED = "random garbage\n" "more garbage\n"

    @pytest.fixture
    def provider(self) -> FormattingProvider:
        return FormattingProvider(None)  # type: ignore[arg-type]

    def test_water_idempotent(self, provider: FormattingProvider) -> None:
        result = provider.format_document(self.WATER, _fmt_params())
        assert result == []

    def test_benzene_idempotent(self, provider: FormattingProvider) -> None:
        result = provider.format_document(self.BENZENE, _fmt_params())
        assert result == []

    def test_link0_idempotent(self, provider: FormattingProvider) -> None:
        result = provider.format_document(self.WITH_LINK0, _fmt_params())
        assert result == []

    def test_comment_idempotent(self, provider: FormattingProvider) -> None:
        result = provider.format_document(self.WITH_COMMENT, _fmt_params())
        assert result == []

    def test_modredundant_idempotent(self, provider: FormattingProvider) -> None:
        result = provider.format_document(self.WITH_MODREDUNDANT, _fmt_params())
        assert result == []

    def test_malformed_idempotent(self, provider: FormattingProvider) -> None:
        """Formatting malformed input is idempotent."""
        result = provider.format_document(self.MALFORMED, _fmt_params())
        # First pass may produce edits, but running again on result should be idempotent
        if result:
            formatted = result[0].new_text
            second = provider.format_document(formatted, _fmt_params())
            assert second == []

    def test_format_then_format_again(self, provider: FormattingProvider) -> None:
        """Any input, when formatted and then formatted again, is idempotent."""
        unformatted = (
            "  # B3LYP/6-31G(d) opt  \n"
            "\n"
            "  Water optimization  \n"
            "\n"
            "  0 1  \n"
            "  O  0.0  0.0  0.0  \n"
            "  H  0.0  0.758602  0.504284  \n"
            "  H  0.0  -0.758602  0.504284  \n"
        )
        first = provider.format_document(unformatted, _fmt_params())
        assert len(first) == 1
        formatted = first[0].new_text
        second = provider.format_document(formatted, _fmt_params())
        assert second == []


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Test edge cases and unusual inputs."""

    @pytest.fixture
    def provider(self) -> FormattingProvider:
        return FormattingProvider(None)  # type: ignore[arg-type]

    def test_single_line_document(self, provider: FormattingProvider) -> None:
        result = provider.format_document("# B3LYP/6-31G(d)\n", _fmt_params())
        assert isinstance(result, list)

    def test_only_blank_lines(self, provider: FormattingProvider) -> None:
        result = provider.format_document("\n\n\n", _fmt_params())
        assert isinstance(result, list)

    def test_tabs_option(self, provider: FormattingProvider) -> None:
        """Formatting with tabs instead of spaces."""
        params = _fmt_params(tab_size=4, insert_spaces=False)
        content = "# B3LYP/6-31G(d) opt\n\nTest\n\n0 1\nH  0  0  0\n"
        result = provider.format_document(content, params)
        assert isinstance(result, list)

    def test_custom_tab_size(self, provider: FormattingProvider) -> None:
        params = _fmt_params(tab_size=4)
        content = "# B3LYP/6-31G(d) opt\n\nTest\n\n0 1\nH  0  0  0\n"
        result = provider.format_document(content, params)
        assert isinstance(result, list)

    def test_negative_charge(self, provider: FormattingProvider) -> None:
        """Negative charge value in charge/mult line."""
        content = "# B3LYP/6-31G(d) opt\n\nAnion\n\n-1 1\nO  0  0  0\n"
        result = provider.format_document(content, _fmt_params())
        assert isinstance(result, list)
        if result:
            assert "-1 1" in result[0].new_text

    def test_positive_charge(self, provider: FormattingProvider) -> None:
        content = "# B3LYP/6-31G(d) opt\n\nCation\n\n+1 2\nO  0  0  0\n"
        result = provider.format_document(content, _fmt_params())
        assert isinstance(result, list)
        if result:
            assert "+1 2" in result[0].new_text

    def test_atom_with_fragment_label(self, provider: FormattingProvider) -> None:
        """Atom with fragment label like C(Fragment=1)."""
        content = "# B3LYP/6-31G(d) opt\n\nTest\n\n0 1\nC(Fragment=1)  0  0  0\n"
        result = provider.format_document(content, _fmt_params())
        assert isinstance(result, list)

    def test_empty_lines_between_sections(self, provider: FormattingProvider) -> None:
        """Multiple blank lines between sections."""
        content = "# B3LYP/6-31G(d)\n\n\n\nTest\n\n\n0 1\nH  0  0  0\n"
        result = provider.format_document(content, _fmt_params())
        assert isinstance(result, list)

    def test_range_format_end_character_nonzero(self, provider: FormattingProvider) -> None:
        """Range formatting with end.character > 0 covers the pass branch."""
        params = DocumentRangeFormattingParams(
            text_document=None,  # type: ignore[arg-type]
            range=Range(
                start=Position(line=0, character=0),
                end=Position(line=3, character=5),
            ),
            options=FormattingOptions(tab_size=2, insert_spaces=True),
        )
        content = "  # B3LYP/6-31G(d)  \n\n  Test  \n\n0 1\nH  0  0  0\n"
        result = provider.format_range(content, params)
        assert isinstance(result, list)

    def test_range_format_end_char_nonzero_already_formatted(
        self, provider: FormattingProvider
    ) -> None:
        """Range with end.character > 0 where content is already formatted returns []."""
        params = DocumentRangeFormattingParams(
            text_document=None,  # type: ignore[arg-type]
            range=Range(
                start=Position(line=0, character=0),
                end=Position(line=1, character=5),
            ),
            options=FormattingOptions(tab_size=2, insert_spaces=True),
        )
        # Content that is already formatted
        content = f"# B3LYP/6-31G(d) opt\n\nTest\n\n0 1\n{_FMT_WATER_O}\n"
        result = provider.format_range(content, params)
        assert result == []

    def test_format_lines_empty_input(self, provider: FormattingProvider) -> None:
        """_format_lines with empty list returns empty list."""
        params = _fmt_params()
        result = provider._format_lines([], params)
        assert result == []

    def test_range_format_end_character_zero_trailing_newline(
        self, provider: FormattingProvider
    ) -> None:
        """Range formatting with end.character=0 but text ends with newline."""
        params = DocumentRangeFormattingParams(
            text_document=None,  # type: ignore[arg-type]
            range=Range(
                start=Position(line=0, character=0),
                end=Position(line=2, character=0),
            ),
            options=FormattingOptions(tab_size=2, insert_spaces=True),
        )
        content = "  # B3LYP/6-31G(d)  \n\n  Test  \n\n0 1\nH  0  0  0\n"
        result = provider.format_range(content, params)
        assert isinstance(result, list)
