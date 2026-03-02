"""Tests for Gaussian LSP server."""
import pytest
from unittest.mock import MagicMock, patch


class TestGaussianServer:
    """Test Gaussian LSP server."""

    def test_server_exists(self):
        """Test server instance exists."""
        from gaussian_lsp.server import server
        assert server is not None
        assert server.name == "gaussian-lsp"
        assert server.version == "0.1.0"

    def test_completion_feature(self):
        """Test completion feature returns keywords."""
        from gaussian_lsp.server import completion
        result = completion(MagicMock())
        # Should return a list of completion items
        assert isinstance(result, list)
        assert len(result) > 0
        # Check first item has required fields
        assert "label" in result[0]
        assert "kind" in result[0]
        # Check some expected keywords are present
        labels = [item["label"] for item in result]
        assert "B3LYP" in labels
        assert "HF" in labels
        assert "OPT" in labels

    def test_hover_feature(self):
        """Test hover feature."""
        from gaussian_lsp.server import hover
        result = hover(MagicMock())
        assert result is None

    def test_diagnostic_feature(self):
        """Test diagnostic feature."""
        from gaussian_lsp.server import diagnostic
        result = diagnostic(MagicMock())
        assert result == []


class TestMain:
    """Test main entry point."""

    @patch('gaussian_lsp.server.server.start_io')
    def test_main(self, mock_start):
        """Test main function."""
        from gaussian_lsp.server import main
        main()
        mock_start.assert_called_once()

    @patch('gaussian_lsp.server.server.start_io')
    def test_main_direct(self, mock_start):
        """Test main when called directly."""
        import gaussian_lsp.server as server_module
        server_module.main()
        mock_start.assert_called_once()
