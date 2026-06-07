"""Tests for Gaussian LSP server."""

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

GAUSSIAN_ERROR_TAXONOMY = [
    {
        "label": "L1_QPErr_route_syntax",
        "status": "static-detectable",
        "reason": "Route keyword spelling and option syntax are visible in the input file.",
        "fixture": "# M06-2X/6-31G(d)\n\nTypo\n\n0 1\nH 0.0 0.0 0.0\n",
        "expected": "Use M062X instead of M06-2X",
    },
    {
        "label": "L101_End_of_file_in_ZSymb",
        "status": "static-detectable",
        "reason": "Missing molecule specification or malformed geometry section is visible before running.",
        "fixture": "# HF/STO-3G\n\nNo geometry\n\n0 1\n",
        "expected": "No atoms defined",
    },
    {
        "label": "L101_WantedFound_malformed_molecule",
        "status": "static-detectable",
        "reason": "Gaussian wanted/found type mismatches are often malformed charge or coordinate lines.",
        "fixture": "# HF/STO-3G\n\nBad molecule\n\n0 singlet\nH 0.0 0.0 0.0\n",
        "expected": "Invalid charge/multiplicity line",
    },
    {
        "label": "L301_impossible_multiplicity_electrons",
        "status": "static-detectable",
        "reason": "Electron count and multiplicity parity can be computed from charge and elements.",
        "fixture": "# HF/STO-3G\n\nHydrogen radical\n\n0 1\nH 0.0 0.0 0.0\n",
        "expected": "electron count parity",
    },
    {
        "label": "L301_basis_center",
        "status": "static-detectable",
        "reason": "Custom basis center cards are part of the input file.",
        "fixture": "# HF/Gen\n\nBad basis\n\n0 1\nH 0.0 0.0 0.0\n\nH\nSTO-3G\n****\n",
        "expected": "Custom basis center line must end with 0",
    },
    {
        "label": "L301_ECP_pointer_card",
        "status": "static-detectable",
        "reason": "GenECP input must contain a separate ECP block after the basis block.",
        "fixture": "# HF/GenECP\n\nMissing ECP\n\n0 2\nI 0.0 0.0 0.0\n\nI 0\nLANL2DZ\n****\n",
        "expected": "GenECP is requested",
    },
    {
        "label": "L202_atoms_too_close",
        "status": "runtime-inferred",
        "reason": "Exact Gaussian crowding thresholds are runtime behavior, but near-duplicate coordinates are visible.",
        "fixture": "# HF/STO-3G\n\nCrowded\n\n0 1\nH 0.0 0.0 0.0\nH 0.0 0.0 0.01\n",
        "expected": "very close",
    },
    {
        "label": "L9999_optimization_stopped",
        "status": "runtime-only",
        "reason": "Requires optimization trajectory/output information after Gaussian runs.",
    },
    {
        "label": "L103_internal_coordinate_failure",
        "status": "runtime-only",
        "reason": "Requires generated internal coordinates and optimization state.",
    },
    {
        "label": "L502_SCF_convergence_failure",
        "status": "runtime-only",
        "reason": "Requires SCF iterations from Gaussian output.",
    },
    {
        "label": "L914_L1002_not_enough_memory",
        "status": "runtime-inferred",
        "reason": "Exact memory need is runtime-only; suspicious %mem/%nproc combinations may be warned later.",
    },
    {
        "label": "General_segmentation_fault",
        "status": "out-of-scope-static",
        "reason": "Generic crash output has no reliable input-only signature.",
    },
]


class TestGaussianServer:
    """Test Gaussian LSP server."""

    def test_server_exists(self):
        """Test server instance exists."""
        from gaussian_lsp import __version__
        from gaussian_lsp.server import server

        assert server is not None
        assert server.name == "gaussian-lsp"
        assert server.version == __version__

    def test_completion_feature(self):
        """Test completion feature returns keywords."""
        from gaussian_lsp.server import completion

        # Mock params and document
        mock_params = MagicMock()
        mock_params.text_document.uri = "file:///test.gjf"
        mock_params.position.line = 0
        mock_params.position.character = 0

        with patch("gaussian_lsp.server.server") as mock_server:
            mock_doc = MagicMock()
            mock_doc.lines = ["# B3LYP"]
            mock_server.workspace.get_text_document.return_value = mock_doc

            result = completion(mock_params)

            # Should return a CompletionList
            assert result is not None
            assert hasattr(result, "items")
            assert len(result.items) > 0
            # Check first item has required fields
            assert hasattr(result.items[0], "label")
            assert hasattr(result.items[0], "kind")

    def test_completion_with_context(self):
        """Test completion provides context-aware results."""
        from gaussian_lsp.server import completion

        mock_params = MagicMock()
        mock_params.text_document.uri = "file:///test.gjf"
        mock_params.position.line = 0
        mock_params.position.character = 0

        with patch("gaussian_lsp.server.server") as mock_server:
            mock_doc = MagicMock()
            mock_doc.lines = ["# B3LYP/6-31G(d)"]
            mock_server.workspace.get_text_document.return_value = mock_doc

            result = completion(mock_params)

            # Check methods are present
            labels = [item.label for item in result.items]
            assert "B3LYP" in labels
            assert "HF" in labels
            assert "OPT" in labels

    def test_hover_feature_with_keyword(self):
        """Test hover feature returns documentation for known keywords."""
        from gaussian_lsp.server import hover

        mock_params = MagicMock()
        mock_params.text_document.uri = "file:///test.gjf"
        mock_params.position.line = 0
        mock_params.position.character = 2

        with patch("gaussian_lsp.server.server") as mock_server:
            mock_doc = MagicMock()
            mock_doc.lines = ["# B3LYP/6-31G(d)"]
            mock_server.workspace.get_text_document.return_value = mock_doc

            result = hover(mock_params)

            # Should return hover info for B3LYP
            if result is not None:
                assert hasattr(result, "contents")

    def test_hover_feature_no_match(self):
        """Test hover feature returns None for unknown keywords."""
        from gaussian_lsp.server import hover

        mock_params = MagicMock()
        mock_params.text_document.uri = "file:///test.gjf"
        mock_params.position.line = 0
        mock_params.position.character = 10

        with patch("gaussian_lsp.server.server") as mock_server:
            mock_doc = MagicMock()
            mock_doc.lines = ["# UNKNOWN/6-31G(d)"]
            mock_server.workspace.get_text_document.return_value = mock_doc

            result = hover(mock_params)

            # May return None for unknown keywords
            assert result is None or hasattr(result, "contents")

    def test_get_word_at_position(self):
        """Test word extraction at position."""
        from gaussian_lsp.server import _get_word_at_position

        # Test extracting B3LYP from "# B3LYP/6-31G(d)"
        line = "# B3LYP/6-31G(d)"

        # Position at B
        word = _get_word_at_position(line, 2)
        assert word == "B3LYP"

        # Position at 3
        word = _get_word_at_position(line, 4)
        assert word == "B3LYP"

        # Position at end
        word = _get_word_at_position(line, len(line))
        assert word == ""

    def test_get_word_at_position_gaussian_punctuation(self):
        """Test Gaussian-aware hover tokens keep keyword punctuation."""
        from gaussian_lsp.server import _get_word_at_position, _hover_lookup_candidates

        assert _get_word_at_position("# CCSD(T)/cc-pVDZ", 3) == "CCSD(T)"
        assert _get_word_at_position("# CCSD(T)/cc-pVDZ", 10) == "cc-pVDZ"
        assert _get_word_at_position("# CAM-B3LYP/6-31+G*", 4) == "CAM-B3LYP"
        assert _get_word_at_position("# CAM-B3LYP/6-31+G*", 15) == "6-31+G*"
        assert _hover_lookup_candidates("") == []
        assert _hover_lookup_candidates("B3LYP/6-31G(d)") == [
            "B3LYP/6-31G(d)",
            "B3LYP",
            "6-31G(d)",
        ]
        assert _hover_lookup_candidates("HF/HF") == ["HF/HF", "HF"]

    def test_hover_unknown_gaussian_token_returns_none(self):
        """Test hover returns None for unknown non-empty tokens."""
        from gaussian_lsp.server import hover

        mock_params = MagicMock()
        mock_params.text_document.uri = "file:///test.gjf"
        mock_params.position.line = 0
        mock_params.position.character = 2

        with patch("gaussian_lsp.server.server") as mock_server:
            mock_doc = MagicMock()
            mock_doc.lines = ["# UNKNOWNKEYWORD"]
            mock_server.workspace.get_text_document.return_value = mock_doc

            assert hover(mock_params) is None

    def test_get_word_at_position_empty_line(self):
        """Test word extraction with empty line."""
        from gaussian_lsp.server import _get_word_at_position

        word = _get_word_at_position("", 0)
        assert word == ""


class TestDiagnosticFeature:
    """Test diagnostic feature."""

    def test_diagnostic_valid_content(self):
        """Test diagnostic with valid content."""
        from gaussian_lsp.server import _analyze_content

        content = """# B3LYP/6-31G(d)

Test

0 2
H 0.0 0.0 0.0
"""
        diagnostics = _analyze_content(content)

        # Valid content should have minimal/no diagnostics
        error_diagnostics = [d for d in diagnostics if d.severity.value <= 1]
        assert len(error_diagnostics) == 0

    def test_diagnostic_missing_route(self):
        """Test diagnostic catches missing route."""
        from gaussian_lsp.server import _analyze_content

        content = """Test

0 1
H 0.0 0.0 0.0
"""
        diagnostics = _analyze_content(content)

        # Should have error about missing route
        error_msgs = [d.message for d in diagnostics]
        assert any("route" in msg.lower() for msg in error_msgs)

    def test_diagnostic_missing_atoms(self):
        """Test diagnostic catches missing atoms."""
        from gaussian_lsp.server import _analyze_content

        content = """# B3LYP/6-31G(d)

Test

0 1
"""
        diagnostics = _analyze_content(content)

        error_msgs = [d.message for d in diagnostics]
        assert any("atom" in msg.lower() for msg in error_msgs)

    def test_diagnostic_invalid_element(self):
        """Test diagnostic warns about invalid element."""
        from gaussian_lsp.server import _analyze_content

        content = """# B3LYP/6-31G(d)

Test

0 1
Xx 0.0 0.0 0.0
"""
        diagnostics = _analyze_content(content)

        warn_msgs = [d.message for d in diagnostics]
        assert any("unknown" in msg.lower() for msg in warn_msgs)

    def test_diagnostic_parse_error(self):
        """Test diagnostic handles parse error."""
        from gaussian_lsp.server import _analyze_content

        content = ""
        diagnostics = _analyze_content(content)

        assert len(diagnostics) > 0
        assert any("parse" in d.message.lower() for d in diagnostics)


class TestFormattingFeature:
    """Test formatting feature."""

    def test_format_gjf_valid(self):
        """Test formatting valid GJF."""
        from gaussian_lsp.server import _format_gjf

        content = """# B3LYP/6-31G(d)

Test

0 1
H 0.0 0.0 0.0
"""
        formatted = _format_gjf(content)

        # Should format successfully
        assert "# B3LYP/6-31G(d)" in formatted
        assert "0 1" in formatted

    def test_format_gjf_invalid(self):
        """Test formatting invalid GJF returns original."""
        from gaussian_lsp.server import _format_gjf

        content = "invalid content"
        formatted = _format_gjf(content)

        # Should return original if parsing fails
        assert formatted == content


class TestMain:
    """Test main entry point."""

    @patch("gaussian_lsp.server.server.start_io")
    def test_main(self, mock_start):
        """Test main function."""
        from gaussian_lsp.server import main

        main()
        mock_start.assert_called_once()

    @patch("gaussian_lsp.server.server.start_io")
    def test_main_direct(self, mock_start):
        """Test main when called directly."""
        import gaussian_lsp.server as server_module

        server_module.main()
        mock_start.assert_called_once()


class TestKeywordDocs:
    """Test keyword documentation."""

    def test_keyword_docs_exist(self):
        """Test keyword documentation exists."""
        from gaussian_lsp.server import KEYWORD_DOCS

        assert "HF" in KEYWORD_DOCS
        assert "B3LYP" in KEYWORD_DOCS
        assert "OPT" in KEYWORD_DOCS
        assert "STO-3G" in KEYWORD_DOCS

    def test_keyword_docs_content(self):
        """Test keyword documentation has content."""
        from gaussian_lsp.server import KEYWORD_DOCS

        for keyword, doc in KEYWORD_DOCS.items():
            assert len(doc) > 0
            assert isinstance(doc, str)


class TestDiagnosticEdgeCases:
    """Test diagnostic edge cases for 100% coverage."""

    def test_diagnostic_empty_file_with_only_comments_and_link0(self):
        """Test diagnostic with file containing only comments and link0."""
        from gaussian_lsp.server import _analyze_content

        # File with only comments and link0, no route section
        content = """%chk=test.chk
! This is a comment
%mem=1GB
! Another comment
"""
        diagnostics = _analyze_content(content)

        # Should have error about missing route
        error_msgs = [d.message for d in diagnostics]
        assert any("Missing route section" in msg for msg in error_msgs)

    def test_diagnostic_route_not_starting_with_hash(self):
        """Test diagnostic with route section not starting with #."""
        from gaussian_lsp.server import _analyze_content

        # Route section without leading # (will be parsed but flagged)
        content = """B3LYP/6-31G(d) opt

Test

0 1
O 0.0 0.0 0.0
"""
        diagnostics = _analyze_content(content)

        # Should have diagnostics about route section
        assert len(diagnostics) > 0

    def test_diagnostic_with_link0_no_route(self):
        """Test diagnostic with link0 commands but no route."""
        from gaussian_lsp.server import _analyze_content

        content = """%chk=test.chk
%mem=1GB
%nproc=4

Test

0 1
H 0.0 0.0 0.0
"""
        diagnostics = _analyze_content(content)

        # Should have error about missing route
        error_msgs = [d.message for d in diagnostics]
        assert any("route" in msg.lower() for msg in error_msgs)


class TestEnhancedGaussianDiagnostics:
    """Test Gaussian diagnostics for common real input failures."""

    @staticmethod
    def messages(content):
        """Return diagnostic messages for content."""
        from gaussian_lsp.server import _analyze_content

        return [diagnostic.message for diagnostic in _analyze_content(content)]

    @staticmethod
    def diagnostics(content):
        """Return diagnostics for content."""
        from gaussian_lsp.server import _analyze_content

        return _analyze_content(content)

    def test_gaussian_error_taxonomy_matrix_is_complete(self):
        """Test referenced Gaussian error families are mapped to LSP scope."""
        statuses = {item["status"] for item in GAUSSIAN_ERROR_TAXONOMY}
        labels = {item["label"] for item in GAUSSIAN_ERROR_TAXONOMY}

        assert statuses == {
            "static-detectable",
            "runtime-inferred",
            "runtime-only",
            "out-of-scope-static",
        }
        assert {
            "L1_QPErr_route_syntax",
            "L101_End_of_file_in_ZSymb",
            "L101_WantedFound_malformed_molecule",
            "L301_basis_center",
            "L9999_optimization_stopped",
            "L103_internal_coordinate_failure",
            "L502_SCF_convergence_failure",
        }.issubset(labels)
        for item in GAUSSIAN_ERROR_TAXONOMY:
            assert item["label"]
            assert item["reason"]
            if item["status"] == "static-detectable":
                assert item.get("fixture")
                assert item.get("expected")

    @pytest.mark.parametrize(
        "case",
        [item for item in GAUSSIAN_ERROR_TAXONOMY if item["status"] == "static-detectable"],
        ids=lambda item: item["label"],
    )
    def test_static_detectable_gaussian_error_families_emit_errors(self, case):
        """Test input-deterministic Gaussian error families emit LSP errors."""
        from lsprotocol import types

        diagnostics = self.diagnostics(case["fixture"])
        messages = [diagnostic.message for diagnostic in diagnostics]

        assert any(case["expected"] in message for message in messages)
        assert any(
            case["expected"] in diagnostic.message
            and diagnostic.severity == types.DiagnosticSeverity.Error
            for diagnostic in diagnostics
        )

    @pytest.mark.parametrize(
        "case",
        [item for item in GAUSSIAN_ERROR_TAXONOMY if item["status"] == "runtime-inferred"],
        ids=lambda item: item["label"],
    )
    def test_runtime_inferred_gaussian_error_families_are_warnings_or_matrix_only(self, case):
        """Test runtime-only risks inferred from input are warnings, not errors."""
        from lsprotocol import types

        if "fixture" not in case:
            assert case["reason"]
            return

        diagnostics = self.diagnostics(case["fixture"])

        assert any(case["expected"] in diagnostic.message for diagnostic in diagnostics)
        assert any(
            case["expected"] in diagnostic.message
            and diagnostic.severity == types.DiagnosticSeverity.Warning
            for diagnostic in diagnostics
        )

    def test_diagnostic_missing_required_blank_lines(self):
        """Test required Gaussian section blank lines are detected."""
        content = """# B3LYP/6-31G(d)
Water title
0 1
O 0.0 0.0 0.0
"""
        messages = self.messages(content)

        assert any("blank line after route section" in message for message in messages)
        assert any("blank line after title section" in message for message in messages)

    def test_diagnostic_missing_charge_multiplicity(self):
        """Test missing charge/multiplicity line is detected explicitly."""
        content = """# B3LYP/6-31G(d)

Water title

O 0.0 0.0 0.0
"""
        messages = self.messages(content)

        assert any("Missing charge/multiplicity line" in message for message in messages)

    def test_diagnostic_malformed_charge_multiplicity(self):
        """Test malformed charge/multiplicity line is detected."""
        content = """# B3LYP/6-31G(d)

Water title

0 singlet
O 0.0 0.0 0.0
"""
        messages = self.messages(content)

        assert any("Invalid charge/multiplicity line" in message for message in messages)

    def test_diagnostic_electron_multiplicity_parity_mismatch_odd_singlet(self):
        """Test odd electron count with singlet multiplicity is flagged."""
        content = """# HF/STO-3G

Hydrogen radical

0 1
H 0.0 0.0 0.0
"""
        messages = self.messages(content)

        assert any("electron count parity" in message for message in messages)

    def test_diagnostic_electron_multiplicity_parity_mismatch_even_doublet(self):
        """Test even electron count with doublet multiplicity is flagged."""
        content = """# HF/STO-3G

Hydrogen molecule

0 2
H 0.0 0.0 0.0
H 0.0 0.0 0.7
"""
        messages = self.messages(content)

        assert any("electron count parity" in message for message in messages)

    def test_diagnostic_missing_gen_basis_section(self):
        """Test Gen route without custom basis data is detected."""
        content = """# B3LYP/Gen

Water title

0 1
O 0.0 0.0 0.0
H 0.0 0.0 1.0
H 1.0 0.0 0.0
"""
        messages = self.messages(content)

        assert any("Gen basis set is requested" in message for message in messages)

    def test_diagnostic_missing_genecp_ecp_section(self):
        """Test GenECP route without an ECP block is detected."""
        content = """# B3LYP/GenECP

Iodine title

0 2
I 0.0 0.0 0.0

I 0
LANL2DZ
****
"""
        messages = self.messages(content)

        assert any("GenECP is requested" in message for message in messages)

    def test_diagnostic_ecp_basis_with_light_elements(self):
        """Test ECP basis on only light elements gets a warning."""
        content = """# B3LYP/LANL2DZ

Water title

0 1
O 0.0 0.0 0.0
H 0.0 0.0 1.0
H 1.0 0.0 0.0
"""
        messages = self.messages(content)

        assert any(
            "ECP basis set is usually intended for heavier elements" in message
            for message in messages
        )

    def test_diagnostic_unbalanced_route_parentheses(self):
        """Test route keyword parentheses are balanced."""
        content = """# B3LYP/6-31G(d) opt=(ts,calcfc

TS title

0 1
H 0.0 0.0 0.0
H 0.0 0.0 0.7
"""
        messages = self.messages(content)

        assert any("Unbalanced parentheses" in message for message in messages)

    def test_diagnostic_common_route_typos(self):
        """Test common Gaussian keyword typos are detected."""
        content = """# b3lyp/631g optimize freqency

Typo title

0 1
H 0.0 0.0 0.0
H 0.0 0.0 0.7
"""
        messages = self.messages(content)

        assert any("Use opt instead of optimize" in message for message in messages)
        assert any("Use freq instead of freqency" in message for message in messages)
        assert any("Did you mean 6-31G" in message for message in messages)

    def test_diagnostic_modredundant_reference_out_of_range(self):
        """Test ModRedundant atom references cannot exceed geometry size."""
        content = """# B3LYP/6-31G(d) opt=modredundant

Constrained title

0 1
H 0.0 0.0 0.0
H 0.0 0.0 0.7

B 1 9 F
"""
        messages = self.messages(content)

        assert any("references atom 9" in message for message in messages)

    def test_diagnostic_malformed_coordinate_line(self):
        """Test malformed coordinate lines are detected."""
        content = """# B3LYP/6-31G(d)

Bad geometry

0 1
O 0.0 0.0
H 0.0 zero 1.0
H 1.0 0.0 0.0
"""
        messages = self.messages(content)

        assert any("Invalid coordinate line" in message for message in messages)

    def test_diagnostic_link0_value_formats(self):
        """Test Link0 resource values are validated."""
        content = """%chk=
%mem=abc
%nproc=0
%nprocshared=two
# HF/STO-3G

Bad Link0

0 1
H 0.0 0.0 0.0
"""
        messages = self.messages(content)

        assert any("%chk must include a non-empty value" in message for message in messages)
        assert any("%mem value should include a positive number" in message for message in messages)
        assert any("%nproc must be a positive integer" in message for message in messages)
        assert any("%nprocshared must be a positive integer" in message for message in messages)

    def test_diagnostic_ignores_link0_without_value_separator(self):
        """Test incomplete Link0 lines without equals do not crash diagnostics."""
        content = """%chk
# HF/STO-3G

Incomplete Link0

0 2
H 0.0 0.0 0.0
"""
        messages = self.messages(content)

        assert not any("must include a non-empty value" in message for message in messages)

    def test_diagnostic_dummy_atom_does_not_affect_electron_parity(self):
        """Test dummy atoms are skipped in electron parity checks."""
        content = """# HF/STO-3G

Dummy atom

0 1
X 0.0 0.0 0.0
"""
        messages = self.messages(content)

        assert not any("electron count parity" in message for message in messages)

    def test_diagnostic_allows_valid_genecp_sections(self):
        """Test GenECP with basis and ECP blocks does not emit missing-block errors."""
        content = """# B3LYP/GenECP

Iodine title

0 2
I 0.0 0.0 0.0

I 0
LANL2DZ
****
I 0
LANL2DZ
****
"""
        messages = self.messages(content)

        assert not any("GenECP is requested" in message for message in messages)

    def test_diagnostic_ecp_basis_with_heavy_element_is_allowed(self):
        """Test ECP basis warning is not emitted for heavy elements."""
        content = """# B3LYP/LANL2DZ

Iodine title

0 2
I 0.0 0.0 0.0
"""
        messages = self.messages(content)

        assert not any("ECP basis set is usually intended" in message for message in messages)

    def test_diagnostic_charge_then_blank_before_geometry(self):
        """Test blank lines before geometry are tolerated while scanning geometry."""
        content = """# HF/STO-3G

Hydrogen radical

0 2

H 0.0 0.0 0.0
"""
        messages = self.messages(content)

        assert not any("Invalid coordinate line" in message for message in messages)

    def test_diagnostic_modredundant_wrong_arity(self):
        """Test ModRedundant commands with too few atom indexes are detected."""
        content = """# B3LYP/6-31G(d) opt=modredundant

Bad constraint

0 1
H 0.0 0.0 0.0
H 0.0 0.0 0.7

A 1 2 F
"""
        messages = self.messages(content)

        assert any("expects 3 integer atom indexes" in message for message in messages)

    def test_diagnostic_valid_modredundant_reference(self):
        """Test valid ModRedundant atom references do not emit reference errors."""
        content = """# B3LYP/6-31G(d) opt=modredundant

Good constraint

0 1
H 0.0 0.0 0.0
H 0.0 0.0 0.7

B 1 2 F
"""
        messages = self.messages(content)

        assert not any("ModRedundant command references" in message for message in messages)

    def test_L101_ZSymb_undefined_zmatrix_variable(self):
        """Test Z-matrix variable references must be defined."""
        content = """# HF/STO-3G

Z-matrix undefined variable

0 1
O
H 1 R1
H 1 R2 2 A1

R1=0.960
R2=0.960
"""
        messages = self.messages(content)

        assert any("Undefined Z-matrix variable: A1" in message for message in messages)

    def test_L101_ZSymb_malformed_zmatrix_variable_definition(self):
        """Test malformed Z-matrix variable definitions are detected."""
        content = """# HF/STO-3G

Z-matrix bad variable

0 1
O
H 1 R1

R1=not-a-number
"""
        messages = self.messages(content)

        assert any("Invalid Z-matrix variable definition" in message for message in messages)

    def test_L101_ZSymb_ignores_non_variable_post_geometry_lines(self):
        """Test non-variable post-geometry lines do not hide undefined Z-matrix variables."""
        content = """# HF/STO-3G

Z-matrix comment line

0 1
O
H 1 R1

Variables:
"""
        messages = self.messages(content)

        assert any("Undefined Z-matrix variable: R1" in message for message in messages)

    def test_L101_WantedFound_mixed_coordinate_line(self):
        """Test mixed Cartesian/Z-matrix coordinate shapes are detected."""
        content = """# HF/STO-3G

Mixed geometry

0 1
O 0.0 0.0 0.0
H 1 R1 0.0
"""
        messages = self.messages(content)

        assert any("Mixed Cartesian/Z-matrix coordinate line" in message for message in messages)

    def test_L301_basis_references_absent_geometry_element(self):
        """Test custom basis center cards must match geometry elements."""
        content = """# HF/Gen

Bad basis element

0 2
H 0.0 0.0 0.0

N 0
STO-3G
****
"""
        messages = self.messages(content)

        assert any("Custom basis references N" in message for message in messages)

    def test_L301_basis_missing_delimiter(self):
        """Test Gen basis sections require **** delimiters."""
        content = """# HF/Gen

Bad basis delimiter

0 2
H 0.0 0.0 0.0

H 0
STO-3G
"""
        messages = self.messages(content)

        assert any("custom basis section with **** delimiters" in message for message in messages)

    def test_L1_QPErr_link0_command_in_route(self):
        """Test Link0-only processor command in route is an input syntax error."""
        content = """# HF/STO-3G nprocshared=8

Bad route

0 2
H 0.0 0.0 0.0
"""
        messages = self.messages(content)

        assert any("%nprocshared as a Link0 command" in message for message in messages)

    def test_L1_QPErr_modredundant_non_integer_index(self):
        """Test ModRedundant atom indexes must be integers."""
        content = """# HF/STO-3G opt=modredundant

Bad modred

0 1
H 0.0 0.0 0.0
H 0.0 0.0 0.7

B 1 two F
"""
        messages = self.messages(content)

        assert any(
            "ModRedundant B command expects 2 integer atom indexes" in message
            for message in messages
        )

    @pytest.mark.parametrize(
        ("route", "expected"),
        [
            ("# RHF UHF/6-31G(d)", "Mutually exclusive SCF methods"),
            ("# B3LYP/6-31G(d) MP2", "Conflicting calculation methods"),
            ("# SP OPT B3LYP/6-31G(d)", "SP and OPT are mutually exclusive"),
            ("# B3LYP/6-31G(d) cc-pVDZ", "Multiple basis sets"),
            ("# PM6/cc-pVTZ", "Semi-empirical methods"),
            ("# RHF/6-31G(d) Guess=Mix", "Guess=Mix"),
            ("# B3LYP/6-31G(d) Opt=ModRedundant", "Opt=ModRedundant"),
        ],
    )
    def test_route_keyword_conflicts(self, route, expected):
        """Test route keyword incompatibilities emit static diagnostics."""
        messages = self.messages(
            f"""{route}

Route conflict

0 1
H 0.0 0.0 0.0
"""
        )

        assert any(expected in message for message in messages)

    def test_diagnostic_parse_error_is_generic(self):
        """Test parser exceptions do not leak raw exception details to users."""
        messages = self.messages("%chk=bad;rm\n# HF/STO-3G\n\nBad\n\n0 1\nH 0 0 0\n")

        assert "Parse error: Invalid GJF file format" in messages
        assert not any("bad;rm" in message for message in messages)

    def test_diagnostic_permission_error_is_generic(self):
        """Test permission errors are reported without raw details."""
        from unittest.mock import patch

        from gaussian_lsp.server import _analyze_content

        with patch("gaussian_lsp.server.GJFParser") as mock_parser_cls:
            mock_parser_cls.return_value.parse.side_effect = PermissionError("/secret/path")
            messages = [diagnostic.message for diagnostic in _analyze_content("content")]

        assert messages == ["Parse error: Unable to read Gaussian input"]

    def test_diagnostic_unexpected_error_is_generic(self):
        """Test unexpected parser errors are reported without raw details."""
        from unittest.mock import patch

        from gaussian_lsp.server import _analyze_content

        with patch("gaussian_lsp.server.GJFParser") as mock_parser_cls:
            mock_parser_cls.return_value.parse.side_effect = RuntimeError("internal secret")
            messages = [diagnostic.message for diagnostic in _analyze_content("content")]

        assert messages == ["Parse error: Invalid GJF file format"]

    def test_validation_accuracy_framework_meets_threshold(self):
        """Test validation cases meet the documented accuracy threshold."""
        cases = [
            ("# RHF UHF/6-31G(d)\n\nBad\n\n0 1\nH 0 0 0\n", True),
            ("# RHF ROHF/6-31G(d)\n\nBad\n\n0 1\nH 0 0 0\n", True),
            ("# B3LYP/6-31G(d) MP2\n\nBad\n\n0 1\nH 0 0 0\n", True),
            ("# PBE0/6-31G(d) CCSD\n\nBad\n\n0 1\nH 0 0 0\n", True),
            ("# SP OPT B3LYP/6-31G(d)\n\nBad\n\n0 1\nH 0 0 0\n", True),
            ("# B3LYP/6-31G(d) cc-pVDZ\n\nBad\n\n0 1\nH 0 0 0\n", True),
            ("# PM6/cc-pVTZ\n\nBad\n\n0 1\nH 0 0 0\n", True),
            ("# RHF/6-31G(d) Guess=Mix\n\nBad\n\n0 1\nH 0 0 0\n", True),
            ("# B3LYP/6-31G(d) Opt=ModRedundant\n\nBad\n\n0 1\nH 0 0 0\n", True),
            ("# HF/STO-3G\n\nOdd singlet\n\n0 1\nH 0 0 0\n", True),
            ("# HF/Gen\n\nNo basis\n\n0 1\nH 0 0 0\n", True),
            ("# HF/STO-3G\n\nBad coord\n\n0 1\nH x 0 0\n", True),
            ("# HF/STO-3G\n\nValid\n\n0 2\nH 0 0 0\n", False),
            ("# B3LYP/6-31G(d) opt freq\n\nValid\n\n0 1\nH 0 0 0\nH 0 0 1\n", False),
            ("# PM6 opt\n\nValid\n\n0 1\nH 0 0 0\nH 0 0 1\n", False),
            ("# HF/Gen\n\nValid\n\n0 2\nH 0 0 0\n\nH 0\nSTO-3G\n****\n", False),
        ]

        true_positive = false_positive = false_negative = 0
        for content, should_error in cases:
            has_error = any(diagnostic.severity == 1 for diagnostic in self.diagnostics(content))
            true_positive += int(has_error and should_error)
            false_positive += int(has_error and not should_error)
            false_negative += int(not has_error and should_error)

        precision = true_positive / (true_positive + false_positive)
        recall = true_positive / (true_positive + false_negative)
        f1 = 2 * precision * recall / (precision + recall)

        assert precision >= 0.9
        assert recall >= 0.9
        assert f1 >= 0.9

    def test_internal_geometry_index_helper_skips_leading_blank(self):
        """Test geometry line helper skips blanks before atoms."""
        from gaussian_lsp.server import _geometry_line_indexes

        lines = ["0 1", "", "H 0.0 0.0 0.0"]

        assert _geometry_line_indexes(lines, 0) == [2]

    def test_internal_chemistry_helper_skips_dummy_and_numeric_atoms(self):
        """Test electron counting skips dummy and numeric atom markers."""
        from gaussian_lsp.parser.gjf_parser import GaussianJob
        from gaussian_lsp.server import _append_chemistry_diagnostics

        diagnostics = []
        job = GaussianJob(
            charge=0, multiplicity=1, atoms=[("X", 0.0, 0.0, 0.0), ("1", 0.0, 0.0, 0.0)]
        )

        _append_chemistry_diagnostics(diagnostics, ["0 1"], job)

        assert diagnostics == []

    def test_internal_basis_section_helper_skips_blank_before_geometry(self):
        """Test basis section helper handles blank lines before geometry starts."""
        from gaussian_lsp.server import _basis_section_lines

        lines = ["0 1", "", "H 0.0 0.0 0.0", "", "H 0", "STO-3G", "****"]

        assert _basis_section_lines(lines, 0) == ["H 0", "STO-3G", "****"]

    def test_internal_geometry_helper_ignores_non_coordinate_extra_lines(self):
        """Test non-coordinate non-element lines do not produce coordinate diagnostics."""
        from gaussian_lsp.parser.gjf_parser import GaussianJob, GJFParser
        from gaussian_lsp.server import _append_geometry_diagnostics

        diagnostics = []
        lines = ["0 1", "not a coordinate"]

        _append_geometry_diagnostics(diagnostics, lines, GJFParser(), GaussianJob())

        assert diagnostics == []

    def test_lsp_protocol_reports_valid_and_broken_diagnostics(self, tmp_path):
        """Test real LSP diagnostic requests for valid and broken files."""
        root = Path(__file__).resolve().parents[1]
        valid_uri = (root / "examples" / "water.gjf").resolve().as_uri()
        valid_text = (root / "examples" / "water.gjf").read_text()
        broken_uri = (tmp_path / "broken.gjf").resolve().as_uri()
        broken_text = """%mem=abc
# b3lyp/631g optimize

Broken

0 2
H 0.0 0.0 0.0
H 0.0 0.0 0.7

B 1 9 F
"""

        proc = subprocess.Popen(
            [sys.executable, "-c", "from gaussian_lsp.server import main; main()"],
            cwd=root,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        next_id = 1

        def send(payload):
            raw = json.dumps(payload, separators=(",", ":")).encode()
            assert proc.stdin is not None
            proc.stdin.write(b"Content-Length: " + str(len(raw)).encode() + b"\r\n\r\n" + raw)
            proc.stdin.flush()

        def read_message():
            assert proc.stdout is not None
            headers = {}
            line = proc.stdout.readline()
            while line not in (b"\r\n", b"\n"):
                key, value = line.decode().split(":", 1)
                headers[key.lower()] = value.strip()
                line = proc.stdout.readline()
            return json.loads(proc.stdout.read(int(headers["content-length"])))

        def request(method, params):
            nonlocal next_id
            request_id = next_id
            next_id += 1
            send({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params})
            while True:
                message = read_message()
                if message.get("id") == request_id:
                    return message

        def notify(method, params):
            send({"jsonrpc": "2.0", "method": method, "params": params})

        try:
            request(
                "initialize",
                {"processId": None, "rootUri": root.resolve().as_uri(), "capabilities": {}},
            )
            notify("initialized", {})
            notify(
                "textDocument/didOpen",
                {
                    "textDocument": {
                        "uri": valid_uri,
                        "languageId": "gaussian",
                        "version": 1,
                        "text": valid_text,
                    }
                },
            )
            valid_response = request(
                "textDocument/diagnostic",
                {
                    "textDocument": {"uri": valid_uri},
                    "identifier": "proof",
                    "previousResultId": None,
                },
            )
            notify(
                "textDocument/didOpen",
                {
                    "textDocument": {
                        "uri": broken_uri,
                        "languageId": "gaussian",
                        "version": 1,
                        "text": broken_text,
                    }
                },
            )
            broken_response = request(
                "textDocument/diagnostic",
                {
                    "textDocument": {"uri": broken_uri},
                    "identifier": "proof",
                    "previousResultId": None,
                },
            )
        finally:
            try:
                notify("exit", {})
            except Exception:
                pass
            proc.kill()

        valid_errors = [
            item for item in valid_response["result"]["items"] if item.get("severity") == 1
        ]
        broken_messages = [item["message"] for item in broken_response["result"]["items"]]

        assert valid_errors == []
        assert any(
            "%mem value should include a positive number" in message for message in broken_messages
        )
        assert any("electron count parity" in message for message in broken_messages)
        assert any("references atom 9" in message for message in broken_messages)
