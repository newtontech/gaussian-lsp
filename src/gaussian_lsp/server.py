"""
gaussian Language Server Protocol implementation
"""

from pygls.server import LanguageServer

server = LanguageServer("gaussian-lsp", "0.1.0")


@server.feature("textDocument/completion")
def completion(params):
    """Provide completions."""
    return []


@server.feature("textDocument/hover")
def hover(params):
    """Provide hover information."""
    return None


@server.feature("textDocument/diagnostic")
def diagnostic(params):
    """Provide diagnostics."""
    return []


def main():
    """Start the server."""
    server.start_io()


if __name__ == "__main__":
    main()
