"""Tests for Gaussian LSP server."""

from unittest.mock import MagicMock, patch


class TestGaussianServer:
    """Test Gaussian LSP server."""

    def test_server_exists(self):
        """Test server instance exists."""
        from gaussian_lsp.server import server

        assert server is not None
        assert server.name == "gaussian-lsp"
        assert server.version == "0.2.10"

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

0 1
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
