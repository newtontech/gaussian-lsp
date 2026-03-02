"""Gaussian Language Server Protocol implementation."""
from typing import List, Optional

from lsprotocol import types
from pygls.server import LanguageServer

from gaussian_lsp.parser.gjf_parser import (
    GAUSSIAN_BASIS_SETS,
    GAUSSIAN_JOB_TYPES,
    GAUSSIAN_METHODS,
    VALID_ELEMENTS,
    GaussianJob,
    GJFParser,
)

server = LanguageServer("gaussian-lsp", "0.2.0")


# Documentation for keywords
KEYWORD_DOCS = {
    # Methods
    "HF": "Hartree-Fock method. Simplest ab initio using single Slater determinant.",
    "RHF": "Restricted Hartree-Fock. For closed-shell systems.",
    "UHF": "Unrestricted Hartree-Fock. Different orbitals for alpha/beta spins.",
    "ROHF": "Restricted Open-shell Hartree-Fock. For open-shell systems.",
    "MP2": "Moller-Plesset 2nd order perturbation. Includes electron correlation.",
    "MP3": "Moller-Plesset third-order perturbation theory.",
    "MP4": "Moller-Plesset fourth-order perturbation theory.",
    "CCSD": "Coupled Cluster Singles and Doubles. High-level correlation method.",
    "CCSD(T)": "CCSD with perturbative triples. Gold standard for QC.",
    "B3LYP": "Becke 3-parameter, Lee-Yang-Parr hybrid DFT. Popular functional.",
    "PBE": "Perdew-Burke-Ernzerhof gradient-corrected DFT functional.",
    "PBE0": "Hybrid version of PBE with 25% exact exchange.",
    "M06": "Minnesota 2006 functional. Good for transition metals.",
    "M062X": "Minnesota 2006 functional with double hybrid. Main group chemistry.",
    "wB97XD": "Long-range corrected hybrid functional with dispersion correction.",
    "CAM-B3LYP": "Coulomb-attenuating B3LYP. Good for charge transfer.",
    # Basis sets
    "STO-3G": "Minimal basis set. Fast but not accurate. Good for qualitative results.",
    "3-21G": "Split-valence basis set. Better than minimal, still fast.",
    "6-31G": "Split-valence basis set with 6 Gaussian primitives in core.",
    "6-31G(d)": "6-31G with polarization functions on heavy atoms.",
    "6-31G(d,p)": "6-31G with polarization functions on all atoms.",
    "6-311G": "Triple-split valence basis set.",
    "cc-pVDZ": "Correlation-consistent polarized valence double-zeta.",
    "cc-pVTZ": "Correlation-consistent polarized valence triple-zeta.",
    "cc-pVQZ": "Correlation-consistent polarized valence quadruple-zeta.",
    "def2-SVP": "Karlsruhe split-valence basis set with polarization.",
    "def2-TZVP": "Karlsruhe triple-zeta with polarization. Good balance.",
    "def2-QZVP": "Karlsruhe quadruple-zeta basis set.",
    "LANL2DZ": "LANL double-zeta with ECP for heavy elements.",
    # Job types
    "SP": "Single point energy calculation.",
    "OPT": "Geometry optimization. Finds local minimum energy structure.",
    "FREQ": "Frequency calculation. Computes vibrational frequencies.",
    "OPT FREQ": "Optimization + frequency. Verifies stationary point.",
    "TS": "Transition state optimization. Searches for first-order saddle point.",
    "IRC": "Intrinsic Reaction Coordinate. Follows reaction path from TS.",
    "SCAN": "Potential energy surface scan.",
    "RAMAN": "Raman activity calculation.",
    "NMR": "NMR chemical shift calculation.",
    "POLAR": "Polarizability and hyperpolarizability calculation.",
    "TD": "Time-dependent DFT. For excited states.",
    "CIS": "Configuration Interaction Singles. Excited state method.",
    "COUNTERPOISE": "Counterpoise correction for basis set superposition error.",
    "ONIOM": "N-layered Integrated molecular Orbital and Mechanics.",
}


@server.feature(types.TEXT_DOCUMENT_COMPLETION)
def completion(params: types.CompletionParams) -> types.CompletionList:
    """Provide completions for Gaussian keywords."""
    items = []

    for keyword in GAUSSIAN_METHODS:
        items.append(
            types.CompletionItem(
                label=keyword,
                kind=types.CompletionItemKind.Method,
                detail="Gaussian Method",
                documentation=KEYWORD_DOCS.get(keyword, f"{keyword} calculation method"),
                insert_text=keyword,
            )
        )

    for keyword in GAUSSIAN_BASIS_SETS:
        items.append(
            types.CompletionItem(
                label=keyword,
                kind=types.CompletionItemKind.Class,
                detail="Basis Set",
                documentation=KEYWORD_DOCS.get(keyword, f"{keyword} basis set"),
                insert_text=keyword,
            )
        )

    for keyword in GAUSSIAN_JOB_TYPES:
        items.append(
            types.CompletionItem(
                label=keyword,
                kind=types.CompletionItemKind.Event,
                detail="Job Type",
                documentation=KEYWORD_DOCS.get(keyword, f"{keyword} job type"),
                insert_text=keyword,
            )
        )

    return types.CompletionList(is_incomplete=False, items=items)


@server.feature(types.TEXT_DOCUMENT_HOVER)
def hover(params: types.HoverParams) -> Optional[types.Hover]:
    """Provide hover information."""
    document = server.workspace.get_text_document(params.text_document.uri)

    # Get word at position
    line = document.lines[params.position.line]
    word = _get_word_at_position(line, params.position.character)

    if word.upper() in KEYWORD_DOCS:
        return types.Hover(
            contents=types.MarkupContent(
                kind=types.MarkupKind.Markdown, value=f"**{word}**\n\n{KEYWORD_DOCS[word.upper()]}"
            )
        )

    # Check methods, basis sets, job types
    word_upper = word.upper()
    for method in GAUSSIAN_METHODS:
        if word_upper == method.upper():
            return types.Hover(
                contents=types.MarkupContent(
                    kind=types.MarkupKind.Markdown,
                    value=f"**{method}**\n\nGaussian calculation method.",
                )
            )

    for basis in GAUSSIAN_BASIS_SETS:
        if word_upper == basis.upper():
            return types.Hover(
                contents=types.MarkupContent(
                    kind=types.MarkupKind.Markdown, value=f"**{basis}**\n\nGaussian basis set."
                )
            )

    return None


def _get_word_at_position(line: str, position: int) -> str:
    """Extract word at given position in line."""
    if position >= len(line):
        return ""

    # Find word boundaries
    start = position
    while start > 0 and line[start - 1].isalnum():
        start -= 1

    end = position
    while end < len(line) and line[end].isalnum():
        end += 1

    return line[start:end]


@server.feature(types.TEXT_DOCUMENT_DIAGNOSTIC)
def diagnostic(params: types.DocumentDiagnosticParams) -> types.RelatedFullDocumentDiagnosticReport:
    """Provide diagnostics for GJF files."""
    document = server.workspace.get_text_document(params.text_document.uri)
    content = document.source

    diagnostics = _analyze_content(content)

    return types.RelatedFullDocumentDiagnosticReport(
        items=diagnostics, kind=types.DocumentDiagnosticReportKind.Full
    )


@server.feature(types.TEXT_DOCUMENT_FORMATTING)
def formatting(params: types.DocumentFormattingParams) -> List[types.TextEdit]:
    """Format GJF document."""
    document = server.workspace.get_text_document(params.text_document.uri)
    content = document.source

    formatted = _format_gjf(content)

    if formatted == content:
        return []

    return [
        types.TextEdit(
            range=types.Range(
                start=types.Position(line=0, character=0),
                end=types.Position(line=len(document.lines), character=0),
            ),
            new_text=formatted,
        )
    ]


def _analyze_content(content: str) -> List[types.Diagnostic]:
    """Analyze GJF content and return diagnostics."""
    diagnostics = []
    parser = GJFParser()

    try:
        job = parser.parse(content)
        lines = content.split("\n")

        # Check for missing or invalid route section
        if not job.route_section:
            # Find first non-comment, non-link0 line to check if it should be a route
            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped and not stripped.startswith("!") and not stripped.startswith("%"):
                    # Check if this line looks like it should be a route section
                    # (contains method or basis set keywords)
                    line_upper = stripped.upper()
                    looks_like_route = (
                        any(method.upper() in line_upper for method in GAUSSIAN_METHODS)
                        or any(basis.upper() in line_upper for basis in GAUSSIAN_BASIS_SETS)
                        or "/" in stripped  # Common pattern: method/basis
                    )
                    if looks_like_route:
                        diagnostics.append(
                            types.Diagnostic(
                                range=types.Range(
                                    start=types.Position(line=i, character=0),
                                    end=types.Position(line=i, character=len(stripped)),
                                ),
                                message="Route section must start with #",
                                severity=types.DiagnosticSeverity.Error,
                                source="gaussian-lsp",
                            )
                        )
                    else:
                        # No route section and first line doesn't look like one
                        diagnostics.append(
                            types.Diagnostic(
                                range=types.Range(
                                    start=types.Position(line=i, character=0),
                                    end=types.Position(line=i, character=1),
                                ),
                                message="Missing route section (must start with #)",
                                severity=types.DiagnosticSeverity.Error,
                                source="gaussian-lsp",
                            )
                        )
                    break
            else:
                # No non-comment, non-link0 lines found
                diagnostics.append(
                    types.Diagnostic(
                        range=types.Range(
                            start=types.Position(line=0, character=0),
                            end=types.Position(line=0, character=1),
                        ),
                        message="Missing route section (must start with #)",
                        severity=types.DiagnosticSeverity.Error,
                        source="gaussian-lsp",
                    )
                )
        elif not job.route_section.startswith("#"):
            # Find route line
            for i, line in enumerate(lines):
                if line.strip() and not line.startswith("!") and not line.startswith("%"):
                    diagnostics.append(
                        types.Diagnostic(
                            range=types.Range(
                                start=types.Position(line=i, character=0),
                                end=types.Position(line=i, character=len(line)),
                            ),
                            message="Route section must start with #",
                            severity=types.DiagnosticSeverity.Error,
                            source="gaussian-lsp",
                        )
                    )
                    break

        # Check for atoms
        if not job.atoms:
            # Try to find where geometry should be
            geom_line = len(lines) - 1
            for i, line in enumerate(lines):
                if line.strip() == f"{job.charge} {job.multiplicity}":
                    geom_line = i + 1
                    break

            diagnostics.append(
                types.Diagnostic(
                    range=types.Range(
                        start=types.Position(line=geom_line, character=0),
                        end=types.Position(line=geom_line, character=1),
                    ),
                    message="No atoms defined in geometry section",
                    severity=types.DiagnosticSeverity.Error,
                    source="gaussian-lsp",
                )
            )

        # Check for unknown elements
        for i, line in enumerate(lines):
            match = parser.ATOM_PATTERN.match(line.strip())
            if match:
                element = match.group(1)
                if "(" in element:
                    element = element.split("(")[0]
                if (
                    element.upper() not in [e.upper() for e in VALID_ELEMENTS]
                    and not element.isdigit()
                ):
                    diagnostics.append(
                        types.Diagnostic(
                            range=types.Range(
                                start=types.Position(line=i, character=0),
                                end=types.Position(line=i, character=len(element)),
                            ),
                            message=f"Unknown element: {element}",
                            severity=types.DiagnosticSeverity.Warning,
                            source="gaussian-lsp",
                        )
                    )

        # Check multiplicity
        if job.multiplicity < 1:
            for i, line in enumerate(lines):
                if line.strip() == f"{job.charge} {job.multiplicity}":
                    diagnostics.append(
                        types.Diagnostic(
                            range=types.Range(
                                start=types.Position(line=i, character=0),
                                end=types.Position(line=i, character=len(line)),
                            ),
                            message=f"Invalid multiplicity: {job.multiplicity}",
                            severity=types.DiagnosticSeverity.Error,
                            source="gaussian-lsp",
                        )
                    )

        # Check for method in route section
        route_upper = job.route_section.upper()
        has_method = any(method.upper() in route_upper for method in GAUSSIAN_METHODS)
        if not has_method:
            for i, line in enumerate(lines):
                if line.startswith("#"):
                    diagnostics.append(
                        types.Diagnostic(
                            range=types.Range(
                                start=types.Position(line=i, character=0),
                                end=types.Position(line=i, character=len(line)),
                            ),
                            message="No recognizable calculation method found",
                            severity=types.DiagnosticSeverity.Warning,
                            source="gaussian-lsp",
                        )
                    )
                    break

        # Check for basis set
        has_basis = any(basis.upper() in route_upper for basis in GAUSSIAN_BASIS_SETS)
        has_gen = "GEN" in route_upper or "GENECP" in route_upper
        if not has_basis and not has_gen:
            for i, line in enumerate(lines):
                if line.startswith("#"):
                    diagnostics.append(
                        types.Diagnostic(
                            range=types.Range(
                                start=types.Position(line=i, character=0),
                                end=types.Position(line=i, character=len(line)),
                            ),
                            message="No recognizable basis set (add one or use Gen)",
                            severity=types.DiagnosticSeverity.Warning,
                            source="gaussian-lsp",
                        )
                    )
                    break

    except Exception as e:
        diagnostics.append(
            types.Diagnostic(
                range=types.Range(
                    start=types.Position(line=0, character=0),
                    end=types.Position(line=0, character=1),
                ),
                message=f"Parse error: {str(e)}",
                severity=types.DiagnosticSeverity.Error,
                source="gaussian-lsp",
            )
        )

    return diagnostics


def _format_gjf(content: str) -> str:
    """Format GJF content according to best practices."""
    parser = GJFParser()

    # First validate the content
    is_valid, errors = parser.validate(content)
    if not is_valid:
        # If validation fails, return original content
        return content

    try:
        job = parser.parse(content)
        result = job.to_gjf()
        return result
    except Exception:
        # If parsing fails, return original content
        return content


def parse_gjf_document(content: str) -> Optional[GaussianJob]:
    """Parse GJF document content."""
    parser = GJFParser()
    try:
        return parser.parse(content)
    except Exception:
        return None


def main() -> None:
    """Start the server."""
    server.start_io()


if __name__ == "__main__":
    main()
