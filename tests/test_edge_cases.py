"""Additional tests for edge cases."""

from unittest.mock import MagicMock, patch


class TestDiagnosticRouteSectionEdgeCase:
    """Test diagnostic route section edge case."""

    def test_diagnostic_route_section_without_hash(self):
        """Test diagnostic when route section exists but doesn't start with #."""
        from gaussian_lsp.server import diagnostic

        mock_params = MagicMock()
        mock_params.text_document.uri = "file:///test.gjf"

        with patch("gaussian_lsp.server.server") as mock_server:
            mock_doc = MagicMock()
            # Content that would create a route_section without leading #
            mock_doc.source = """B3LYP/6-31G(d)

Test

0 1
H 0.0 0.0 0.0
"""
            mock_doc.lines = mock_doc.source.split("\n")
            mock_server.workspace.get_text_document.return_value = mock_doc

            result = diagnostic(mock_params)

            assert result is not None
            assert hasattr(result, "items")
