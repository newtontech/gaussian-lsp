"""Tests for the CodeActionProvider feature."""

from __future__ import annotations

import pytest
from lsprotocol.types import (
    CodeActionKind,
    Diagnostic,
    DiagnosticSeverity,
    Position,
    Range,
)

from gaussian_lsp.features.code_actions import CodeActionProvider


@pytest.fixture
def provider() -> CodeActionProvider:
    """Create a CodeActionProvider instance for testing."""
    return CodeActionProvider()


def _diag(line: int, message: str, char: int = 0, length: int = 10) -> Diagnostic:
    """Create a minimal diagnostic for testing."""
    return Diagnostic(
        range=Range(
            start=Position(line=line, character=char),
            end=Position(line=line, character=char + length),
        ),
        message=message,
        severity=DiagnosticSeverity.Error,
        source="gaussian-lsp",
    )


def _apply_action(source: str, action: CodeAction) -> str:
    """Apply the text edits from a code action to the source and return the result."""
    lines = source.split("\n")
    changes = action.edit.changes.get("document", [])
    # Sort changes in reverse order so earlier edits don't shift later ones.
    changes_sorted = sorted(changes, key=lambda e: (e.range.start.line, e.range.start.character), reverse=True)
    for change in changes_sorted:
        start_line = change.range.start.line
        start_char = change.range.start.character
        end_line = change.range.end.line
        end_char = change.range.end.character

        before = lines[:start_line]
        # Partial line before the edit
        prefix = lines[start_line][:start_char] if start_line < len(lines) else ""
        # Partial line after the edit
        suffix = lines[end_line][end_char:] if end_line < len(lines) else ""
        after = lines[end_line + 1:] if end_line < len(lines) else []

        new_lines = (prefix + change.new_text + suffix).split("\n")
        lines = before + new_lines + after

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Provider basics
# ---------------------------------------------------------------------------


class TestCodeActionProviderInit:
    """Test provider instantiation."""

    def test_provider_exists(self, provider: CodeActionProvider) -> None:
        """Provider can be created."""
        assert provider is not None

    def test_no_actions_for_empty_diagnostics(self, provider: CodeActionProvider) -> None:
        """Empty diagnostics list produces only general actions."""
        actions = provider.get_code_actions("# HF/STO-3G\n\nTitle\n\n0 1\nH 0 0 0\n", [])
        # Only general actions (e.g. add %chk), no diagnostic-bound actions.
        for action in actions:
            assert action.diagnostics is None or len(action.diagnostics) == 0


# ---------------------------------------------------------------------------
# Route section fixes
# ---------------------------------------------------------------------------


class TestRouteHashFix:
    """Test adding missing # prefix to route lines."""

    def test_adds_hash_to_route(self, provider: CodeActionProvider) -> None:
        """Route line without # gets a # prefix."""
        source = "B3LYP/6-31G(d) opt\n\nTitle\n\n0 1\nH 0.0 0.0 0.0\n"
        diag = _diag(0, "Route section must start with #")
        actions = provider.get_code_actions(source, [diag])

        assert len(actions) >= 1
        action = actions[0]
        assert "Add '#' prefix" in action.title
        result = _apply_action(source, action)
        assert result.startswith("# B3LYP/6-31G(d) opt")

    def test_missing_route_section(self, provider: CodeActionProvider) -> None:
        """Missing route section diagnostic also triggers hash fix."""
        source = "B3LYP/6-31G(d)\n\nTitle\n\n0 1\nH 0.0 0.0 0.0\n"
        diag = _diag(0, "Missing route section (must start with #)")
        actions = provider.get_code_actions(source, [diag])

        assert len(actions) >= 1
        assert "Add '#' prefix" in actions[0].title


class TestRouteTypoFix:
    """Test route keyword typo corrections."""

    def test_fix_optimize_to_opt(self, provider: CodeActionProvider) -> None:
        """'optimize' is replaced with 'opt'."""
        source = "# B3LYP/6-31G(d) optimize\n\nTitle\n\n0 1\nH 0 0 0\n"
        diag = _diag(0, "Use opt instead of optimize.")
        actions = provider.get_code_actions(source, [diag])

        assert len(actions) >= 1
        action = actions[0]
        assert "optimize" in action.title.lower() or "opt" in action.title.lower()
        result = _apply_action(source, action)
        assert "opt" in result.lower()
        assert "optimize" not in result.lower()

    def test_fix_freqency_to_freq(self, provider: CodeActionProvider) -> None:
        """'freqency' is replaced with 'freq'."""
        source = "# B3LYP/6-31G(d) freqency\n\nTitle\n\n0 1\nH 0 0 0\n"
        diag = _diag(0, "Use freq instead of freqency.")
        actions = provider.get_code_actions(source, [diag])

        assert len(actions) >= 1
        result = _apply_action(source, actions[0])
        assert "freq" in result.lower()
        assert "freqency" not in result.lower()

    def test_fix_631g_to_631g(self, provider: CodeActionProvider) -> None:
        """'631G' is replaced with '6-31G'."""
        source = "# B3LYP/631G\n\nTitle\n\n0 1\nH 0 0 0\n"
        diag = _diag(0, "Did you mean 6-31G?")
        actions = provider.get_code_actions(source, [diag])

        assert len(actions) >= 1
        result = _apply_action(source, actions[0])
        assert "6-31G" in result
        assert "631G" not in result

    def test_fix_m06_2x(self, provider: CodeActionProvider) -> None:
        """'M06-2X' is replaced with 'M062X'."""
        source = "# M06-2X/6-31G(d)\n\nTitle\n\n0 1\nH 0 0 0\n"
        diag = _diag(0, "Use M062X instead of M06-2X.")
        actions = provider.get_code_actions(source, [diag])

        assert len(actions) >= 1
        result = _apply_action(source, actions[0])
        assert "M062X" in result


# ---------------------------------------------------------------------------
# Blank line fixes
# ---------------------------------------------------------------------------


class TestBlankLineFix:
    """Test inserting missing blank lines between sections."""

    def test_insert_blank_after_route(self, provider: CodeActionProvider) -> None:
        """Missing blank line after route section gets inserted."""
        source = "# B3LYP/6-31G(d)\nTitle\n0 1\nH 0 0 0\n"
        diag = _diag(1, "Missing blank line after route section before the title.")
        actions = provider.get_code_actions(source, [diag])

        assert len(actions) >= 1
        action = actions[0]
        assert "blank line" in action.title.lower()
        result = _apply_action(source, action)
        lines = result.split("\n")
        # Line after route should now be blank.
        assert lines[1].strip() == ""

    def test_insert_blank_after_title(self, provider: CodeActionProvider) -> None:
        """Missing blank line after title section gets inserted."""
        source = "# B3LYP/6-31G(d)\n\nTitle\n0 1\nH 0 0 0\n"
        diag = _diag(3, "Missing blank line after title section before charge/multiplicity.")
        actions = provider.get_code_actions(source, [diag])

        assert len(actions) >= 1
        action = actions[0]
        assert "blank line" in action.title.lower()
        result = _apply_action(source, action)
        lines = result.split("\n")
        # There should be a blank line before charge/mult.
        assert any(line.strip() == "" for line in lines[2:4])


# ---------------------------------------------------------------------------
# Charge/multiplicity fixes
# ---------------------------------------------------------------------------


class TestChargeMultFix:
    """Test charge/multiplicity corrections."""

    def test_fix_invalid_charge_mult(self, provider: CodeActionProvider) -> None:
        """Invalid charge/multiplicity line is replaced with '0 1'."""
        source = "# HF/STO-3G\n\nTitle\n\n0 singlet\nH 0.0 0.0 0.0\n"
        diag = _diag(4, "Invalid charge/multiplicity line; use two integers like '0 1'.")
        actions = provider.get_code_actions(source, [diag])

        assert len(actions) >= 1
        action = actions[0]
        assert "0 1" in action.title
        result = _apply_action(source, action)
        assert "0 1" in result

    def test_insert_missing_charge_mult(self, provider: CodeActionProvider) -> None:
        """Missing charge/multiplicity line gets inserted."""
        source = "# HF/STO-3G\n\nTitle\n\nH 0.0 0.0 0.0\n"
        diag = _diag(4, "Missing charge/multiplicity line before geometry; add a line like '0 1'.")
        actions = provider.get_code_actions(source, [diag])

        assert len(actions) >= 1
        action = actions[0]
        assert "0 1" in action.title
        result = _apply_action(source, action)
        assert "0 1" in result


class TestElectronParityFix:
    """Test multiplicity toggle for electron parity mismatches."""

    def test_toggle_singlet_to_doublet(self, provider: CodeActionProvider) -> None:
        """Singlet (1) is toggled to doublet (2) when parity mismatches."""
        source = "# HF/STO-3G\n\nH radical\n\n0 1\nH 0.0 0.0 0.0\n"
        diag = _diag(4, "Charge/multiplicity electron count parity mismatch; check total electrons and spin multiplicity.")
        actions = provider.get_code_actions(source, [diag])

        assert len(actions) >= 1
        action = actions[0]
        assert "2" in action.title
        result = _apply_action(source, action)
        assert "0 2" in result

    def test_toggle_doublet_to_singlet(self, provider: CodeActionProvider) -> None:
        """Doublet (2) is toggled to singlet (1) when parity mismatches."""
        source = "# HF/STO-3G\n\nH2\n\n0 2\nH 0 0 0\nH 0 0 0.7\n"
        diag = _diag(4, "Charge/multiplicity electron count parity mismatch;")
        actions = provider.get_code_actions(source, [diag])

        assert len(actions) >= 1
        action = actions[0]
        assert "1" in action.title
        result = _apply_action(source, action)
        assert "0 1" in result


# ---------------------------------------------------------------------------
# Link0 fixes
# ---------------------------------------------------------------------------


class TestLink0Fix:
    """Test Link0 command value fixes."""

    def test_fix_empty_chk(self, provider: CodeActionProvider) -> None:
        """Empty %chk value gets a default."""
        source = "%chk=\n# HF/STO-3G\n\nTitle\n\n0 1\nH 0 0 0\n"
        diag = _diag(0, "%chk must include a non-empty value.")
        actions = provider.get_code_actions(source, [diag])

        assert len(actions) >= 1
        action = actions[0]
        assert "molecule.chk" in action.title
        result = _apply_action(source, action)
        assert "%chk=molecule.chk" in result

    def test_fix_mem_value(self, provider: CodeActionProvider) -> None:
        """Invalid %mem value gets replaced with '4GB'."""
        source = "%mem=abc\n# HF/STO-3G\n\nTitle\n\n0 1\nH 0 0 0\n"
        diag = _diag(0, "%mem value should include a positive number and optional unit like MB or GB.")
        actions = provider.get_code_actions(source, [diag])

        assert len(actions) >= 1
        action = actions[0]
        assert "4GB" in action.title
        result = _apply_action(source, action)
        assert "%mem=4GB" in result

    def test_fix_nproc_value(self, provider: CodeActionProvider) -> None:
        """Invalid %nproc value gets replaced with '4'."""
        source = "%nproc=0\n# HF/STO-3G\n\nTitle\n\n0 1\nH 0 0 0\n"
        diag = _diag(0, "%nproc must be a positive integer.")
        actions = provider.get_code_actions(source, [diag])

        assert len(actions) >= 1
        action = actions[0]
        assert "4" in action.title
        result = _apply_action(source, action)
        assert "%nproc=4" in result

    def test_fix_nprocshared_non_numeric(self, provider: CodeActionProvider) -> None:
        """Non-numeric %nprocshared value gets replaced."""
        source = "%nprocshared=two\n# HF/STO-3G\n\nTitle\n\n0 1\nH 0 0 0\n"
        diag = _diag(0, "%nprocshared must be a positive integer.")
        actions = provider.get_code_actions(source, [diag])

        assert len(actions) >= 1
        result = _apply_action(source, actions[0])
        assert "%nprocshared=4" in result


# ---------------------------------------------------------------------------
# SP/OPT conflict fix
# ---------------------------------------------------------------------------


class TestSPOptConflict:
    """Test SP/OPT mutual exclusion fix."""

    def test_removes_sp(self, provider: CodeActionProvider) -> None:
        """SP is removed when both SP and OPT are present."""
        source = "# SP OPT B3LYP/6-31G(d)\n\nTitle\n\n0 1\nH 0 0 0\n"
        diag = _diag(0, "SP and OPT are mutually exclusive job types.")
        actions = provider.get_code_actions(source, [diag])

        assert len(actions) >= 1
        action = actions[0]
        assert "SP" in action.title
        result = _apply_action(source, action)
        assert "SP" not in result.split("\n")[0]
        assert "OPT" in result.split("\n")[0]


# ---------------------------------------------------------------------------
# General actions
# ---------------------------------------------------------------------------


class TestGeneralActions:
    """Test non-diagnostic-bound general code actions."""

    def test_add_missing_chk(self, provider: CodeActionProvider) -> None:
        """Source without %chk gets an 'Add %chk' action."""
        source = "# HF/STO-3G\n\nTitle\n\n0 1\nH 0 0 0\n"
        actions = provider.get_code_actions(source, [])

        add_chk = [a for a in actions if "%chk" in a.title]
        assert len(add_chk) >= 1
        result = _apply_action(source, add_chk[0])
        assert result.startswith("%chk=molecule.chk")

    def test_no_add_chk_when_present(self, provider: CodeActionProvider) -> None:
        """Source with %chk does not get an 'Add %chk' action."""
        source = "%chk=test.chk\n# HF/STO-3G\n\nTitle\n\n0 1\nH 0 0 0\n"
        actions = provider.get_code_actions(source, [])

        add_chk = [a for a in actions if "Add '%chk" in a.title]
        assert len(add_chk) == 0


# ---------------------------------------------------------------------------
# Multiple diagnostics
# ---------------------------------------------------------------------------


class TestMultipleDiagnostics:
    """Test handling of multiple simultaneous diagnostics."""

    def test_produces_actions_for_each_diagnostic(self, provider: CodeActionProvider) -> None:
        """Multiple diagnostics produce multiple code actions."""
        source = "B3LYP/631G optimize\nTitle\n0 1\nH 0 0 0\n"
        diags = [
            _diag(0, "Route section must start with #"),
            _diag(0, "Use opt instead of optimize."),
        ]
        actions = provider.get_code_actions(source, diags)

        assert len(actions) >= 2

    def test_action_kind_is_quickfix(self, provider: CodeActionProvider) -> None:
        """All diagnostic-bound actions are QuickFix kind."""
        source = "# B3LYP/6-31G(d) optimize\n\nTitle\n\n0 1\nH 0 0 0\n"
        diag = _diag(0, "Use opt instead of optimize.")
        actions = provider.get_code_actions(source, [diag])

        for action in actions:
            if action.diagnostics:
                assert action.kind == CodeActionKind.QuickFix


# ---------------------------------------------------------------------------
# Before/after edit verification
# ---------------------------------------------------------------------------


class TestEditApplication:
    """Verify that edits produce the expected before/after content."""

    @pytest.mark.parametrize(
        ("source", "message", "expected_substring"),
        [
            (
                "B3LYP/6-31G(d)\n\nTitle\n\n0 1\nH 0 0 0\n",
                "Route section must start with #",
                "# B3LYP/6-31G(d)",
            ),
            (
                "# B3LYP/6-31G(d) optimize\n\nTitle\n\n0 1\nH 0 0 0\n",
                "Use opt instead of optimize.",
                "opt",
            ),
            (
                "# B3LYP/631G\n\nTitle\n\n0 1\nH 0 0 0\n",
                "Did you mean 6-31G?",
                "6-31G",
            ),
            (
                "# B3LYP/6-31G(d)\nTitle\n0 1\nH 0 0 0\n",
                "Missing blank line after route section",
                "",
            ),
        ],
        ids=[
            "add-hash-prefix",
            "fix-optimize-typo",
            "fix-631g-typo",
            "insert-blank-line",
        ],
    )
    def test_edit_produces_expected_result(
        self,
        provider: CodeActionProvider,
        source: str,
        message: str,
        expected_substring: str,
    ) -> None:
        """Each quick fix produces the expected textual change."""
        diag = _diag(0, message)
        actions = provider.get_code_actions(source, [diag])

        assert len(actions) >= 1
        result = _apply_action(source, actions[0])
        assert expected_substring in result


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_source_no_diagnostics(self, provider: CodeActionProvider) -> None:
        """Empty source with no diagnostics returns general actions."""
        actions = provider.get_code_actions("", [])
        # Should at least have the %chk suggestion.
        assert len(actions) >= 1

    def test_unknown_diagnostic_no_action(self, provider: CodeActionProvider) -> None:
        """Diagnostics with no matching fix produce no diagnostic-bound action."""
        source = "# HF/STO-3G\n\nTitle\n\n0 1\nH 0 0 0\n"
        diag = _diag(0, "Something completely unrelated to anything.")
        actions = provider.get_code_actions(source, [diag])

        # Only general actions, no diagnostic-bound ones.
        diag_bound = [a for a in actions if a.diagnostics and len(a.diagnostics) > 0]
        assert len(diag_bound) == 0

    def test_line_out_of_bounds_graceful(self, provider: CodeActionProvider) -> None:
        """Diagnostic with line number beyond source length doesn't crash."""
        source = "# HF/STO-3G\n\nTitle\n\n0 1\nH 0 0 0\n"
        diag = _diag(100, "Route section must start with #")
        # Should not raise.
        actions = provider.get_code_actions(source, [diag])
        assert isinstance(actions, list)

    def test_method_typo_suggests_close_match(self, provider: CodeActionProvider) -> None:
        """Unrecognizable method triggers a suggestion action."""
        source = "# B3LY/6-31G(d)\n\nTitle\n\n0 1\nH 0 0 0\n"
        diag = _diag(0, "No recognizable calculation method found")
        actions = provider.get_code_actions(source, [diag])

        if actions:
            result = _apply_action(source, actions[0])
            assert "B3LYP" in result

    def test_basis_typo_suggests_close_match(self, provider: CodeActionProvider) -> None:
        """Unrecognizable basis set triggers a suggestion action."""
        source = "# HF/STO3G\n\nTitle\n\n0 1\nH 0 0 0\n"
        diag = _diag(0, "No recognizable basis set (add one or use Gen)")
        actions = provider.get_code_actions(source, [diag])

        if actions:
            result = _apply_action(source, actions[0])
            assert "STO-3G" in result
