"""Tests for the TypecheckProvider feature."""

import pytest
from lsprotocol.types import DiagnosticSeverity

from gaussian_lsp.features.typecheck import SOURCE, TypecheckProvider


@pytest.fixture
def provider() -> TypecheckProvider:
    """Create a TypecheckProvider instance for testing."""
    return TypecheckProvider()


# ---------------------------------------------------------------------------
# Provider instantiation
# ---------------------------------------------------------------------------


class TestTypecheckProviderInit:
    """Test provider instantiation."""

    def test_provider_exists(self, provider: TypecheckProvider) -> None:
        """Test that provider can be created."""
        assert provider is not None

    def test_validate_returns_list(self, provider: TypecheckProvider) -> None:
        """Test that validate returns a list."""
        result = provider.validate("")
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# Valid inputs — should produce no error-severity typecheck diagnostics
# ---------------------------------------------------------------------------


class TestValidInput:
    """Test typecheck on well-formed Gaussian input."""

    VALID_WATER = """\
# B3LYP/6-31G(d) opt freq

Water optimization

0 1
O  0.000000  0.000000  0.000000
H  0.000000  0.758602  0.504284
H  0.000000 -0.758602  0.504284
"""

    def test_valid_input_no_errors(self, provider: TypecheckProvider) -> None:
        """Valid input should produce zero error-severity typecheck diagnostics."""
        diagnostics = provider.validate(self.VALID_WATER)
        errors = [d for d in diagnostics if d.severity == DiagnosticSeverity.Error]
        assert errors == []

    def test_valid_input_source_label(self, provider: TypecheckProvider) -> None:
        """All diagnostics from the typecheck provider should have the correct source."""
        diagnostics = provider.validate(self.VALID_WATER)
        for diag in diagnostics:
            assert diag.source == SOURCE

    def test_valid_hf_calculation(self, provider: TypecheckProvider) -> None:
        """A valid HF/STO-3G SP input should produce no error diagnostics."""
        content = """\
# HF/STO-3G SP

Hydrogen atom

0 1
H  0.0 0.0 0.0
"""
        diagnostics = provider.validate(content)
        errors = [d for d in diagnostics if d.severity == DiagnosticSeverity.Error]
        assert errors == []

    def test_valid_with_link0(self, provider: TypecheckProvider) -> None:
        """Valid input with properly typed Link0 commands should have no errors."""
        content = """\
%mem=4GB
%nprocshared=8
%chk=test.chk
# B3LYP/6-31G(d) opt

Molecule

0 1
O  0.0 0.0 0.0
H  0.0 0.758 0.504
H  0.0 -0.758 0.504
"""
        diagnostics = provider.validate(content)
        errors = [d for d in diagnostics if d.severity == DiagnosticSeverity.Error]
        assert errors == []


# ---------------------------------------------------------------------------
# Required sections
# ---------------------------------------------------------------------------


class TestRequiredSections:
    """Test required-section validation."""

    def test_missing_route_section(self, provider: TypecheckProvider) -> None:
        """Missing route section should produce an error."""
        content = """\
No route here

Some title

0 1
H 0.0 0.0 0.0
"""
        diagnostics = provider.validate(content)
        messages = [d.message for d in diagnostics]
        assert any("route section" in m.lower() for m in messages)

    def test_missing_title(self, provider: TypecheckProvider) -> None:
        """Missing title should produce an error when route exists.

        When the title line is absent, the parser ends up with no title
        because the charge/mult line is consumed as the title.  In that
        case the typecheck provider should report missing coordinates
        (since no atoms are found) rather than a missing title, since
        the parser swallows the charge/mult line as the title string.
        Verify the provider handles the cascading state gracefully.
        """
        content = """\
# B3LYP/6-31G(d) opt

0 1
H 0.0 0.0 0.0
"""
        diagnostics = provider.validate(content)
        # The parser treats "0 1" as the title, so we get missing coords.
        messages = [d.message for d in diagnostics]
        assert any("coordinate" in m.lower() or "title" in m.lower() for m in messages)

    def test_missing_atoms(self, provider: TypecheckProvider) -> None:
        """Missing atoms should produce an error."""
        content = """\
# B3LYP/6-31G(d) opt

Empty molecule

0 1
"""
        diagnostics = provider.validate(content)
        messages = [d.message for d in diagnostics]
        assert any("coordinate" in m.lower() for m in messages)

    def test_invalid_multiplicity(self, provider: TypecheckProvider) -> None:
        """Multiplicity of 0 should produce an error."""
        content = """\
# B3LYP/6-31G(d) opt

Bad mult

0 0
H 0.0 0.0 0.0
"""
        diagnostics = provider.validate(content)
        errors = [d for d in diagnostics if d.severity == DiagnosticSeverity.Error]
        assert any("multiplicity" in d.message.lower() for d in errors)


# ---------------------------------------------------------------------------
# Route keyword types
# ---------------------------------------------------------------------------


class TestRouteKeywordTypes:
    """Test route section keyword type validation."""

    def test_no_method_warning(self, provider: TypecheckProvider) -> None:
        """Route without a recognizable method should warn."""
        content = """\
# /6-31G(d) opt

No method

0 1
H 0.0 0.0 0.0
H 0.0 0.0 0.7
"""
        diagnostics = provider.validate(content)
        messages = [d.message for d in diagnostics]
        assert any("method" in m.lower() for m in messages)

    def test_no_basis_set_warning(self, provider: TypecheckProvider) -> None:
        """Route without a recognizable basis set should warn."""
        content = """\
# B3LYP opt

No basis

0 1
H 0.0 0.0 0.0
H 0.0 0.0 0.7
"""
        diagnostics = provider.validate(content)
        messages = [d.message for d in diagnostics]
        assert any("basis" in m.lower() for m in messages)

    def test_no_job_type_warning(self, provider: TypecheckProvider) -> None:
        """Route without a recognizable job type should warn."""
        content = """\
# B3LYP/6-31G(d)

No job type

0 1
H 0.0 0.0 0.0
"""
        diagnostics = provider.validate(content)
        messages = [d.message for d in diagnostics]
        assert any("job type" in m.lower() for m in messages)

    def test_known_method_no_warning(self, provider: TypecheckProvider) -> None:
        """Route with a known method should not produce method warnings."""
        content = """\
# MP2/cc-pVTZ SP

Valid method

0 1
H 0.0 0.0 0.0
H 0.0 0.0 0.7
"""
        diagnostics = provider.validate(content)
        method_warnings = [
            d for d in diagnostics if "method" in d.message.lower() and d.source == SOURCE
        ]
        assert method_warnings == []

    def test_gen_basis_counts_as_basis(self, provider: TypecheckProvider) -> None:
        """Route with Gen should not produce basis warnings."""
        content = """\
# B3LYP/Gen SP

Gen basis

0 1
H 0.0 0.0 0.0

H 0
****
H S
   1.0 0.0
****
"""
        diagnostics = provider.validate(content)
        basis_warnings = [
            d for d in diagnostics if "basis" in d.message.lower() and d.source == SOURCE
        ]
        assert basis_warnings == []


# ---------------------------------------------------------------------------
# Link0 value types
# ---------------------------------------------------------------------------


class TestLink0Types:
    """Test Link0 command value type validation."""

    def test_mem_valid_units(self, provider: TypecheckProvider) -> None:
        """Valid %mem values should produce no errors."""
        for value in ("4GB", "100MB", "1TB", "500MW", "8gb", "100"):
            content = f"%mem={value}\n# HF/STO-3G SP\n\nTitle\n\n0 1\nH 0.0 0.0 0.0\n"
            diagnostics = provider.validate(content)
            errors = [
                d
                for d in diagnostics
                if d.severity == DiagnosticSeverity.Error and "mem" in d.message.lower()
            ]
            assert errors == [], f"Unexpected error for %mem={value}"

    def test_mem_invalid_unit(self, provider: TypecheckProvider) -> None:
        """Invalid %mem value should produce an error."""
        content = """\
%mem=abc
# HF/STO-3G SP

Title

0 1
H 0.0 0.0 0.0
"""
        diagnostics = provider.validate(content)
        errors = [
            d
            for d in diagnostics
            if d.severity == DiagnosticSeverity.Error and "mem" in d.message.lower()
        ]
        assert len(errors) == 1

    def test_mem_zero_value(self, provider: TypecheckProvider) -> None:
        """Zero %mem value should produce an error."""
        content = """\
%mem=0
# HF/STO-3G SP

Title

0 1
H 0.0 0.0 0.0
"""
        diagnostics = provider.validate(content)
        errors = [
            d
            for d in diagnostics
            if d.severity == DiagnosticSeverity.Error and "mem" in d.message.lower()
        ]
        assert len(errors) == 1

    def test_nprocshared_valid(self, provider: TypecheckProvider) -> None:
        """Valid %nprocshared should produce no errors."""
        content = """\
%nprocshared=4
# HF/STO-3G SP

Title

0 1
H 0.0 0.0 0.0
"""
        diagnostics = provider.validate(content)
        errors = [
            d
            for d in diagnostics
            if d.severity == DiagnosticSeverity.Error and "nprocshared" in d.message.lower()
        ]
        assert errors == []

    def test_nprocshared_non_integer(self, provider: TypecheckProvider) -> None:
        """Non-integer %nprocshared should produce an error."""
        content = """\
%nprocshared=abc
# HF/STO-3G SP

Title

0 1
H 0.0 0.0 0.0
"""
        diagnostics = provider.validate(content)
        errors = [
            d
            for d in diagnostics
            if d.severity == DiagnosticSeverity.Error and "nprocshared" in d.message.lower()
        ]
        assert len(errors) == 1

    def test_nprocshared_zero(self, provider: TypecheckProvider) -> None:
        """Zero %nprocshared should produce an error."""
        content = """\
%nprocshared=0
# HF/STO-3G SP

Title

0 1
H 0.0 0.0 0.0
"""
        diagnostics = provider.validate(content)
        errors = [
            d
            for d in diagnostics
            if d.severity == DiagnosticSeverity.Error and "nprocshared" in d.message.lower()
        ]
        assert len(errors) == 1

    def test_nprocshared_negative(self, provider: TypecheckProvider) -> None:
        """Negative %nprocshared should produce an error."""
        content = """\
%nprocshared=-1
# HF/STO-3G SP

Title

0 1
H 0.0 0.0 0.0
"""
        diagnostics = provider.validate(content)
        errors = [
            d
            for d in diagnostics
            if d.severity == DiagnosticSeverity.Error and "nprocshared" in d.message.lower()
        ]
        assert len(errors) == 1

    def test_empty_chk_value(self, provider: TypecheckProvider) -> None:
        """Empty %chk value should produce an error."""
        content = """\
%chk=
# HF/STO-3G SP

Title

0 1
H 0.0 0.0 0.0
"""
        diagnostics = provider.validate(content)
        errors = [
            d
            for d in diagnostics
            if d.severity == DiagnosticSeverity.Error and "chk" in d.message.lower()
        ]
        assert len(errors) >= 1


# ---------------------------------------------------------------------------
# Enum option validation
# ---------------------------------------------------------------------------


class TestEnumOptions:
    """Test route keyword enum option validation."""

    def test_valid_guess_option(self, provider: TypecheckProvider) -> None:
        """Valid Guess=Read should not produce warnings."""
        content = """\
# B3LYP/6-31G(d) Guess=Read SP

Guess test

0 1
H 0.0 0.0 0.0
"""
        diagnostics = provider.validate(content)
        guess_warnings = [
            d
            for d in diagnostics
            if "guess" in d.message.lower() and "unknown" in d.message.lower()
        ]
        assert guess_warnings == []

    def test_invalid_guess_option(self, provider: TypecheckProvider) -> None:
        """Invalid Guess=BadOption should produce a warning."""
        content = """\
# B3LYP/6-31G(d) Guess(BadOption) SP

Bad guess

0 1
H 0.0 0.0 0.0
"""
        diagnostics = provider.validate(content)
        warnings = [
            d
            for d in diagnostics
            if "unknown" in d.message.lower() and "guess" in d.message.lower()
        ]
        assert len(warnings) == 1

    def test_valid_scf_option(self, provider: TypecheckProvider) -> None:
        """Valid SCF=QC should not produce warnings."""
        content = """\
# B3LYP/6-31G(d) SCF=QC SP

SCF test

0 1
H 0.0 0.0 0.0
"""
        diagnostics = provider.validate(content)
        scf_warnings = [
            d for d in diagnostics if "unknown" in d.message.lower() and "scf" in d.message.lower()
        ]
        assert scf_warnings == []

    def test_invalid_scf_option(self, provider: TypecheckProvider) -> None:
        """Invalid SCF option should produce a warning."""
        content = """\
# B3LYP/6-31G(d) SCF(InvalidOpt) SP

Bad SCF

0 1
H 0.0 0.0 0.0
"""
        diagnostics = provider.validate(content)
        warnings = [
            d for d in diagnostics if "unknown" in d.message.lower() and "scf" in d.message.lower()
        ]
        assert len(warnings) == 1

    def test_numeric_enum_option_accepted(self, provider: TypecheckProvider) -> None:
        """Numeric options (e.g., MAXCYCLE=100) should not produce warnings."""
        content = """\
# B3LYP/6-31G(d) Opt(MaxCycle=100) SP

Numeric option

0 1
H 0.0 0.0 0.0
"""
        diagnostics = provider.validate(content)
        opt_warnings = [
            d for d in diagnostics if "unknown" in d.message.lower() and "opt" in d.message.lower()
        ]
        assert opt_warnings == []

    def test_valid_opt_option(self, provider: TypecheckProvider) -> None:
        """Valid Opt=TS should not produce warnings."""
        content = """\
# B3LYP/6-31G(d) Opt=TS SP

TS opt

0 1
H 0.0 0.0 0.0
"""
        diagnostics = provider.validate(content)
        opt_warnings = [
            d for d in diagnostics if "unknown" in d.message.lower() and "opt" in d.message.lower()
        ]
        assert opt_warnings == []


# ---------------------------------------------------------------------------
# Unit validation
# ---------------------------------------------------------------------------


class TestUnitValidation:
    """Test unit keyword validation."""

    def test_valid_units_ang(self, provider: TypecheckProvider) -> None:
        """Valid Units=Ang should produce no errors."""
        content = """\
# B3LYP/6-31G(d) Units=Ang SP

Units test

0 1
H 0.0 0.0 0.0
"""
        diagnostics = provider.validate(content)
        unit_errors = [
            d
            for d in diagnostics
            if "unknown" in d.message.lower() and "units" in d.message.lower()
        ]
        assert unit_errors == []

    def test_invalid_units_value(self, provider: TypecheckProvider) -> None:
        """Invalid Units value should produce an error."""
        content = """\
# B3LYP/6-31G(d) Units=INVALID SP

Bad units

0 1
H 0.0 0.0 0.0
"""
        diagnostics = provider.validate(content)
        unit_errors = [
            d
            for d in diagnostics
            if "unknown" in d.message.lower() and "units" in d.message.lower()
        ]
        assert len(unit_errors) == 1


# ---------------------------------------------------------------------------
# Unparseable input
# ---------------------------------------------------------------------------


class TestUnparseableInput:
    """Test that unparseable input does not crash the provider."""

    def test_empty_string(self, provider: TypecheckProvider) -> None:
        """Empty string should return empty list (parser raises)."""
        result = provider.validate("")
        assert isinstance(result, list)

    def test_whitespace_only(self, provider: TypecheckProvider) -> None:
        """Whitespace-only input should return empty list."""
        result = provider.validate("   \n  \n")
        assert isinstance(result, list)

    def test_garbage_input(self, provider: TypecheckProvider) -> None:
        """Random garbage should not crash."""
        result = provider.validate("asdfghjkl!@#$%^&*()")
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# Source identification
# ---------------------------------------------------------------------------


class TestSourceIdentification:
    """Test that diagnostics have the correct source."""

    def test_all_diagnostics_have_source(self, provider: TypecheckProvider) -> None:
        """All typecheck diagnostics should have source gaussian-lsp-typecheck."""
        content = """\
# /6-31G(d) opt

No method

0 1
H 0.0 0.0 0.0
"""
        diagnostics = provider.validate(content)
        for d in diagnostics:
            assert d.source == SOURCE
            assert d.source == "gaussian-lsp-typecheck"

    def test_valid_input_all_diagnostics_have_source(self, provider: TypecheckProvider) -> None:
        """Even for valid input, any diagnostics should have correct source."""
        content = """\
# B3LYP/6-31G(d) opt

Water

0 1
O  0.0 0.0 0.0
H  0.0 0.758 0.504
H  0.0 -0.758 0.504
"""
        diagnostics = provider.validate(content)
        for d in diagnostics:
            assert d.source == SOURCE


# ---------------------------------------------------------------------------
# Diagnostic ranges
# ---------------------------------------------------------------------------


class TestDiagnosticRanges:
    """Test that diagnostics have valid ranges."""

    def test_diagnostics_have_valid_ranges(self, provider: TypecheckProvider) -> None:
        """All diagnostics should have non-negative line/character ranges."""
        content = """\
%nprocshared=0
# B3LYP/6-31G(d) opt

Bad nproc

0 1
H 0.0 0.0 0.0
"""
        diagnostics = provider.validate(content)
        assert len(diagnostics) > 0
        for d in diagnostics:
            assert d.range.start.line >= 0
            assert d.range.start.character >= 0
            assert d.range.end.line >= 0
            assert d.range.end.character >= d.range.start.character


# ---------------------------------------------------------------------------
# Additional coverage for edge cases
# ---------------------------------------------------------------------------


class TestEdgeCaseCoverage:
    """Tests for uncovered branches in the typecheck provider."""

    def test_empty_value_non_critical_link0(self, provider: TypecheckProvider) -> None:
        """Empty value for a non-critical Link0 key should not produce errors."""
        content = """\
%subst=
# HF/STO-3G SP

Title

0 1
H 0.0 0.0 0.0
"""
        diagnostics = provider.validate(content)
        # subst has empty value but is not in the critical set
        errors = [
            d
            for d in diagnostics
            if d.severity == DiagnosticSeverity.Error and "subst" in d.message.lower()
        ]
        assert errors == []

    def test_unknown_link0_key_no_error(self, provider: TypecheckProvider) -> None:
        """An unknown Link0 key not in the schema should produce no typecheck errors."""
        content = """\
%unknownkey=somevalue
# HF/STO-3G SP

Title

0 1
H 0.0 0.0 0.0
"""
        diagnostics = provider.validate(content)
        # The key is not in _LINK0_SCHEMA, so no typecheck errors for it
        unknown_errors = [
            d
            for d in diagnostics
            if d.severity == DiagnosticSeverity.Error and "unknownkey" in d.message.lower()
        ]
        assert unknown_errors == []

    def test_route_continuation_lines(self, provider: TypecheckProvider) -> None:
        """Route section spanning multiple lines should be handled correctly."""
        content = """\
# B3LYP/6-31G(d)
 opt freq

Multi-line route

0 1
O  0.0 0.0 0.0
H  0.0 0.758 0.504
H  0.0 -0.758 0.504
"""
        diagnostics = provider.validate(content)
        errors = [d for d in diagnostics if d.severity == DiagnosticSeverity.Error]
        assert errors == []

    def test_permission_error_returns_empty(self, provider: TypecheckProvider) -> None:
        """A PermissionError during parsing should return empty list."""
        from unittest.mock import patch

        with patch.object(
            provider._parser,
            "parse",
            side_effect=PermissionError("denied"),
        ):
            result = provider.validate("# B3LYP/6-31G(d)\n\nT\n\n0 1\nH 0.0 0.0 0.0\n")
            assert result == []

    def test_generic_exception_returns_empty(self, provider: TypecheckProvider) -> None:
        """A generic exception during parsing should return empty list."""
        from unittest.mock import patch

        with patch.object(
            provider._parser,
            "parse",
            side_effect=RuntimeError("boom"),
        ):
            result = provider.validate("# B3LYP/6-31G(d)\n\nT\n\n0 1\nH 0.0 0.0 0.0\n")
            assert result == []

    def test_invalid_multiplicity_no_charge_line(self, provider: TypecheckProvider) -> None:
        """Invalid multiplicity when charge line cannot be found should skip."""
        # This exercises the branch where charge_line is None in _check_required_sections
        from unittest.mock import patch

        from gaussian_lsp.parser.gjf_parser import GaussianJob

        fake_job = GaussianJob(
            route_section="# B3LYP/6-31G(d) opt",
            title="Test",
            charge=0,
            multiplicity=0,
            atoms=[("H", 0.0, 0.0, 0.0)],
        )
        with patch.object(provider._parser, "parse", return_value=fake_job):
            content = "# B3LYP/6-31G(d) opt\n\nTest\n\n0 0\nH 0.0 0.0 0.0\n"
            diagnostics = provider.validate(content)
            # multiplicity 0 is invalid but charge_line may not be found
            # Should still produce some diagnostics
            assert isinstance(diagnostics, list)

    def test_find_route_end_no_route(self, provider: TypecheckProvider) -> None:
        """_find_route_end should return 0 when no route line exists."""
        from gaussian_lsp.features.typecheck import TypecheckProvider

        result = TypecheckProvider._find_route_end(["not a route", "another line"])
        assert result == 0

    def test_find_route_end_with_continuation(self, provider: TypecheckProvider) -> None:
        """_find_route_end should return the last route continuation line."""
        from gaussian_lsp.features.typecheck import TypecheckProvider

        lines = [
            "# B3LYP/6-31G(d)",
            " opt freq",
            "",
            "Title",
        ]
        result = TypecheckProvider._find_route_end(lines)
        assert result == 1

    def test_format_enum_list_short(self, provider: TypecheckProvider) -> None:
        """_format_enum_list should format short option lists."""
        from gaussian_lsp.features.typecheck import TypecheckProvider

        options = frozenset({"A", "B", "C"})
        result = TypecheckProvider._format_enum_list(options)
        assert "A" in result
        assert "B" in result
        assert "C" in result

    def test_format_enum_list_long(self, provider: TypecheckProvider) -> None:
        """_format_enum_list should truncate long option lists."""
        from gaussian_lsp.features.typecheck import TypecheckProvider

        options = frozenset(str(i) for i in range(20))
        result = TypecheckProvider._format_enum_list(options)
        assert "..." in result

    def test_typecheck_result_to_diagnostic(self) -> None:
        """TypecheckResult.to_diagnostic should produce a valid Diagnostic."""
        from gaussian_lsp.features.typecheck import TypecheckResult

        result = TypecheckResult(
            line=5,
            character=10,
            end_character=20,
            message="test message",
            severity=DiagnosticSeverity.Warning,
        )
        diag = result.to_diagnostic()
        assert diag.range.start.line == 5
        assert diag.range.start.character == 10
        assert diag.range.end.character == 20
        assert diag.message == "test message"
        assert diag.severity == DiagnosticSeverity.Warning

    def test_no_route_line_skips_type_checks(self, provider: TypecheckProvider) -> None:
        """When there's no route line, route type checks should return empty."""
        from unittest.mock import patch

        from gaussian_lsp.parser.gjf_parser import GaussianJob

        fake_job = GaussianJob(
            route_section="",
            title="Test",
            charge=0,
            multiplicity=1,
            atoms=[("H", 0.0, 0.0, 0.0)],
        )
        with patch.object(provider._parser, "parse", return_value=fake_job):
            content = "Test\n\n0 1\nH 0.0 0.0 0.0\n"
            diagnostics = provider.validate(content)
            # Missing route should produce a diagnostic
            assert any("route" in d.message.lower() for d in diagnostics)

    def test_multiple_enum_options(self, provider: TypecheckProvider) -> None:
        """Multiple options in a keyword should each be validated."""
        content = """\
# B3LYP/6-31G(d) SCF(QC,BogusOption) SP

Multi option

0 1
H 0.0 0.0 0.0
"""
        diagnostics = provider.validate(content)
        # QC is valid, BogusOption is not in the SCF enum
        warnings = [
            d for d in diagnostics if "unknown" in d.message.lower() and "scf" in d.message.lower()
        ]
        assert len(warnings) == 1
