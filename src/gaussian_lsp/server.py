"""Gaussian Language Server Protocol implementation."""

import logging
import re
from typing import Dict, List, Optional, Set, Tuple

from lsprotocol import types
from pygls.server import LanguageServer

from gaussian_lsp import __version__
from gaussian_lsp.features.code_actions import CodeActionProvider
from gaussian_lsp.features.diagnostic import DiagnosticProvider
from gaussian_lsp.features.typecheck import TypecheckProvider
from gaussian_lsp.parser.gjf_parser import (
    GAUSSIAN_BASIS_SETS,
    GAUSSIAN_JOB_TYPES,
    GAUSSIAN_METHODS,
    VALID_ELEMENTS,
    GaussianJob,
    GJFParser,
)

server = LanguageServer("gaussian-lsp", __version__)
logger = logging.getLogger(__name__)

diagnostic_provider = DiagnosticProvider(server)
typecheck_provider = TypecheckProvider()
code_action_provider = CodeActionProvider()


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

ELEMENT_ATOMIC_NUMBERS: Dict[str, int] = {
    "H": 1,
    "He": 2,
    "Li": 3,
    "Be": 4,
    "B": 5,
    "C": 6,
    "N": 7,
    "O": 8,
    "F": 9,
    "Ne": 10,
    "Na": 11,
    "Mg": 12,
    "Al": 13,
    "Si": 14,
    "P": 15,
    "S": 16,
    "Cl": 17,
    "Ar": 18,
    "K": 19,
    "Ca": 20,
    "Sc": 21,
    "Ti": 22,
    "V": 23,
    "Cr": 24,
    "Mn": 25,
    "Fe": 26,
    "Co": 27,
    "Ni": 28,
    "Cu": 29,
    "Zn": 30,
    "Ga": 31,
    "Ge": 32,
    "As": 33,
    "Se": 34,
    "Br": 35,
    "Kr": 36,
    "Rb": 37,
    "Sr": 38,
    "Y": 39,
    "Zr": 40,
    "Nb": 41,
    "Mo": 42,
    "Tc": 43,
    "Ru": 44,
    "Rh": 45,
    "Pd": 46,
    "Ag": 47,
    "Cd": 48,
    "In": 49,
    "Sn": 50,
    "Sb": 51,
    "Te": 52,
    "I": 53,
    "Xe": 54,
    "Cs": 55,
    "Ba": 56,
    "La": 57,
    "Ce": 58,
    "Pr": 59,
    "Nd": 60,
    "Pm": 61,
    "Sm": 62,
    "Eu": 63,
    "Gd": 64,
    "Tb": 65,
    "Dy": 66,
    "Ho": 67,
    "Er": 68,
    "Tm": 69,
    "Yb": 70,
    "Lu": 71,
    "Hf": 72,
    "Ta": 73,
    "W": 74,
    "Re": 75,
    "Os": 76,
    "Ir": 77,
    "Pt": 78,
    "Au": 79,
    "Hg": 80,
    "Tl": 81,
    "Pb": 82,
    "Bi": 83,
    "Po": 84,
    "At": 85,
    "Rn": 86,
    "Fr": 87,
    "Ra": 88,
    "Ac": 89,
    "Th": 90,
    "Pa": 91,
    "U": 92,
    "Np": 93,
    "Pu": 94,
    "Am": 95,
    "Cm": 96,
    "Bk": 97,
    "Cf": 98,
    "Es": 99,
    "Fm": 100,
    "Md": 101,
    "No": 102,
    "Lr": 103,
    "Rf": 104,
    "Db": 105,
    "Sg": 106,
    "Bh": 107,
    "Hs": 108,
    "Mt": 109,
    "Ds": 110,
    "Rg": 111,
    "Cn": 112,
    "Nh": 113,
    "Fl": 114,
    "Mc": 115,
    "Lv": 116,
    "Ts": 117,
    "Og": 118,
}

CHARGE_MULT_PATTERN = re.compile(r"^[+-]?\d+\s+\d+$")
INT_START_PATTERN = re.compile(r"^[+-]?\d+\b")
SIMPLE_NUMBER_PATTERN = re.compile(r"^[+-]?(?:(?:\d+(?:\.\d*)?)|(?:\.\d+))(?:[Ee][+-]?\d+)?$")
ZMATRIX_VARIABLE_PATTERN = re.compile(r"^[A-Za-z]\w*$")
MODRED_ATOM_COUNTS = {"B": 2, "A": 3, "D": 4, "L": 3}
ECP_BASIS_MARKERS = ("LANL2DZ", "LANL2MB", "SDD", "DEF2-ECP")
ROUTE_TYPO_HINTS = {
    "FREQENCY": "Use freq instead of freqency.",
    "OPTIMIZE": "Use opt instead of optimize.",
    "M06-2X": "Use M062X instead of M06-2X.",
    "631G": "Did you mean 6-31G?",
    "NPROCSHARED": "Use %nprocshared as a Link0 command, not a route keyword.",
}
HOVER_TOKEN_CHARS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+-_()*,.=")
ROUTE_SPLIT_PATTERN = re.compile(r"[\s/,=]+")
SCF_TYPES = {"RHF", "UHF", "ROHF"}
DFT_METHODS = {
    "B3LYP",
    "B3P86",
    "B3PW91",
    "B1B95",
    "B1LYP",
    "PBE",
    "PBE0",
    "PBE1PBE",
    "RPBE",
    "REVTPSS",
    "M06",
    "M06HF",
    "M062X",
    "M06L",
    "WB97",
    "WB97X",
    "WB97XD",
    "CAM-B3LYP",
    "BLYP",
    "BP86",
    "BP91",
    "OLYP",
    "OPBE",
    "TPSS",
    "TPSSH",
}
POST_HF_METHODS = {"MP2", "MP3", "MP4", "MP4SDQ", "MP5", "CCSD", "CCSD(T)", "QCISD", "QCISD(T)"}
SEMIEMPIRICAL_METHODS = {"PM3", "PM6", "PM7", "AM1", "RM1", "MNDO", "MNDOD", "DFTB", "DFTB3"}


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

    candidates = _hover_lookup_candidates(word)
    for candidate in candidates:
        if candidate.upper() in KEYWORD_DOCS:
            return types.Hover(
                contents=types.MarkupContent(
                    kind=types.MarkupKind.Markdown,
                    value=f"**{candidate}**\n\n{KEYWORD_DOCS[candidate.upper()]}",
                )
            )

    # Check methods, basis sets, job types
    candidate_uppers = {candidate.upper() for candidate in candidates}
    for method in GAUSSIAN_METHODS:
        if method.upper() in candidate_uppers:
            return types.Hover(
                contents=types.MarkupContent(
                    kind=types.MarkupKind.Markdown,
                    value=f"**{method}**\n\nGaussian calculation method.",
                )
            )

    for basis in GAUSSIAN_BASIS_SETS:
        if basis.upper() in candidate_uppers:
            return types.Hover(
                contents=types.MarkupContent(
                    kind=types.MarkupKind.Markdown, value=f"**{basis}**\n\nGaussian basis set."
                )
            )

    return None


def _hover_lookup_candidates(word: str) -> List[str]:
    """Return possible hover lookup keys for a Gaussian route token."""
    if not word:
        return []

    candidates = [word]
    for part in re.split(r"[/=]", word):
        if part and part not in candidates:
            candidates.append(part)

    return candidates


def _get_word_at_position(line: str, position: int) -> str:
    """Extract word at given position in line."""
    if position >= len(line):
        return ""

    # Find word boundaries
    start = position
    while start > 0 and line[start - 1] in HOVER_TOKEN_CHARS:
        start -= 1

    end = position
    while end < len(line) and line[end] in HOVER_TOKEN_CHARS:
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


@server.feature(types.TEXT_DOCUMENT_CODE_ACTION)
def code_action(params: types.CodeActionParams) -> List[types.CodeAction]:
    """Provide code actions for the document."""
    document = server.workspace.get_text_document(params.text_document.uri)
    content = document.source
    return code_action_provider.get_code_actions(content, params.context.diagnostics)


@server.feature(types.TEXT_DOCUMENT_DID_OPEN)
def did_open(params: types.DidOpenTextDocumentParams) -> None:
    """Handle document open — publish live diagnostics."""
    uri = params.text_document.uri
    text = params.text_document.text
    diagnostics = diagnostic_provider.get_diagnostics(text)
    diagnostics.extend(typecheck_provider.validate(text))
    server.publish_diagnostics(uri, diagnostics)


@server.feature(types.TEXT_DOCUMENT_DID_CHANGE)
def did_change(params: types.DidChangeTextDocumentParams) -> None:
    """Handle document change — publish live diagnostics."""
    uri = params.text_document.uri
    if params.content_changes:
        text = params.content_changes[-1].text
        diagnostics = diagnostic_provider.get_diagnostics(text)
        diagnostics.extend(typecheck_provider.validate(text))
        server.publish_diagnostics(uri, diagnostics)


def _make_diagnostic(
    line: int, message: str, severity: types.DiagnosticSeverity, character: int = 0
) -> types.Diagnostic:
    """Create a gaussian-lsp diagnostic at a single line."""
    return types.Diagnostic(
        range=types.Range(
            start=types.Position(line=max(line, 0), character=0),
            end=types.Position(line=max(line, 0), character=max(character, 1)),
        ),
        message=message,
        severity=severity,
        source="gaussian-lsp",
    )


def _canonical_element(element: str) -> str:
    """Normalize a Gaussian element token to an element symbol."""
    clean = element.split("(")[0]
    return clean[:1].upper() + clean[1:].lower() if clean else clean


def _find_route_line(lines: List[str]) -> Optional[int]:
    """Find the first route line."""
    for i, line in enumerate(lines):
        if line.strip().startswith("#"):
            return i
    return None


def _find_charge_line(lines: List[str]) -> Optional[Tuple[int, int, int]]:
    """Find charge/multiplicity line and return index, charge, multiplicity."""
    for i, line in enumerate(lines):
        stripped = line.strip()
        if CHARGE_MULT_PATTERN.match(stripped):
            charge, multiplicity = stripped.split()[:2]
            return i, int(charge), int(multiplicity)
    return None


def _looks_like_route_continuation(line: str) -> bool:
    """Return whether a non-empty line plausibly continues a route section."""
    upper = line.upper()
    return (
        line.strip().startswith("#")
        or "/" in line
        or "=" in line
        or "(" in line
        or any(method.upper() in upper for method in GAUSSIAN_METHODS)
        or any(basis.upper() in upper for basis in GAUSSIAN_BASIS_SETS)
        or any(job_type.upper() in upper for job_type in GAUSSIAN_JOB_TYPES)
    )


def _geometry_line_indexes(lines: List[str], charge_line: Optional[int]) -> List[int]:
    """Return likely geometry line indexes."""
    indexes: List[int] = []
    if charge_line is None:
        return indexes

    for i in range(charge_line + 1, len(lines)):
        stripped = lines[i].strip()
        if stripped:
            indexes.append(i)
        elif indexes:
            break
    return indexes


def _post_geometry_lines(lines: List[str], charge_line: Optional[int]) -> List[Tuple[int, str]]:
    """Return non-empty lines after the first geometry block separator."""
    if charge_line is None:
        return []

    geometry_seen = False
    after_geometry = False
    post_lines = []
    for i in range(charge_line + 1, len(lines)):
        stripped = lines[i].strip()
        if not stripped and geometry_seen:
            after_geometry = True
            continue
        if not stripped:
            continue
        if after_geometry:
            post_lines.append((i, stripped))
        else:
            geometry_seen = True
    return post_lines


def _append_raw_structure_diagnostics(
    diagnostics: List[types.Diagnostic], lines: List[str], parser: GJFParser
) -> None:
    """Diagnose section separators and charge/multiplicity shape."""
    route_line = _find_route_line(lines)
    charge_data = _find_charge_line(lines)
    charge_line = charge_data[0] if charge_data else None

    if route_line is not None and route_line + 1 < len(lines):
        next_line = lines[route_line + 1].strip()
        if next_line and not _looks_like_route_continuation(next_line):
            diagnostics.append(
                _make_diagnostic(
                    route_line + 1,
                    "Missing blank line after route section before the title.",
                    types.DiagnosticSeverity.Error,
                    len(lines[route_line + 1]),
                )
            )

    if charge_line is not None and charge_line > 0 and lines[charge_line - 1].strip():
        diagnostics.append(
            _make_diagnostic(
                charge_line,
                "Missing blank line after title section before charge/multiplicity.",
                types.DiagnosticSeverity.Error,
                len(lines[charge_line]),
            )
        )

    if charge_data is None:
        likely_bad_line = None
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped or stripped.startswith(("%", "#", "!")):
                continue
            if INT_START_PATTERN.match(stripped):
                likely_bad_line = i
                diagnostics.append(
                    _make_diagnostic(
                        i,
                        "Invalid charge/multiplicity line; use two integers like '0 1'.",
                        types.DiagnosticSeverity.Error,
                        len(line),
                    )
                )
                break

        if likely_bad_line is None:
            first_atom_line = next(
                (i for i, line in enumerate(lines) if parser.ATOM_PATTERN.match(line.strip())),
                len(lines) - 1,
            )
            diagnostics.append(
                _make_diagnostic(
                    first_atom_line,
                    "Missing charge/multiplicity line before geometry; add a line like '0 1'.",
                    types.DiagnosticSeverity.Error,
                    len(lines[first_atom_line]) if lines else 1,
                )
            )


def _append_link0_value_diagnostics(diagnostics: List[types.Diagnostic], lines: List[str]) -> None:
    """Validate Link0 value formats that commonly stop Gaussian startup."""
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("%"):
            continue

        if "=" not in stripped:
            continue

        key, value = stripped[1:].split("=", 1)
        key_lower = key.lower()
        value = value.strip()
        if key_lower in {"chk", "oldchk"} and not value:
            diagnostics.append(
                _make_diagnostic(
                    i,
                    f"%{key_lower} must include a non-empty value.",
                    types.DiagnosticSeverity.Error,
                    len(line),
                )
            )
        elif key_lower == "mem":
            if not re.match(
                r"^[1-9]\d*(?:\.\d+)?\s*(KB|MB|GB|TB|KW|MW|GW|TW)?$",
                value,
                re.I,
            ):
                diagnostics.append(
                    _make_diagnostic(
                        i,
                        "%mem value should include a positive number and optional "
                        "unit like MB or GB.",
                        types.DiagnosticSeverity.Error,
                        len(line),
                    )
                )
        elif key_lower in {"nproc", "nprocs", "nprocshared", "nprocsshared"}:
            if not value.isdigit() or int(value) < 1:
                diagnostics.append(
                    _make_diagnostic(
                        i,
                        f"%{key_lower} must be a positive integer.",
                        types.DiagnosticSeverity.Error,
                        len(line),
                    )
                )


def _append_route_semantic_diagnostics(
    diagnostics: List[types.Diagnostic], lines: List[str], route_section: str, job: GaussianJob
) -> None:
    """Validate route-level syntax and common typo failures."""
    route_line = _find_route_line(lines)
    if route_line is None:
        return

    if route_section.count("(") != route_section.count(")"):
        diagnostics.append(
            _make_diagnostic(
                route_line,
                "Unbalanced parentheses in route section; close keyword option groups.",
                types.DiagnosticSeverity.Error,
                len(lines[route_line]),
            )
        )

    route_upper = route_section.upper()
    for typo, hint in ROUTE_TYPO_HINTS.items():
        if typo in route_upper:
            diagnostics.append(
                _make_diagnostic(
                    route_line,
                    hint,
                    types.DiagnosticSeverity.Error,
                    len(lines[route_line]),
                )
            )

    tokens = _route_tokens(route_section)
    token_set = set(tokens)
    method_tokens = _ordered_matches(tokens, GAUSSIAN_METHODS)
    basis_tokens = _ordered_matches(tokens, GAUSSIAN_BASIS_SETS)
    scf_tokens = sorted(token_set & SCF_TYPES)
    post_hf_tokens = [method for method in method_tokens if method in POST_HF_METHODS]
    dft_tokens = [method for method in method_tokens if method in DFT_METHODS]
    semiempirical_tokens = [method for method in method_tokens if method in SEMIEMPIRICAL_METHODS]

    if len(scf_tokens) > 1:
        diagnostics.append(
            _make_diagnostic(
                route_line,
                f"Mutually exclusive SCF methods in route section: {', '.join(scf_tokens)}.",
                types.DiagnosticSeverity.Error,
                len(lines[route_line]),
            )
        )

    if len(method_tokens) > 1 and (post_hf_tokens or dft_tokens or semiempirical_tokens):
        diagnostics.append(
            _make_diagnostic(
                route_line,
                f"Conflicting calculation methods in route section: {', '.join(method_tokens)}.",
                types.DiagnosticSeverity.Error,
                len(lines[route_line]),
            )
        )

    if "SP" in token_set and "OPT" in token_set:
        diagnostics.append(
            _make_diagnostic(
                route_line,
                "SP and OPT are mutually exclusive job types.",
                types.DiagnosticSeverity.Error,
                len(lines[route_line]),
            )
        )

    if len(basis_tokens) > 1:
        diagnostics.append(
            _make_diagnostic(
                route_line,
                f"Multiple basis sets in route section: {', '.join(basis_tokens)}.",
                types.DiagnosticSeverity.Error,
                len(lines[route_line]),
            )
        )

    if semiempirical_tokens and basis_tokens:
        diagnostics.append(
            _make_diagnostic(
                route_line,
                "Semi-empirical methods such as "
                f"{semiempirical_tokens[0]} should not be combined with explicit basis sets.",
                types.DiagnosticSeverity.Error,
                len(lines[route_line]),
            )
        )

    if "GUESS" in token_set and "MIX" in token_set and "RHF" in token_set:
        diagnostics.append(
            _make_diagnostic(
                route_line,
                "Guess=Mix is intended for unrestricted/open-shell calculations, not RHF.",
                types.DiagnosticSeverity.Error,
                len(lines[route_line]),
            )
        )

    if "OPT" in token_set and "MODREDUNDANT" in token_set and not job.modredundant:
        diagnostics.append(
            _make_diagnostic(
                route_line,
                "Opt=ModRedundant is requested, but no ModRedundant section was found.",
                types.DiagnosticSeverity.Error,
                len(lines[route_line]),
            )
        )


def _route_tokens(route_section: str) -> List[str]:
    """Return uppercase Gaussian route tokens."""
    cleaned = route_section.replace("#", " ").replace("(", " ").replace(")", " ")
    return [token.upper() for token in ROUTE_SPLIT_PATTERN.split(cleaned) if token]


def _ordered_matches(tokens: List[str], choices: List[str]) -> List[str]:
    """Return route tokens that exactly match supported Gaussian choices."""
    token_set = set(tokens)
    matches = []
    for choice in choices:
        normalized = choice.upper()
        if normalized in token_set and normalized not in matches:
            matches.append(normalized)
    return matches


def _append_chemistry_diagnostics(
    diagnostics: List[types.Diagnostic], lines: List[str], job: GaussianJob
) -> None:
    """Validate static chemistry constraints that Gaussian rejects early."""
    if not job.atoms:
        return

    total_electrons = 0
    for element, _x, _y, _z in job.atoms:
        canonical = _canonical_element(element)
        if canonical in {"X", "Bq"} or element.isdigit():
            continue
        if canonical not in ELEMENT_ATOMIC_NUMBERS:
            return
        total_electrons += ELEMENT_ATOMIC_NUMBERS[canonical]
    total_electrons -= job.charge

    if total_electrons > 0 and total_electrons % 2 != (job.multiplicity - 1) % 2:
        charge_line = _find_charge_line(lines)
        line = charge_line[0] if charge_line else 0
        diagnostics.append(
            _make_diagnostic(
                line,
                "Charge/multiplicity electron count parity mismatch; "
                "check total electrons and spin multiplicity.",
                types.DiagnosticSeverity.Error,
                len(lines[line]) if lines else 1,
            )
        )


def _basis_section_lines(lines: List[str], charge_line: Optional[int]) -> List[str]:
    """Return non-empty lines after the geometry block."""
    return [line for _i, line in _post_geometry_lines(lines, charge_line)]


def _append_basis_diagnostics(
    diagnostics: List[types.Diagnostic], lines: List[str], job: GaussianJob
) -> None:
    """Validate Gen/GenECP and ECP basis situations."""
    route_line = _find_route_line(lines)
    charge_data = _find_charge_line(lines)
    extra_lines = _basis_section_lines(lines, charge_data[0] if charge_data else None)
    route_upper = job.route_section.upper()
    if route_line is None:
        return

    has_genecp = re.search(r"[/\s=]GENECP\b", route_upper) is not None
    has_gen = re.search(r"[/\s=]GEN\b", route_upper) is not None

    if has_gen and "****" not in extra_lines:
        diagnostics.append(
            _make_diagnostic(
                route_line,
                "Gen basis set is requested, but no custom basis section with **** "
                "delimiters was found.",
                types.DiagnosticSeverity.Error,
                len(lines[route_line]),
            )
        )

    if has_genecp:
        delimiter_count = sum(1 for line in extra_lines if line == "****")
        if delimiter_count < 2:
            diagnostics.append(
                _make_diagnostic(
                    route_line,
                    "GenECP is requested, but no separate ECP block was found "
                    "after the basis section.",
                    types.DiagnosticSeverity.Error,
                    len(lines[route_line]),
                )
            )

    if has_gen or has_genecp:
        geometry_elements = {_canonical_element(atom[0]) for atom in job.atoms}
        for basis_line in extra_lines:
            if basis_line == "****":
                continue
            parts = basis_line.split()
            first_element = _canonical_element(parts[0])
            if first_element not in VALID_ELEMENTS:
                continue
            if parts[-1] != "0":
                line_index = next(
                    (i for i, line in enumerate(lines) if line.strip() == basis_line),
                    route_line,
                )
                diagnostics.append(
                    _make_diagnostic(
                        line_index,
                        "Custom basis center line must end with 0.",
                        types.DiagnosticSeverity.Error,
                        len(lines[line_index]),
                    )
                )
                continue
            for center in parts[:-1]:
                center_element = _canonical_element(center)
                if center_element in VALID_ELEMENTS and center_element not in geometry_elements:
                    line_index = next(
                        (i for i, line in enumerate(lines) if line.strip() == basis_line),
                        route_line,
                    )
                    diagnostics.append(
                        _make_diagnostic(
                            line_index,
                            f"Custom basis references {center_element}, but geometry "
                            f"has no {center_element} atoms.",
                            types.DiagnosticSeverity.Error,
                            len(lines[line_index]),
                        )
                    )
                    break

    if any(marker in route_upper for marker in ECP_BASIS_MARKERS):
        has_heavy_element = any(
            ELEMENT_ATOMIC_NUMBERS.get(_canonical_element(atom[0]), 0) > 36 for atom in job.atoms
        )
        if job.atoms and not has_heavy_element:
            diagnostics.append(
                _make_diagnostic(
                    route_line,
                    "ECP basis set is usually intended for heavier elements; "
                    "check whether this basis is appropriate.",
                    types.DiagnosticSeverity.Warning,
                    len(lines[route_line]),
                )
            )


def _append_geometry_diagnostics(
    diagnostics: List[types.Diagnostic], lines: List[str], parser: GJFParser, job: GaussianJob
) -> None:
    """Validate coordinate and ModRedundant lines."""
    charge_data = _find_charge_line(lines)
    charge_line = charge_data[0] if charge_data else None
    for i in _geometry_line_indexes(lines, charge_line):
        stripped = lines[i].strip()
        if parser.ATOM_PATTERN.match(stripped):
            continue

        parts = stripped.split()
        if len(parts) >= 2 and _canonical_element(parts[0]) in VALID_ELEMENTS:
            diagnostics.append(
                _make_diagnostic(
                    i,
                    "Invalid coordinate line; expected 'Element X Y Z' with three "
                    "numeric coordinates.",
                    types.DiagnosticSeverity.Error,
                    len(lines[i]),
                )
            )

    atom_count = len(job.atoms)
    for i, line in enumerate(lines):
        parts = line.strip().split()
        if not parts or parts[0].upper() not in MODRED_ATOM_COUNTS:
            continue

        command = parts[0].upper()
        expected_atoms = MODRED_ATOM_COUNTS[command]
        atom_refs = []
        for token in parts[1 : 1 + expected_atoms]:
            if token.isdigit():
                atom_refs.append(int(token))
        if len(atom_refs) != expected_atoms:
            diagnostics.append(
                _make_diagnostic(
                    i,
                    f"ModRedundant {command} command expects {expected_atoms} "
                    "integer atom indexes.",
                    types.DiagnosticSeverity.Error,
                    len(line),
                )
            )
            continue
        for atom_ref in atom_refs:
            if atom_ref < 1 or atom_ref > atom_count:
                diagnostics.append(
                    _make_diagnostic(
                        i,
                        f"ModRedundant command references atom {atom_ref}, but "
                        f"geometry has {atom_count} atoms.",
                        types.DiagnosticSeverity.Error,
                        len(line),
                    )
                )
                break

    for index, first_atom in enumerate(job.atoms):
        first_element, first_x, first_y, first_z = first_atom
        for second_atom in job.atoms[index + 1 :]:
            second_element, second_x, second_y, second_z = second_atom
            distance = (
                (first_x - second_x) ** 2 + (first_y - second_y) ** 2 + (first_z - second_z) ** 2
            ) ** 0.5
            if distance < 0.1:
                diagnostics.append(
                    _make_diagnostic(
                        charge_line + 1 if charge_line is not None else 0,
                        f"Atoms {first_element} and {second_element} are very close; "
                        "Gaussian may fail after running.",
                        types.DiagnosticSeverity.Warning,
                        1,
                    )
                )
                return


def _append_zmatrix_diagnostics(
    diagnostics: List[types.Diagnostic], lines: List[str], parser: GJFParser
) -> None:
    """Validate common Z-matrix input mistakes that surface as L101 errors."""
    charge_data = _find_charge_line(lines)
    charge_line = charge_data[0] if charge_data else None
    geometry_indexes = _geometry_line_indexes(lines, charge_line)
    if not geometry_indexes:
        return

    variable_refs: Set[str] = set()
    has_zmatrix_line = False
    for i in geometry_indexes:
        stripped = lines[i].strip()
        parts = stripped.split()
        if not parts or _canonical_element(parts[0]) not in VALID_ELEMENTS:
            continue
        if parser.ATOM_PATTERN.match(stripped):
            continue

        has_zmatrix_line = True
        if len(parts) not in {1, 3, 5, 7}:
            diagnostics.append(
                _make_diagnostic(
                    i,
                    "Mixed Cartesian/Z-matrix coordinate line; use either 3 Cartesian "
                    "numbers or valid Z-matrix fields.",
                    types.DiagnosticSeverity.Error,
                    len(lines[i]),
                )
            )
            continue

        for ref_position in range(1, len(parts), 2):
            if not parts[ref_position].isdigit():
                diagnostics.append(
                    _make_diagnostic(
                        i,
                        "Z-matrix atom reference positions must be integer atom indexes.",
                        types.DiagnosticSeverity.Error,
                        len(lines[i]),
                    )
                )
                break
        for value_position in range(2, len(parts), 2):
            value = parts[value_position]
            if not SIMPLE_NUMBER_PATTERN.match(value):
                variable_refs.add(value)

    if not has_zmatrix_line:
        return

    variable_defs: Set[str] = set()
    for i, line in _post_geometry_lines(lines, charge_line):
        if "=" not in line:
            continue
        name, value = [part.strip() for part in line.split("=", 1)]
        if not ZMATRIX_VARIABLE_PATTERN.match(name) or not SIMPLE_NUMBER_PATTERN.match(value):
            diagnostics.append(
                _make_diagnostic(
                    i,
                    "Invalid Z-matrix variable definition; use NAME=numeric_value.",
                    types.DiagnosticSeverity.Error,
                    len(lines[i]),
                )
            )
            continue
        variable_defs.add(name)

    for variable in sorted(variable_refs - variable_defs):
        line_index = geometry_indexes[-1]
        diagnostics.append(
            _make_diagnostic(
                line_index,
                f"Undefined Z-matrix variable: {variable}.",
                types.DiagnosticSeverity.Error,
                len(lines[line_index]),
            )
        )


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
        elif not job.route_section.startswith("#"):  # pragma: no cover
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

        _append_raw_structure_diagnostics(diagnostics, lines, parser)
        _append_link0_value_diagnostics(diagnostics, lines)
        _append_route_semantic_diagnostics(diagnostics, lines, job.route_section, job)
        _append_chemistry_diagnostics(diagnostics, lines, job)
        _append_basis_diagnostics(diagnostics, lines, job)
        _append_geometry_diagnostics(diagnostics, lines, parser, job)
        _append_zmatrix_diagnostics(diagnostics, lines, parser)

        # Append typecheck diagnostics (keyword types, enums, units, required sections)
        diagnostics.extend(typecheck_provider.validate(content))

    except ValueError:
        logger.warning("Invalid Gaussian input during diagnostics", exc_info=True)
        diagnostics.append(
            types.Diagnostic(
                range=types.Range(
                    start=types.Position(line=0, character=0),
                    end=types.Position(line=0, character=1),
                ),
                message="Parse error: Invalid GJF file format",
                severity=types.DiagnosticSeverity.Error,
                source="gaussian-lsp",
            )
        )
    except PermissionError:
        logger.warning("Permission error during Gaussian input diagnostics", exc_info=True)
        diagnostics.append(
            types.Diagnostic(
                range=types.Range(
                    start=types.Position(line=0, character=0),
                    end=types.Position(line=0, character=1),
                ),
                message="Parse error: Unable to read Gaussian input",
                severity=types.DiagnosticSeverity.Error,
                source="gaussian-lsp",
            )
        )
    except Exception:
        logger.error("Unexpected Gaussian input diagnostic failure", exc_info=True)
        diagnostics.append(
            types.Diagnostic(
                range=types.Range(
                    start=types.Position(line=0, character=0),
                    end=types.Position(line=0, character=1),
                ),
                message="Parse error: Invalid GJF file format",
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
