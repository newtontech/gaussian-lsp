"""
gaussian Language Server Protocol implementation
"""

from pygls.server import LanguageServer
from gaussian_lsp.parser.gjf_parser import GJFParser


server = LanguageServer("gaussian-lsp", "0.1.0")


@server.feature("textDocument/completion")
def completion(params):
    """Provide completions for Gaussian keywords."""
    items = []
    
    # Common Gaussian calculation methods
    methods = [
        "HF", "MP2", "MP3", "MP4", "CCSD", "CCSD(T)",
        "B3LYP", "PBE", "PBE0", "M06", "M062X", "wB97XD",
        "BLYP", "BP86", "TPSS", "TPSSH"
    ]
    
    # Common basis sets
    basis_sets = [
        "STO-3G", "3-21G", "6-31G", "6-31G(d)", "6-31G(d,p)",
        "6-311G(d)", "6-311G(d,p)", "cc-pVDZ", "cc-pVTZ", "cc-pVQZ",
        "def2-SVP", "def2-TZVP", "def2-QZVP"
    ]
    
    # Common job types
    job_types = [
        "SP", "OPT", "FREQ", "OPT FREQ", "TS", "IRC", "SCAN"
    ]
    
    all_keywords = methods + basis_sets + job_types
    
    for keyword in all_keywords:
        items.append({
            "label": keyword,
            "kind": 1,  # Text
            "detail": "Gaussian Keyword"
        })
    
    return items


@server.feature("textDocument/hover")
def hover(params):
    """Provide hover information."""
    return None


@server.feature("textDocument/diagnostic")
def diagnostic(params):
    """Provide diagnostics for GJF files."""
    return []


def parse_gjf_document(content: str):
    """Parse GJF document content."""
    parser = GJFParser()
    try:
        return parser.parse(content)
    except Exception:
        return None


def main():
    """Start the server."""
    server.start_io()


if __name__ == "__main__":
    main()
